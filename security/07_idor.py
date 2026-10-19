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

def register_and_login(username, password):
    try:
        requests.post(f"{BASE}/api/auth/register", json={"username": username, "password": password}, timeout=5)
        r = requests.post(f"{BASE}/api/auth/login", json={"username": username, "password": password}, timeout=5)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None

# ---- T1: Story ID enumeration (horizontal IDOR) ----------------------------------
def test_story_id_enumeration():
    section("T1 . Story ID Enumeration (Horizontal IDOR)")
    # Create two users and have user A post a story
    user_a = register_and_login("IdorUserA1", "passA")
    user_b = register_and_login("IdorUserB1", "passB")

    story_id = None
    try:
        r = requests.post(f"{BASE}/api/stories",
                          json={"username": "IdorUserA1", "caption": "UserA secret story", "mediaUrl": ""},
                          timeout=5)
        if r.status_code in [200, 201]:
            data = r.json()
            story_id = data.get("id")
            print(f"    UserA created story with id={story_id}")
    except Exception as e:
        log("Story creation for IDOR test", False, str(e))
        return

    if not story_id:
        log("Story creation", False, "Could not get story ID - skipping IDOR")
        return

    # UserB tries to view UserA story by ID (without being UserA)
    try:
        r = requests.get(f"{BASE}/api/stories/{story_id}", timeout=5)
        vuln = r.status_code == 200
        log(f"User B views User A story by ID (GET /api/stories/{story_id})", vuln,
            f"HTTP {r.status_code} - content exposed: {len(r.text)} bytes")
    except Exception as e:
        log("IDOR story view", False, str(e))

    # UserB tries to view story with incremented/decremented IDs (enumeration)
    accessible = 0
    for oid in range(1, 20):
        try:
            r = requests.get(f"{BASE}/api/stories/{oid}", timeout=3)
            if r.status_code == 200:
                accessible += 1
        except Exception:
            pass

    vuln = accessible > 0
    log(f"Story ID enumeration (IDs 1-19): {accessible} accessible", vuln,
        f"{accessible} stories retrievable by guessing sequential IDs")

# ---- T2: Story view count manipulation ------------------------------------------
def test_story_view_manipulation():
    section("T2 . Story View Count Manipulation (IDOR via viewStory)")
    try:
        r = requests.get(f"{BASE}/api/stories", timeout=5)
        stories = r.json() if r.status_code == 200 else []
    except Exception:
        stories = []

    if not stories:
        log("Story view IDOR", False, "No stories available to test")
        return

    for story in stories[:3]:
        sid = story.get("id")
        before = story.get("viewCount", 0)
        # Repeatedly hit view endpoint
        for _ in range(5):
            try:
                requests.post(f"{BASE}/api/stories/{sid}/view", timeout=3)
            except Exception:
                pass
        try:
            r2 = requests.get(f"{BASE}/api/stories/{sid}", timeout=5)
            after = r2.json().get("viewCount", 0) if r2.status_code == 200 else before
        except Exception:
            after = before
        vuln = after > before
        log(f"Story {sid} view count manipulation: {before} -> {after}", vuln,
            f"viewCount changed by {after - before} without auth")

# ---- T3: Story delete by non-owner (IDOR delete) --------------------------------
def test_story_delete_idor():
    section("T3 . Story Delete by Non-Owner (IDOR Delete)")
    # Create UserC and their story
    try:
        requests.post(f"{BASE}/api/auth/register",
                      json={"username": "IdorUserC1", "password": "passC"}, timeout=5)
        r = requests.post(f"{BASE}/api/stories",
                          json={"username": "IdorUserC1", "caption": "UserC private", "mediaUrl": ""},
                          timeout=5)
        if r.status_code in [200, 201]:
            story_id = r.json().get("id")
        else:
            story_id = 1
    except Exception:
        story_id = 1

    # Attacker deletes without being the owner
    for path in [f"/api/stories/{story_id}", f"/api/stories/{story_id}/delete"]:
        try:
            r = requests.delete(f"{BASE}{path}", timeout=5)
            vuln = r.status_code in [200, 204]
            log(f"DELETE {path} as non-owner", vuln, f"HTTP {r.status_code}")
        except Exception as e:
            log(f"DELETE {path}", False, str(e))

# ---- T4: Leaderboard IDOR (access other users data) -----------------------------
def test_leaderboard_user_idor():
    section("T4 . Leaderboard / User Profile IDOR")
    for path in ["/api/leaderboard/user/1", "/api/user/1", "/api/user/TestUser123",
                 "/api/leaderboard/user/TestUser123"]:
        try:
            r = requests.get(f"{BASE}{path}", timeout=5)
            vuln = r.status_code == 200
            log(f"GET {path} (unauthenticated user data access)", vuln,
                f"HTTP {r.status_code} - {len(r.text)} bytes")
        except Exception as e:
            log(f"GET {path}", False, str(e))

# ---- T5: Private message IDOR (read other user's DMs) ---------------------------
def test_private_message_idor():
    section("T5 . Private Message IDOR")
    for path in ["/api/messages/private/TestUser123",
                 "/api/chat/private/TestUser123",
                 "/api/messages/1",
                 "/api/chat/dm/TestUser123"]:
        try:
            r = requests.get(f"{BASE}{path}", timeout=5)
            vuln = r.status_code == 200 and len(r.text) > 10
            log(f"GET {path} (unauthenticated DM access)", vuln,
                f"HTTP {r.status_code}")
        except Exception as e:
            log(f"GET {path}", False, str(e))

def run():
    print("\n" + "#"*60)
    print("  07 . INSECURE DIRECT OBJECT REFERENCE (IDOR)")
    print("#"*60)
    test_story_id_enumeration()
    test_story_view_manipulation()
    test_story_delete_idor()
    test_leaderboard_user_idor()
    test_private_message_idor()
    vuln_count = sum(1 for r in RESULTS if r["vulnerable"])
    print(f"\nSUMMARY: {vuln_count}/{len(RESULTS)} tests flagged VULNERABLE\n")
    return RESULTS

if __name__ == "__main__":
    run()
