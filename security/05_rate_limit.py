import requests
import threading
import time
from colorama import Fore, Style, init

init(autoreset=True)
BASE = "http://localhost:8090"
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

# ---- T1: Login flood (no rate limiting) ----------------------------------------
def test_login_flood():
    section("T1 . Login Endpoint Flood (Rate Limit Check)")
    count_ok = 0
    count_429 = 0
    count_err = 0
    THREADS = 50

    def do_login():
        nonlocal count_ok, count_429, count_err
        try:
            r = requests.post(f"{BASE}/api/auth/login",
                              json={"username": "TestUser123", "password": "wrong"},
                              timeout=5)
            if r.status_code == 429:
                count_429 += 1
            elif r.status_code in [200, 401]:
                count_ok += 1
            else:
                count_err += 1
        except Exception:
            count_err += 1

    threads = [threading.Thread(target=do_login) for _ in range(THREADS)]
    start = time.time()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    elapsed = time.time() - start

    vuln = count_429 == 0 and count_ok > 0
    log(f"Login flood: {THREADS} concurrent requests", vuln,
        f"OK/401={count_ok}  429={count_429}  err={count_err}  time={elapsed:.2f}s")

# ---- T2: Register flood (spam accounts) ----------------------------------------
def test_register_flood():
    section("T2 . Register Endpoint Spam (Account Creation Flood)")
    results_local = []
    THREADS = 30

    def do_register(i):
        try:
            r = requests.post(f"{BASE}/api/auth/register",
                              json={"username": f"FloodUser{i}", "password": "pw"},
                              timeout=5)
            results_local.append(r.status_code)
        except Exception:
            results_local.append(0)

    threads = [threading.Thread(target=do_register, args=(i,)) for i in range(THREADS)]
    start = time.time()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    elapsed = time.time() - start

    created = results_local.count(200) + results_local.count(201)
    blocked = results_local.count(429)
    vuln = blocked == 0 and created > 10
    log(f"Register flood: {THREADS} concurrent registrations", vuln,
        f"Created={created}  Blocked(429)={blocked}  time={elapsed:.2f}s")

# ---- T3: Chat message flood (spam detection) ------------------------------------
def test_chat_flood():
    section("T3 . Chat Message Flood (Spam Detection)")
    ok_count = [0]
    THREADS = 40

    def send_msg(i):
        try:
            r = requests.post(f"{BASE}/api/chat/send",
                              json={"sender": "SpamBot", "content": f"SPAM{i}"*10, "room": "public"},
                              timeout=5)
            if r.status_code in [200, 201]:
                ok_count[0] += 1
        except Exception:
            pass

    threads = [threading.Thread(target=send_msg, args=(i,)) for i in range(THREADS)]
    start = time.time()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    elapsed = time.time() - start

    vuln = ok_count[0] > 20
    log(f"Chat flood: {THREADS} concurrent messages", vuln,
        f"Accepted={ok_count[0]}/{THREADS}  time={elapsed:.2f}s")

# ---- T4: Story flood ------------------------------------------------------------
def test_story_flood():
    section("T4 . Story Creation Flood")
    ok_count = [0]
    THREADS = 20

    def post_story(i):
        try:
            r = requests.post(f"{BASE}/api/stories",
                              json={"username": "FloodUser0", "caption": f"flood{i}", "mediaUrl": ""},
                              timeout=5)
            if r.status_code in [200, 201]:
                ok_count[0] += 1
        except Exception:
            pass

    threads = [threading.Thread(target=post_story, args=(i,)) for i in range(THREADS)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    vuln = ok_count[0] > 10
    log(f"Story flood: {THREADS} stories created", vuln,
        f"Accepted={ok_count[0]}/{THREADS}")

# ---- T5: Large payload (oversized body) -----------------------------------------
def test_large_payload():
    section("T5 . Oversized Payload / Memory Exhaustion")
    for size_kb in [100, 500, 1000]:
        payload = "A" * (size_kb * 1024)
        try:
            r = requests.post(f"{BASE}/api/chat/send",
                              json={"sender": "attacker", "content": payload, "room": "public"},
                              timeout=10)
            vuln = r.status_code in [200, 201]
            log(f"Oversized payload ({size_kb}KB) accepted", vuln,
                f"HTTP {r.status_code}")
        except Exception as e:
            log(f"Oversized payload ({size_kb}KB)", False, f"Rejected/error: {e}")

# ---- T6: Slowloris-style incomplete HTTP ----------------------------------------
def test_connection_exhaustion():
    section("T6 . Connection Exhaustion (Slow HTTP)")
    import socket
    open_sockets = []
    blocked = False
    for i in range(100):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(3)
            s.connect(("127.0.0.1", 8090))
            s.send(b"GET /api/leaderboard HTTP/1.1\r\nHost: localhost\r\n")
            open_sockets.append(s)
        except Exception:
            blocked = True
            break

    for s in open_sockets:
        try:
            s.close()
        except Exception:
            pass

    vuln = len(open_sockets) > 50 and not blocked
    log(f"Connection exhaustion: opened {len(open_sockets)} slow connections", vuln,
        f"Server accepted {len(open_sockets)} incomplete HTTP requests")

def run():
    print("\n" + "#"*60)
    print("  05 . RATE LIMITING AND DOS RESISTANCE")
    print("#"*60)
    test_login_flood()
    test_register_flood()
    test_chat_flood()
    test_story_flood()
    test_large_payload()
    test_connection_exhaustion()
    vuln_count = sum(1 for r in RESULTS if r["vulnerable"])
    print(f"\nSUMMARY: {vuln_count}/{len(RESULTS)} tests flagged VULNERABLE\n")
    return RESULTS

if __name__ == "__main__":
    run()
