#!/usr/bin/env python3
"""
02_sqli.py — SQL Injection Attack
===================================
Tests /api/auth/login and /api/auth/register for SQL injection
by injecting classic payloads into username and password fields.

The app uses Spring Data JPA with parameterized queries, so classic
string-concatenation SQLi should be blocked — but this confirms it.

Findings to look for:
  VULN: 200 OK with success:true for a SQLi payload username
  VULN: 500 Internal Server Error (reveals DB errors / stack traces)
  VULN: Different response for tautology vs normal bad password
"""

import requests
import json

BASE_URL = "http://localhost:8090"

# Classic SQL injection payloads
SQLI_PAYLOADS = [
    # Tautology-based
    ("' OR '1'='1",           "classic tautology"),
    ("' OR '1'='1'--",        "tautology with comment"),
    ("' OR 1=1--",            "numeric tautology"),
    ("admin'--",              "comment bypass"),
    ("' OR 'x'='x",           "string tautology"),
    ("\" OR \"1\"=\"1",       "double-quote tautology"),
    # UNION-based
    ("' UNION SELECT 1--",    "union select 1"),
    ("' UNION SELECT null--", "union null"),
    # Stacked queries
    ("'; DROP TABLE user_accounts;--", "drop table"),
    ("'; INSERT INTO user_accounts(username,score) VALUES('hacked',9999);--", "insert row"),
    # Blind boolean
    ("' AND 1=1--",           "blind true"),
    ("' AND 1=2--",           "blind false"),
    # Error-based
    ("' AND EXTRACTVALUE(1,CONCAT(0x7e,VERSION()))--", "error-based mysql"),
    ("' AND 1=CONVERT(int,(SELECT TOP 1 username FROM user_accounts))--", "mssql convert"),
    # NoSQL-style (won't work on SQL but tests parser)
    ('{"$gt": ""}',           "nosql gt operator"),
    # Null byte
    ("admin\x00",             "null byte injection"),
    # Oversized input
    ("A" * 1000,              "oversized username (1000 chars)"),
    ("A" * 10000,             "oversized username (10000 chars)"),
]


def test_login(username, password, label):
    try:
        r = requests.post(f"{BASE_URL}/api/auth/login",
                          json={"username": username, "password": password},
                          timeout=5)
        body = {}
        try:
            body = r.json()
        except Exception:
            pass

        success  = body.get("success", False)
        msg      = body.get("message", "")
        http     = r.status_code

        flag = ""
        if success:
            flag = "  🚨 CRITICAL: AUTH BYPASSED!"
        elif http == 500:
            flag = "  🚨 SERVER ERROR: Possible injection / stack trace leak!"
        elif http not in (400, 401):
            flag = f"  ⚠  Unexpected HTTP {http}"

        result = "BYPASSED" if success else ("ERROR" if http == 500 else "BLOCKED")
        print(f"  [{result:7s}] {label:<40} HTTP {http} | {msg[:50]}{flag}")
        return success, http
    except Exception as e:
        print(f"  [TIMEOUT ] {label:<40} ERROR: {e}")
        return False, 0


def test_register(username, label):
    try:
        r = requests.post(f"{BASE_URL}/api/auth/register",
                          json={"username": username, "password": "validpass"},
                          timeout=5)
        body = {}
        try:
            body = r.json()
        except Exception:
            pass

        success = body.get("success", False)
        http    = r.status_code
        flag    = "  🚨 INJECTED USER REGISTERED!" if success else ""
        result  = "CREATED" if success else ("ERROR" if http == 500 else "BLOCKED")
        print(f"  [{result:7s}] {label:<40} HTTP {http}{flag}")
        return success
    except Exception as e:
        print(f"  [TIMEOUT ] {label:<40} ERROR: {e}")
        return False


def section(title):
    print(f"\n{'='*65}")
    print(f"  {title}")
    print(f"{'='*65}")


def run():
    print("=" * 65)
    print("  NEXUS ARENA — SQL Injection Test Suite")
    print("=" * 65)
    print(f"  Server: {BASE_URL}")
    print(f"  Tests : {len(SQLI_PAYLOADS)} payloads × 2 endpoints\n")

    section("PHASE 1: SQLi in LOGIN username field (password='x')")
    bypasses = 0
    for payload, label in SQLI_PAYLOADS:
        ok, code = test_login(payload, "wrongpassword_x", label)
        if ok: bypasses += 1

    section("PHASE 2: SQLi in LOGIN password field (username='admin')")
    for payload, label in SQLI_PAYLOADS[:12]:  # subset for password field
        ok, code = test_login("CyberNinja", payload, label)
        if ok: bypasses += 1

    section("PHASE 3: SQLi in REGISTER username field")
    for payload, label in SQLI_PAYLOADS:
        test_register(payload, label)

    section("PHASE 4: Second-Order SQLi — Register then Login")
    # Plant a payload as a username, then see if login triggers it
    evil_names = [
        "'; UPDATE user_accounts SET score=99999 WHERE '1'='1",
        "admin'/*",
        "user\\' OR \\'1\\'=\\'1",
    ]
    for name in evil_names:
        r = requests.post(f"{BASE_URL}/api/auth/register",
                          json={"username": name, "password": "x"}, timeout=5)
        try:
            body = r.json()
        except Exception:
            body = {}
        print(f"  Register '{name[:40]}': success={body.get('success')} | {body.get('message','')[:50]}")

    section("RESULTS")
    if bypasses == 0:
        print("  ✔  All SQL injection attempts were BLOCKED.")
        print("  ✔  Spring Data JPA parameterized queries are working correctly.")
    else:
        print(f"  🚨 {bypasses} SQLi payload(s) BYPASSED authentication!")

    print("\n  Additional Check: Visit http://localhost:8090/h2-console")
    print("  If accessible publicly in production, that is itself a critical vulnerability.")
    print(f"\n{'='*65}")
    print(f"  SQL INJECTION TEST COMPLETE")
    print(f"{'='*65}\n")


if __name__ == "__main__":
    run()
