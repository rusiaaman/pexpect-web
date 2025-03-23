# Import and initialize eventlet monkey patching FIRST
import eventlet
eventlet.monkey_patch()

import os
import pexpect
import threading
import time
import signal
import io
from flask import Flask, request, jsonify, render_template
from flask_socketio import SocketIO, emit

# For storing terminal output buffer
class CircularStringIO:
    def __init__(self, max_size=100000):
        self.buffer = ""
        self.max_size = max_size
        self.lock = threading.Lock()
    
    def write(self, text):
        with self.lock:
            self.buffer += text
            if len(self.buffer) > self.max_size:
                self.buffer = self.buffer[-self.max_size:]
    
    def get_contents(self):
        with self.lock:
            return self.buffer
    
    def clear(self):
        with self.lock:
            self.buffer = ""

app = Flask(__name__)
app.config['SECRET_KEY'] = 'pexpect-web-secret'
socketio = SocketIO(app, async_mode='eventlet', cors_allowed_origins='*')

# Global pexpect subprocess
terminal = None
terminal_lock = threading.Lock()
read_thread = None
running = False

# Buffer to store terminal output
terminal_buffer = CircularStringIO(max_size=500000)  # Store up to 500KB of terminal history

def initialize_terminal():
    """Initialize or reset the terminal session."""
    global terminal, running, terminal_buffer
    
    # Kill any existing read thread
    stop_reading()
    
    # Kill existing terminal process if it exists
    if terminal and terminal.isalive():
        try:
            terminal.close(force=True)
        except:
            pass

    # Clear terminal buffer when explicitly resetting
    terminal_buffer.clear()

    # Try to use zsh, then bash, fallback to sh
    if os.path.exists("/bin/zsh"):
        shell_path = "/bin/zsh"
        startup_command = "source ~/.zshrc 2>/dev/null || true"
    elif os.path.exists("/bin/bash"):
        shell_path = "/bin/bash"
        startup_command = "source ~/.bashrc 2>/dev/null || true"
    else:
        shell_path = "/bin/sh"
        startup_command = ""
    
    # Create a new pexpect process with proper terminal settings
    with terminal_lock:
        # Important settings for proper terminal emulation
        terminal = pexpect.spawn(
            shell_path, 
            encoding='utf-8',
            dimensions=(24, 80),  # Default size, will be updated soon
            env=dict(os.environ, TERM='xterm-256color')  # Set proper terminal type
        )
        
        # Source the appropriate rc file if it exists
        if startup_command:
            terminal.sendline(startup_command)
            # Wait a bit for the rc file to be loaded
            time.sleep(0.5)
    
    # Start reading from the terminal
    start_reading()


def read_terminal():
    """Continuously read from terminal and emit updates via WebSocket."""
    global terminal, running, terminal_buffer
    
    running = True
    
    try:
        while running and terminal and terminal.isalive():
            try:
                # Read any new data (non-blocking)
                with terminal_lock:
                    new_data = terminal.read_nonblocking(size=4096, timeout=0.05)
                    if new_data:
                        # Store in buffer
                        terminal_buffer.write(new_data)
                        
                        # Use app context for emitting to socket
                        with app.app_context():
                            socketio.emit('terminal_output', {'data': new_data})
            except pexpect.TIMEOUT:
                # This is normal, just means no new data
                pass
            except pexpect.EOF:
                # Terminal has closed
                with app.app_context():
                    socketio.emit('terminal_message', {'data': 'Terminal session ended'})
                break
            except Exception as e:
                with app.app_context():
                    socketio.emit('terminal_error', {'error': str(e)})
                time.sleep(0.5)
            
            # Small sleep to prevent CPU overuse
            time.sleep(0.01)
            
    except Exception as e:
        with app.app_context():
            socketio.emit('terminal_error', {'error': f"Read thread error: {str(e)}"})
    finally:
        running = False


def start_reading():
    """Start the terminal reading thread."""
    global read_thread, running
    
    if not running:
        read_thread = threading.Thread(target=read_terminal)
        read_thread.daemon = True
        read_thread.start()


def stop_reading():
    """Stop the terminal reading thread."""
    global running, read_thread
    
    running = False
    if read_thread and read_thread.is_alive():
        read_thread.join(timeout=1.0)
        read_thread = None


@app.route('/')
def index():
    """Render the main interface."""
    return render_template('index.html')


@socketio.on('connect')
def handle_connect():
    """Handle WebSocket connection."""
    # Send the current terminal buffer to just this new client
    buffer_content = terminal_buffer.get_contents()
    if buffer_content:
        emit('terminal_output', {'data': buffer_content})
    
    # Welcome message
    emit('terminal_message', {'data': 'Connected to terminal.'})


@socketio.on('disconnect')
def handle_disconnect():
    """Handle WebSocket disconnection."""
    pass


@socketio.on('get_buffer')
def handle_get_buffer():
    """Send the current terminal buffer to the client."""
    buffer_content = terminal_buffer.get_contents()
    if buffer_content:
        emit('terminal_output', {'data': buffer_content})


@socketio.on('send_key')
def handle_key(data):
    """Send data directly to the terminal."""
    key_data = data.get('key', '')
    
    if not key_data:
        return
    
    with terminal_lock:
        if terminal and terminal.isalive():
            # Send the data directly to the terminal
            terminal.send(key_data)
        else:
            emit('terminal_error', {'error': 'Terminal is not running'})


@socketio.on('reset_terminal')
def handle_reset():
    """Reset the terminal session."""
    initialize_terminal()
    socketio.emit('terminal_message', {'data': 'Terminal has been reset.'})


@socketio.on('resize_terminal')
def handle_resize(data):
    """Resize the terminal."""
    rows = data.get('rows', 24)
    cols = data.get('cols', 80)
    
    with terminal_lock:
        if terminal and terminal.isalive():
            terminal.setwinsize(rows, cols)
            socketio.emit('terminal_message', {'data': f'Terminal resized to {rows}x{cols}'})
        else:
            emit('terminal_error', {'error': 'Terminal is not running'})


if __name__ == '__main__':
    # Initialize the terminal before starting the app
    initialize_terminal()
    socketio.run(app, debug=True, host='0.0.0.0', port=5050)
