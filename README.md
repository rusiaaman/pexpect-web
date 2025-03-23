# Pexpect Web Terminal

A real-time, interactive web-based terminal interface powered by Python's pexpect library, Flask, WebSockets, and xterm.js.

## Demo

![Pexpect Web Terminal Demo](pexpect-web-demo.mp4)

## Overview

This application creates a fully interactive web terminal that communicates with a bash/sh shell running on the server. The terminal provides a seamless experience that mimics a native terminal application, with real-time streaming of output via WebSockets and direct keyboard input.

## Features

- Full-screen terminal interface using xterm.js for proper terminal emulation
- Correct handling of ANSI escape sequences and control characters
- Shared terminal state across multiple browser windows/tabs
- Persistent terminal buffer that preserves history between connections
- Real-time streaming of terminal output via WebSockets to all connected clients
- Complete keyboard input support (all keys and key combinations)
- Reset terminal session and clear screen options
- Responsive design that automatically resizes the terminal
- Continuous output streaming without timeouts

## Requirements

- Python 3.x
- Flask
- Flask-SocketIO
- pexpect
- eventlet

## Installation

1. Clone this repository
2. Create a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

## Usage

1. Start the application:
   ```
   python app.py
   ```
   or use the convenience script:
   ```
   ./run.sh
   ```
2. Open your web browser and navigate to `http://localhost:5050`
3. Click anywhere in the black terminal area to focus and start typing
4. Use the terminal as you would a regular terminal - all keyboard input is sent directly to the shell

## Security Considerations

This application executes shell commands on the server. In a production environment, additional security measures should be implemented:

- User authentication
- Command validation and sanitization
- Access control and permission management
- Process isolation
- Rate limiting

## License

MIT
