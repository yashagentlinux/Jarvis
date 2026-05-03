import socket
import http.client

def check():
    host = "generativelanguage.googleapis.com"
    print(f"Checking connection to {host}...")
    
    try:
        ip = socket.gethostbyname(host)
        print(f"DNS Success! IP is {ip}")
        
        conn = http.client.HTTPSConnection(host, timeout=5)
        conn.request("GET", "/")
        res = conn.getresponse()
        print(f"HTTP Success! Status: {res.status}")
        
    except Exception as e:
        print(f"CONNECTION FAILED: {e}")
        print("\nPossible fixes:")
        print("1. Check if a firewall or VPN is blocking Python.")
        print("2. Try adding '8.8.8.8' to your /etc/resolv.conf")

if __name__ == "__main__":
    check()
