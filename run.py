from app import app
import webbrowser
import time

def main():
    print("=" * 50)
    print("🚀 SISTEM INFORMASI AKUNTANSI - WEB VERSION")
    print("📁 Folder: SIA_CODE_REWRITE")
    print("🌐 Access: http://localhost:5000")
    print("⏹️  Press CTRL+C to stop")
    print("=" * 50)
    
    # Open browser after 2 seconds
    time.sleep(2)
    webbrowser.open('http://localhost:5000')
    
    # Run Flask app
    app.run(host='0.0.0.0', port=5000, debug=True)

if __name__ == '__main__':
    main()