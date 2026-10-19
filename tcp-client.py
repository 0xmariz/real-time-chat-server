"""
Real-Time TCP Chat Client (CLI)
Connects directly to the TCP Socket Server on Port 8888
"""
import socket
import threading
import sys

import os

RAW_HOST = sys.argv[1] if len(sys.argv) > 1 else os.getenv("TCP_HOST", "127.0.0.1")
# Clean URL scheme if passed by accident
HOST = RAW_HOST.replace("https://", "").replace("http://", "").split("/")[0].split(":")[0]
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else int(os.getenv("TCP_PORT", "8888"))

def receive_messages(sock):
    while True:
        try:
            data = sock.recv(4096)
            if not data:
                print("\n[Server disconnected]")
                break
            print(data.decode("utf-8", errors="replace"), end="", flush=True)
        except Exception:
            break

def main():
    print(f"Connecting to TCP Chat Server at {HOST}:{PORT}...")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((HOST, PORT))
    except Exception as e:
        print(f"Error connecting to server: {e}")
        return

    # Start listener thread
    t = threading.Thread(target=receive_messages, args=(sock,), daemon=True)
    t.start()

    try:
        while True:
            line = input()
            if not line:
                continue
            sock.sendall((line + "\n").encode("utf-8"))
            if line.strip().lower() in ["/quit", "/exit"]:
                break
    except (KeyboardInterrupt, EOFError):
        pass
    finally:
        sock.close()
        print("Disconnected.")

if __name__ == "__main__":
    main()
