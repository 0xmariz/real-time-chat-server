import socket
import time
import threading
from colorama import Fore, Style, init

init(autoreset=True)
TCP_HOST = "127.0.0.1"
TCP_PORT = 8888
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

def tcp_connect(timeout=5):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    s.connect((TCP_HOST, TCP_PORT))
    time.sleep(0.3)
    s.recv(4096)
    return s

def send_and_recv(s, msg, wait=0.5):
    s.sendall((msg + "\n").encode())
    time.sleep(wait)
    try:
        return s.recv(4096).decode(errors="ignore")
    except Exception:
        return ""

# ---- T1: TCP connection flood ---------------------------------------------------
def test_tcp_flood():
    section("T1 . TCP Connection Flood")
    sockets = []
    failed = 0
    for i in range(50):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(3)
            s.connect((TCP_HOST, TCP_PORT))
            sockets.append(s)
        except Exception:
            failed += 1
    for s in sockets:
        try:
            s.close()
        except Exception:
            pass
    vuln = len(sockets) > 30
    log(f"TCP flood: opened {len(sockets)}/50 connections", vuln,
        f"Connected={len(sockets)}  Failed={failed}")

# ---- T2: Malformed commands -----------------------------------------------------
def test_malformed_commands():
    section("T2 . Malformed TCP Commands")
    malformed = [
        "/nick",
        "/nick   ",
        "/join",
        "/whisper",
        "/whisper noargs",
        "////invalid",
        "/nick " + "A" * 2000,
        "/msg " + "B" * 5000,
        "\x00\x01\x02\x03\x04",
        "\r\n\r\n",
        "A" * 10000,
        "/nick <script>alert(1)</script>",
        "/msg '; DROP TABLE messages; --",
        "/whisper admin GIVE_ADMIN",
    ]
    try:
        s = tcp_connect()
        for cmd in malformed:
            resp = send_and_recv(s, cmd, wait=0.3)
            crashed = len(resp) == 0 and cmd not in ["\x00\x01\x02\x03\x04", "\r\n\r\n"]
            vuln = crashed
            label = cmd[:50].replace("\x00", "\\x00").replace("\r", "\\r").replace("\n", "\\n")
            log(f"Malformed TCP cmd: {label!r}", vuln,
                "No response (possible crash)" if crashed else f"Handled: {resp[:60].strip()!r}")
        s.close()
    except Exception as e:
        log("TCP malformed commands", True, f"Connection failed mid-test: {e}")

# ---- T3: Nick injection ---------------------------------------------------------
def test_nick_injection():
    section("T3 . /nick Command Injection")
    payloads = [
        "/nick <script>alert('xss')</script>",
        "/nick admin",
        "/nick ' OR 1=1 --",
        "/nick ../../../etc/passwd",
        "/nick \"; cat /etc/passwd #",
        "/nick ",
        "/nick {{7*7}}",
    ]
    for payload in payloads:
        try:
            s = tcp_connect()
            resp = send_and_recv(s, payload)
            vuln = "admin" in resp.lower() and "admin" in payload.lower() and "already" not in resp.lower()
            log(f"TCP /nick injection: {payload[:50]!r}", vuln,
                f"Response: {resp[:80].strip()!r}")
            s.close()
        except Exception as e:
            log(f"TCP /nick {payload[:30]!r}", False, f"Error: {e}")

# ---- T4: Command without nick ---------------------------------------------------
def test_command_without_nick():
    section("T4 . Commands Without Authenticating (/nick)")
    try:
        s = tcp_connect()
        commands = ["/msg hello world", "/join public", "/leaderboard", "/stories", "/stats"]
        for cmd in commands:
            resp = send_and_recv(s, cmd, wait=0.3)
            vuln = "Please" not in resp and "set your username" not in resp.lower() and len(resp) > 0
            log(f"Command without nick: {cmd!r}", vuln,
                f"Response: {resp[:80].strip()!r}")
        s.close()
    except Exception as e:
        log("TCP commands without nick", False, str(e))

# ---- T5: Null bytes and binary data ---------------------------------------------
def test_binary_data():
    section("T5 . Null Bytes and Binary Data Injection")
    binary_payloads = [
        b"\x00" * 100,
        b"\xff\xfe" * 50,
        b"HELLO\x00WORLD\n",
        b"\r\n\r\n" * 10,
        bytes(range(256)),
    ]
    for raw in binary_payloads:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(3)
            s.connect((TCP_HOST, TCP_PORT))
            time.sleep(0.3)
            s.sendall(raw)
            time.sleep(0.5)
            try:
                resp = s.recv(4096)
                crashed = False
            except Exception:
                crashed = True
            log(f"Binary payload ({len(raw)} bytes): {raw[:20]!r}", crashed,
                "Server crashed/disconnected" if crashed else f"Response: {resp[:40]!r}")
            s.close()
        except Exception as e:
            log(f"Binary payload {raw[:10]!r}", False, f"Error: {e}")

# ---- T6: Whisper to non-existent user -------------------------------------------
def test_whisper_nonexistent():
    section("T6 . Whisper to Non-existent User")
    try:
        s = tcp_connect()
        send_and_recv(s, "/nick TcpTester99")
        resp = send_and_recv(s, "/whisper NonExistentUser9999 hello secret message")
        vuln = "error" not in resp.lower() and "not found" not in resp.lower() and len(resp) == 0
        log("Whisper to non-existent user", vuln,
            f"Response: {resp[:80].strip()!r}")
        s.close()
    except Exception as e:
        log("Whisper non-existent user", False, str(e))

# ---- T7: Impersonation via concurrent nick setting ------------------------------
def test_nick_race():
    section("T7 . Nick Race Condition (Duplicate Username)")
    results_local = []
    def grab_nick():
        try:
            s = tcp_connect()
            resp = send_and_recv(s, "/nick SameNick")
            results_local.append(("ok" if "Welcome" in resp or "SameNick" in resp else "denied", s))
        except Exception:
            results_local.append(("error", None))

    threads = [threading.Thread(target=grab_nick) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    ok_count = sum(1 for r, _ in results_local if r == "ok")
    for _, s in results_local:
        if s:
            try:
                s.close()
            except Exception:
                pass

    vuln = ok_count > 1
    log(f"Duplicate /nick race condition: {ok_count}/5 connections claimed 'SameNick'", vuln,
        f"More than 1 user with same nick is a collision vulnerability")

def run():
    print("\n" + "#"*60)
    print("  08 . TCP SERVER ABUSE AND COMMAND INJECTION")
    print("#"*60)
    test_tcp_flood()
    test_malformed_commands()
    test_nick_injection()
    test_command_without_nick()
    test_binary_data()
    test_whisper_nonexistent()
    test_nick_race()
    vuln_count = sum(1 for r in RESULTS if r["vulnerable"])
    print(f"\nSUMMARY: {vuln_count}/{len(RESULTS)} tests flagged VULNERABLE\n")
    return RESULTS

if __name__ == "__main__":
    run()
