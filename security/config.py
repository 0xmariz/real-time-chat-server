import os

# Base target URLs for security tests
# Can be overridden by environment variables if desired
TARGET_HTTP = os.getenv("TARGET_HTTP", "https://real-time-chat-server-n8ml.onrender.com").rstrip("/")

# WebSocket endpoint derived from HTTP scheme (https -> wss, http -> ws)
if TARGET_HTTP.startswith("https://"):
    DEFAULT_WS = "wss://" + TARGET_HTTP[len("https://"):] + "/ws"
elif TARGET_HTTP.startswith("http://"):
    DEFAULT_WS = "ws://" + TARGET_HTTP[len("http://"):] + "/ws"
else:
    DEFAULT_WS = "ws://" + TARGET_HTTP + "/ws"

TARGET_WS = os.getenv("TARGET_WS", DEFAULT_WS)

# TCP host and port (typically runs locally or on a VPS)
TARGET_TCP_HOST = os.getenv("TARGET_TCP_HOST", "127.0.0.1")
TARGET_TCP_PORT = int(os.getenv("TARGET_TCP_PORT", "8888"))
