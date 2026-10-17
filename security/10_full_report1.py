"""
10_full_report.py — Master Security Test Runner + JSON Report
==============================================================
Runs all security tests (01-09) and generates a full vulnerability
report as JSON + colored console summary.

Usage:
    python 10_full_report.py

Requires: pip install requests colorama websocket-client
"""
import sys
import os
import json
import time
from datetime import datetime
from colorama import Fore, Style, init

init(autoreset=True)

REPORT_DIR = os.path.dirname(os.path.abspath(__file__))
TIMESTAMP  = datetime.now().strftime("%Y%m%d_%H%M%S")
REPORT_FILE = os.path.join(REPORT_DIR, f"report_{TIMESTAMP}.json")

def banner():
    print()
    print(Fore.MAGENTA + "=" * 65)
    print("   NEXUS ARENA CHAT SERVER — FULL SECURITY ASSESSMENT")
    print(f"   Target : http://localhost:8090  |  TCP: localhost:8888")
    print(f"   Date   : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 65 + Style.RESET_ALL)
    print()

def import_module(filename):
    import importlib.util
    path = os.path.join(REPORT_DIR, filename)
    spec = importlib.util.spec_from_file_location(filename[:-3], path)
    mod  = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def run_suite(name, filename):
    print(f"\n{Fore.CYAN}{'>'*65}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}  RUNNING: {name}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'>'*65}{Style.RESET_ALL}")
    try:
        mod = import_module(filename)
        results = mod.run()
        return results or []
    except Exception as e:
        print(f"{Fore.RED}  [ERROR] {filename} failed to run: {e}{Style.RESET_ALL}")
        return [{"test": f"Module load failed: {filename}", "vulnerable": False, "detail": str(e)}]

SUITES = [
    ("01 · Brute Force & Credential Attacks",    "01_bruteforce.py"),
    ("02 · SQL Injection",                        "02_sqli.py"),
    ("03 · Cross-Site Scripting (XSS)",           "03_xss.py"),
    ("04 · Auth Bypass & Privilege Escalation",   "04_auth_bypass.py"),
    ("05 · Rate Limiting & DoS Resistance",       "05_rate_limit.py"),
    ("06 · Mass Assignment & XP Manipulation",    "06_mass_assign.py"),
    ("07 · IDOR (Insecure Direct Object Ref)",    "07_idor.py"),
    ("08 · TCP Server Abuse",                     "08_tcp_flood.py"),
    ("09 · WebSocket & STOMP Security",           "09_websocket.py"),
]

def print_summary(all_results):
    print()
    print(Fore.YELLOW + "=" * 65)
    print("  VULNERABILITY SUMMARY")
    print("=" * 65 + Style.RESET_ALL)

    total_vuln  = 0
    total_tests = 0

    for suite_name, results in all_results.items():
        vuln  = sum(1 for r in results if r.get("vulnerable"))
        total = len(results)
        total_vuln  += vuln
        total_tests += total
        color = Fore.RED if vuln > 0 else Fore.GREEN
        bar   = f"[{'!' * vuln}{'.' * (total - vuln)}]"
        print(f"  {color}{bar:25s}  {vuln:2d}/{total:2d} VULNERABLE  {suite_name}{Style.RESET_ALL}")

    print()
    risk_color = Fore.RED if total_vuln > 5 else (Fore.YELLOW if total_vuln > 0 else Fore.GREEN)
    risk_label = "HIGH RISK" if total_vuln > 5 else ("MEDIUM RISK" if total_vuln > 0 else "CLEAN")
    print(f"  {risk_color}OVERALL RISK: {risk_label}")
    print(f"  Total Vulnerable: {total_vuln}/{total_tests} tests{Style.RESET_ALL}")
    print(Fore.YELLOW + "=" * 65 + Style.RESET_ALL)

def save_report(all_results):
    report = {
        "meta": {
            "timestamp":  TIMESTAMP,
            "target_http": "http://localhost:8090",
            "target_tcp":  "localhost:8888",
            "tool":        "Nexus Arena Security Test Suite v1.0",
        },
        "suites": {}
    }
    for suite_name, results in all_results.items():
        vuln = [r for r in results if r.get("vulnerable")]
        report["suites"][suite_name] = {
            "total":      len(results),
            "vulnerable": len(vuln),
            "findings":   results,
        }
    report["summary"] = {
        "total_tests":     sum(len(v) for v in all_results.values()),
        "total_vulnerable": sum(len([r for r in v if r.get("vulnerable")]) for v in all_results.values()),
    }
    with open(REPORT_FILE, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\n  {Fore.CYAN}Report saved: {REPORT_FILE}{Style.RESET_ALL}")

def run():
    banner()
    all_results = {}
    for name, filename in SUITES:
        results = run_suite(name, filename)
        all_results[name] = results
        time.sleep(0.5)

    print_summary(all_results)
    save_report(all_results)
    print()

if __name__ == "__main__":
    run()
