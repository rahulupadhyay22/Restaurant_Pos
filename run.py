import os
import sys
import glob
import json
import datetime
import threading
import webbrowser
import socket
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from app import create_app, socketio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = create_app()

def verify_license(license_file):
    print(f"🔍 Checking license file: {license_file}")
    # Load the public key for verification
    with open("public.pem", "rb") as f:
        public_key = serialization.load_pem_public_key(f.read())

    # Read the license file
    with open(license_file, "r") as f:
        data = json.load(f)

    license_data = data["license"]
    signature = bytes.fromhex(data["signature"])

    # Reconstruct the JSON used for signing
    license_json = json.dumps(license_data, separators=(',', ':')).encode()

    # Verify the signature
    try:
        public_key.verify(
            signature,
            license_json,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH,
            ),
            hashes.SHA256(),
        )
    except Exception as e:
        print(f"❌ License verification failed: {e}")
        sys.exit(1)

    expiry = datetime.datetime.strptime(license_data["expiry_date"], "%Y-%m-%d").date()
    today = datetime.date.today()

    if today > expiry:
        print("❌ License expired on", expiry)
        sys.exit(1)
    else:
        print(f"✅ License valid until {expiry} for {license_data['client']} (Plan: {license_data['plan']})")

def open_browser():
    """Launch the POS in the default browser automatically after a short delay with correct LAN IP."""
    import time
    time.sleep(2)  # Wait for server to start

    # Determine local IPv4 address
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Connect to a public DNS server to get active local IP (doesn't actually send packets)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
    except Exception as e:
        print(f"⚠️ Could not determine local IP, falling back to 127.0.0.1: {e}")
        local_ip = "127.0.0.1"
    finally:
        s.close()

    url = f"http://{local_ip}:5000"
    print(f"🌐 Opening POS at {url}")
    webbrowser.open_new(url)

if __name__ == "__main__":
    # Automatically find the first license file matching license_*.lic
    license_files = glob.glob(os.path.join(os.getcwd(), 'license_*.lic'))

    if not license_files:
        print("❌ No license file found matching license_*.lic. Exiting.")
        sys.exit(1)

    license_path = license_files[0]
    verify_license(license_path)

    print("🚀 Starting POS system...")

    # Start browser auto-launch in a background thread
    threading.Thread(target=open_browser).start()

    # Start the Flask-SocketIO app
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
