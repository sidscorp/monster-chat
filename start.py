#!/usr/bin/env python3
import socket
from contextlib import closing
import sys
import os

def find_free_port():
    """Find an available port"""
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(('', 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port

def main():
    """Start the Flask app on an available port"""
    port = find_free_port()
    
    print("🤖 OpenRouter Chat UI")
    print("=" * 50)
    print(f"🚀 Starting server on port {port}...")
    print(f"📱 Open your browser and go to: http://localhost:{port}")
    print("🆓 Using free OpenRouter models only")
    print("🛑 Press Ctrl+C to stop the server")
    print("=" * 50)
    
    # Import and start the Flask app
    from app import app
    app.run(debug=False, host='0.0.0.0', port=port)

if __name__ == '__main__':
    main()