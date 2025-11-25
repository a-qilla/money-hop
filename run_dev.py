from app import app
import webbrowser
import threading
import time
import os
import sys

def find_free_port():
    """Find a free port starting from 5000"""
    import socket
    from contextlib import closing
    
    for port in range(5000, 9000):
        with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
            if sock.connect_ex(('localhost', port)) != 0:
                return port
    return 5000

def open_browser(port):
    """Open browser after delay"""
    time.sleep(3)
    webbrowser.open(f'http://localhost:{port}')

def main():
    # Find available port
    port = find_free_port()
    
    print("=" * 60)
    print("🚀 SISTEM INFORMASI AKUNTANSI - DEVELOPMENT MODE")
    print(f"📁 Folder: {os.path.basename(os.getcwd())}")
    print(f"🌐 Access: http://localhost:{port}")
    print(f"🐍 Python: {sys.version.split()[0]}")
    print("💡 Running from: run_dev.py")
    print("⏹️  Press CTRL+C to stop")
    print("=" * 60)
    
    # Open browser automatically
    threading.Thread(target=open_browser, args=(port,), daemon=True).start()
    
    # Run Flask app
    try:
        app.run(host='0.0.0.0', port=port, debug=True, use_reloader=False)
    except Exception as e:
        print(f"❌ Error: {e}")
        print("💡 Coba close aplikasi lain yang menggunakan port yang sama")
        input("Press Enter to exit...")

if __name__ == '__main__':
    main()