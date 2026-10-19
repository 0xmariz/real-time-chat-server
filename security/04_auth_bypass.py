import requests
from colorama import Fore, Style, init

init(autoreset=True)
try:
    from config import TARGET_HTTP
except ImportError:
    from .config import TARGET_HTTP

BASE = TARGET_HTTP
RESULTS = []

def log(label, vuln, detail):
    color = Fore.RED if vuln else Fore.GREEN
    tag = "VULN" if vuln else "SAFE"
    print(f"  {color}[{tag}]{Style.RESET_ALL} {label}")
    if detail:
        print(f"         -> {detail}")
    RESULTS.append({"test": label, "vulnerable": vuln, "detail": detail})

def section(title):
    print(f"\n{'='*60}\n  {title}\n{'='*60}")

def register(username, password=None):
    body = {"username": username}
    if password:
        body["password"] = password
    try:
        return requests.post(f"{BASE}/api/auth/register", json=body, timeout=5)
    except Exception:
        return None

def guest_login(username):
    try:
        return requests.post(f"{BASE}/api/auth/guest", json={"username": username}, timeout=5)
    except Exception:
        return None

def test_h2_console():
    section("T1 . H2 Console Exposure (Critical)")
    for path in ["/h2-console", "/h2-console/", "/h2-console/login.jsp", "/console", "/actuator/h2-console"]:
        try:
            r = requests.get(f"{BASE}{path}", timeout=5, allow_redirects=True)
            vuln = r.status_code in [200, 302] and "H2" in r.text
            msg = "H2 login page EXPOSED" if vuln else "not accessible"
            log(f"H2 console at {path}", vuln, f"HTTP {r.status_code} - {msg}")
        except Exception as e:
            log(f"H2 console at {path}", False, f"Connection error: {e}")

def test_unauth_endpoints():
    section("T2 . Unauthenticated API Access")
    endpoints = [
        ("GET",  "/api/leaderboard",        None),
        ("GET",  "/api/chat/history/public", None),
        ("GET",  "/api/stories",             None),
        ("POST", "/api/leaderboard/bonus",   {"username": "TestUser123", "points": 500}),
        ("POST", "/api/chat/send",           {"sender": "hacker", "content": "unauth msg", "room": "public"}),
    ]
    for method, path, body in endpoints:
        try:
            r = requests.get(f"{BASE}{path}", timeout=5) if method == "GET" else requests.post(f"{BASE}{path}", json=body, timeout=5)
            vuln = r.status_code not in [401, 403]
            msg = "accessible without auth!" if vuln else "properly protected"
            log(f"{method} {path} without auth", vuln, f"HTTP {r.status_code} - {msg}")
        except Exception as e:
            log(f"{method} {path}", False, f"Error: {e}")

def test_guest_privilege_escalation():
    section("T3 . Guest Privilege Escalation")
    gr = guest_login("HackerGuest9")
    if not gr or gr.status_code != 200:
        log("Guest login setup", False, "Could not create guest - skipping")
        return
    try:
        r = requests.post(f"{BASE}/api/leaderboard/bonus", json={"username": "HackerGuest9", "points": 99999}, timeout=5)
        vuln = r.status_code == 200
        msg = "XP awarded with NO auth check!" if vuln else "blocked"
        log("Guest awarding self 99999 XP via /api/leaderboard/bonus", vuln, f"HTTP {r.status_code} - {msg}")
    except Exception as e:
        log("Guest XP award", False, str(e))
    try:
        r = requests.post(f"{BASE}/api/stories", json={"username": "HackerGuest9", "caption": "Guest Story", "mediaUrl": ""}, timeout=5)
        log("Guest creating a story (should require auth)", r.status_code in [200, 201], f"HTTP {r.status_code}")
    except Exception as e:
        log("Guest story post", False, str(e))

def test_sender_spoofing():
    section("T4 . Message Sender Spoofing")
    register("VictimUser99", "victimpass")
    try:
        r = requests.post(f"{BASE}/api/chat/send", json={"sender": "VictimUser99", "content": "I was hacked!", "room": "public", "type": "CHAT"}, timeout=5)
        vuln = r.status_code in [200, 201]
        msg = "message sent AS victim!" if vuln else "blocked"
        log("REST chat: spoofed sender field", vuln, f"HTTP {r.status_code} - {msg}")
    except Exception as e:
        log("Sender spoofing REST", False, str(e))

def test_register_mass_assign():
    section("T5 . Mass Assignment via Register")
    payloads = [
        {"username": "AdminHacker1", "password": "pw", "role": "ADMIN"},
        {"username": "AdminHacker2", "password": "pw", "isAdmin": True},
        {"username": "AdminHacker3", "password": "pw", "score": 999999, "level": 100},
        {"username": "AdminHacker4", "password": "pw", "guest": False, "rank": 1},
    ]
    for p in payloads:
        try:
            r = requests.post(f"{BASE}/api/auth/register", json=p, timeout=5)
            data = {}
            try:
                data = r.json()
            except Exception:
                pass
            extra_keys = [k for k in p if k not in ("username", "password")]
            injected = any(str(p[k]) in str(data) for k in extra_keys)
            vuln = injected and r.status_code in [200, 201]
            log(f"Register with extra field: {extra_keys[0]}", vuln, f"HTTP {r.status_code} - injected in response: {injected}")
        except Exception as e:
            log("Register mass assign", False, str(e))

def test_no_session_enforcement():
    section("T6 . Forged Bearer Token Access")
    fake_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyIjoiYWRtaW4ifQ.FAKESIG"
    headers = {"Authorization": f"Bearer {fake_token}"}
    for path in ["/api/leaderboard/bonus", "/api/stories", "/api/chat/history/public"]:
        try:
            r = requests.get(f"{BASE}{path}", headers=headers, timeout=5)
            vuln = r.status_code == 200
            msg = "accepted fake JWT!" if vuln else "rejected"
            log(f"Forged Bearer token on GET {path}", vuln, f"HTTP {r.status_code} - {msg}")
        except Exception as e:
            log(f"Forged token {path}", False, str(e))

def test_account_takeover():
    section("T7 . Account Takeover Vectors")
    for path in ["/api/auth/change-password", "/api/auth/update", "/api/user/update", "/api/profile/update"]:
        try:
            r = requests.post(f"{BASE}{path}", json={"username": "TestUser123", "newPassword": "hacked123"}, timeout=5)
            log(f"Password change at {path} without old-password auth", r.status_code in [200, 201], f"HTTP {r.status_code}")
        except Exception as e:
            log(f"Account takeover {path}", False, str(e))

def run():
    print("\n" + "#"*60)
    print("  04 . AUTH BYPASS AND PRIVILEGE ESCALATION")
    print("#"*60)
    test_h2_console()
    test_unauth_endpoints()
    test_guest_privilege_escalation()
    test_sender_spoofing()
    test_register_mass_assign()
    test_no_session_enforcement()
    test_account_takeover()
    vuln_count = sum(1 for r in RESULTS if r["vulnerable"])
    print(f"\nSUMMARY: {vuln_count}/{len(RESULTS)} tests flagged VULNERABLE\n")
    return RESULTS

if __name__ == "__main__":
    run()
