#!/usr/bin/env python3
"""
03_xss.py — Stored & Reflected XSS Attack
==========================================
Tests whether the server stores and reflects unsanitized HTML/JS
in chat messages, stories, and usernames, and checks security headers.
"""

import requests
import json

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

# Common XSS payloads
XSS_PAYLOADS = [
    ("<script>alert('XSS')</script>",             "Basic script tag"),
    ("<script>alert(document.cookie)</script>",   "Cookie steal script"),
    ("<img src=x onerror=alert('XSS')>",          "Image onerror handler"),
    ("<svg onload=alert('XSS')>",                 "SVG onload handler"),
    ("<a href='javascript:alert(1)'>click</a>",   "Javascript: URI link"),
    ("<details open ontoggle=alert('XSS')>",      "HTML5 details ontoggle"),
]

def post_story(username, content, media_url=""):
    try:
        r = requests.post(f"{BASE_URL}/api/stories",
                          json={"username": username, "content": content, "mediaUrl": media_url},
                          timeout=6)
        try:
            return r.status_code, r.json()
        except Exception:
            return r.status_code, {}
    except Exception as e:
        return 0, {"error": str(e)}

def section(title):
    print(f"\n{'='*65}\n  {title}\n{'='*65}")

def run():
    global RESULTS
    RESULTS = []
    print("=" * 65)
    print("  NEXUS ARENA — XSS (Cross-Site Scripting) Test Suite")
    print("=" * 65)
    print(f"  Server : {BASE_URL}\n")

    section("PHASE 1: Stored XSS in Story Content")
    for payload, label in XSS_PAYLOADS:
        code, body = post_story("XSSTester", payload)
        stored_content = body.get("content", "")
        vuln = (payload in stored_content) and ("<script" in stored_content or "onerror=" in stored_content or "onload=" in stored_content)
        detail = "Raw script stored unescaped in DB" if vuln else f"HTTP {code} stored/sanitized"
        log(f"Stored XSS in story: {label}", vuln, detail)

    section("PHASE 2: XSS in Username")
    for payload, label in XSS_PAYLOADS[:3]:
        short = payload[:32]
        try:
            r = requests.post(f"{BASE_URL}/api/auth/guest", json={"username": short}, timeout=6)
            stored_name = r.json().get("username", "") if r.status_code == 200 else ""
            vuln = any(c in stored_name for c in ["<", ">", "'"])
            log(f"XSS in username: {label}", vuln, f"Stored username: '{stored_name}'")
        except Exception as e:
            log(f"XSS in username: {label}", False, f"Connection error: {e}")

    section("PHASE 3: Reflected XSS via Query Params")
    for payload, label in XSS_PAYLOADS[:3]:
        try:
            r = requests.get(f"{BASE_URL}/?test={requests.utils.quote(payload)}", timeout=6)
            vuln = payload in r.text
            log(f"Reflected XSS: {label}", vuln, "Payload reflected raw in response" if vuln else "Not reflected")
        except Exception as e:
            log(f"Reflected XSS: {label}", False, f"Error: {e}")

    section("PHASE 4: Security Headers Check")
    try:
        r = requests.get(f"{BASE_URL}/", timeout=6)
        headers = r.headers
        log("Header: Content-Security-Policy", "Content-Security-Policy" not in headers,
            headers.get("Content-Security-Policy", "Missing CSP header"))
        log("Header: X-Content-Type-Options", headers.get("X-Content-Type-Options") != "nosniff",
            headers.get("X-Content-Type-Options", "Missing nosniff header"))
        log("Header: X-Frame-Options (Clickjacking)", "X-Frame-Options" not in headers,
            headers.get("X-Frame-Options", "Missing X-Frame-Options"))
    except Exception as e:
        log("Security headers check", False, f"Error checking headers: {e}")

    print(f"\n{'='*65}")
    print(f"  XSS TEST COMPLETE ({len(RESULTS)} findings recorded)")
    print(f"{'='*65}\n")
    return RESULTS

if __name__ == "__main__":
    run()
