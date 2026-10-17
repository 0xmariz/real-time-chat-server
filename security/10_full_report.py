"""
10_full_report.py — Master Security Test Runner + JSON + HTML Report
====================================================================
Runs security tests 01-09 and generates timestamp-matched JSON and HTML
reports from the same results.

Usage:
    python 10_full_report.py

Dependencies:
    pip install requests colorama websocket-client

Only run this against systems you own or are explicitly authorized to test.
"""

import html
import importlib.util
import json
import os
import time
from datetime import datetime

from colorama import Fore, Style, init

init(autoreset=True)

REPORT_DIR = os.path.dirname(os.path.abspath(__file__))
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
REPORT_FILE = os.path.join(REPORT_DIR, f"report_{TIMESTAMP}.json")
HTML_REPORT_FILE = os.path.join(REPORT_DIR, f"report_{TIMESTAMP}.html")

TARGET_HTTP = "http://localhost:8090"
TARGET_TCP = "localhost:8888"
TOOL_NAME = "Nexus Arena Security Test Suite v1.0"

SUITES = [
    ("01 · Brute Force & Credential Attacks", "01_bruteforce.py"),
    ("02 · SQL Injection", "02_sqli.py"),
    ("03 · Cross-Site Scripting (XSS)", "03_xss.py"),
    ("04 · Auth Bypass & Privilege Escalation", "04_auth_bypass.py"),
    ("05 · Rate Limiting & DoS Resistance", "05_rate_limit.py"),
    ("06 · Mass Assignment & XP Manipulation", "06_mass_assign.py"),
    ("07 · IDOR (Insecure Direct Object Ref)", "07_idor.py"),
    ("08 · TCP Server Abuse", "08_tcp_flood.py"),
    ("09 · WebSocket & STOMP Security", "09_websocket.py"),
]


def banner():
    print()
    print(Fore.MAGENTA + "=" * 72)
    print("  NEXUS ARENA CHAT SERVER — FULL SECURITY ASSESSMENT")
    print(f"  Target: {TARGET_HTTP} | TCP: {TARGET_TCP}")
    print(f"  Date  : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 72 + Style.RESET_ALL)
    print()


def import_module(filename):
    """Load a test file whose name starts with a number."""
    path = os.path.join(REPORT_DIR, filename)
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Test module not found: {path}")

    module_name = os.path.splitext(filename)[0]
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not create an import spec for {filename}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_suite(name, filename):
    print(f"\n{Fore.CYAN}{'>' * 72}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}  RUNNING: {name}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'>' * 72}{Style.RESET_ALL}")

    try:
        module = import_module(filename)
        if not callable(getattr(module, "run", None)):
            raise AttributeError(f"{filename} does not define a callable run()")

        results = module.run()
        if results is None:
            return []
        if not isinstance(results, list):
            raise TypeError(
                f"{filename} run() must return a list of result dictionaries; "
                f"got {type(results).__name__}"
            )

        normalized = []
        for item in results:
            if isinstance(item, dict):
                item.setdefault("test", "Unnamed test")
                item.setdefault("vulnerable", False)
                item.setdefault("detail", "")
                normalized.append(item)
            else:
                normalized.append({
                    "test": "Invalid test result",
                    "vulnerable": False,
                    "detail": f"Expected dict, received {type(item).__name__}",
                    "status": "error",
                })
        return normalized

    except Exception as exc:
        message = f"{type(exc).__name__}: {exc}"
        print(f"{Fore.RED}  [ERROR] {filename} failed: {message}{Style.RESET_ALL}")
        # A test runner error is NOT a passing security test.
        return [{
            "test": f"Module load/run failed: {filename}",
            "vulnerable": False,
            "detail": message,
            "status": "error",
        }]


def count_results(all_results):
    total_tests = 0
    total_vulnerable = 0
    total_errors = 0

    for results in all_results.values():
        total_tests += len(results)
        total_vulnerable += sum(
            1 for result in results
            if result.get("vulnerable") is True
        )
        total_errors += sum(
            1 for result in results
            if result.get("status") == "error"
        )

    passed = max(0, total_tests - total_vulnerable - total_errors)
    return {
        "total_tests": total_tests,
        "total_vulnerable": total_vulnerable,
        "total_passed": passed,
        "total_errors": total_errors,
    }


def risk_level(vulnerable, total):
    if total == 0:
        return "NOT ASSESSED"
    ratio = vulnerable / total
    if vulnerable == 0:
        return "CLEAN"
    if ratio >= 0.25 or vulnerable >= 6:
        return "HIGH RISK"
    return "MEDIUM RISK"


def print_summary(all_results):
    summary = count_results(all_results)

    print()
    print(Fore.YELLOW + "=" * 72)
    print("  VULNERABILITY SUMMARY")
    print("=" * 72 + Style.RESET_ALL)

    for suite_name, results in all_results.items():
        vuln = sum(1 for result in results if result.get("vulnerable") is True)
        errors = sum(1 for result in results if result.get("status") == "error")
        total = len(results)
        color = Fore.RED if vuln else (Fore.YELLOW if errors else Fore.GREEN)
        bar = f"[{'!' * min(vuln, 20)}{'.' * max(0, min(total - vuln, 20))}]"
        print(
            f"  {color}{bar:24s} {vuln:2d}/{total:2d} vulnerable"
            f" | {errors:2d} errors | {suite_name}{Style.RESET_ALL}"
        )

    level = risk_level(summary["total_vulnerable"], summary["total_tests"])
    risk_color = (
        Fore.RED if level == "HIGH RISK"
        else Fore.YELLOW if level == "MEDIUM RISK"
        else Fore.GREEN if level == "CLEAN"
        else Fore.YELLOW
    )
    print()
    print(f"  {risk_color}OVERALL RISK: {level}")
    print(
        f"  Tests: {summary['total_tests']} | "
        f"Vulnerable: {summary['total_vulnerable']} | "
        f"Passed: {summary['total_passed']} | Errors: {summary['total_errors']}"
        f"{Style.RESET_ALL}"
    )
    print(Fore.YELLOW + "=" * 72 + Style.RESET_ALL)


def build_report_data(all_results):
    summary = count_results(all_results)
    suites = {}

    for suite_name, results in all_results.items():
        suites[suite_name] = {
            "total": len(results),
            "vulnerable": sum(
                1 for result in results if result.get("vulnerable") is True
            ),
            "errors": sum(
                1 for result in results if result.get("status") == "error"
            ),
            "findings": results,
        }

    return {
        "meta": {
            "timestamp": TIMESTAMP,
            "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "target_http": TARGET_HTTP,
            "target_tcp": TARGET_TCP,
            "tool": TOOL_NAME,
        },
        "suites": suites,
        "summary": {
            **summary,
            "risk_level": risk_level(
                summary["total_vulnerable"], summary["total_tests"]
            ),
        },
    }


def save_json_report(report):
    with open(REPORT_FILE, "w", encoding="utf-8") as file:
        json.dump(report, file, indent=2, ensure_ascii=False)
    print(f"\n  {Fore.CYAN}JSON report saved: {REPORT_FILE}{Style.RESET_ALL}")


def esc(value):
    """HTML-escape untrusted test names/details before inserting into HTML."""
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        value = json.dumps(value, ensure_ascii=False)
    return html.escape(str(value), quote=True)


def make_finding_row(result):
    vulnerable = result.get("vulnerable") is True
    errored = result.get("status") == "error"
    if errored:
        status_class, status_label = "error", "ERROR"
    elif vulnerable:
        status_class, status_label = "vuln", "VULNERABLE"
    else:
        status_class, status_label = "safe", "PASS"

    row_class = "vuln-row" if vulnerable else ("error-row" if errored else "")
    return (
        f'<tr class="{row_class}" data-status="{status_class}">'
        f'<td><span class="pill {status_class}">{status_label}</span></td>'
        f'<td class="test-name">{esc(result.get("test", "Unnamed test"))}</td>'
        f'<td class="detail">{esc(result.get("detail", ""))}</td>'
        "</tr>"
    )


def generate_html_report(report):
    summary = report["summary"]
    meta = report["meta"]
    total = summary["total_tests"]
    vulnerable = summary["total_vulnerable"]
    passed = summary["total_passed"]
    errors = summary["total_errors"]
    risk = summary["risk_level"]
    percentage = round((vulnerable / total) * 100) if total else 0

    risk_class = "high" if risk == "HIGH RISK" else (
        "medium" if risk == "MEDIUM RISK" else "clean"
    )

    suite_sections = []
    for index, (suite_name, suite) in enumerate(report["suites"].items(), start=1):
        suite_total = suite["total"]
        suite_vuln = suite["vulnerable"]
        suite_errors = suite.get("errors", 0)
        suite_pct = round((suite_vuln / suite_total) * 100) if suite_total else 0
        suite_class = "has-vulns" if suite_vuln else (
            "has-errors" if suite_errors else "all-safe"
        )
        rows = "".join(make_finding_row(result) for result in suite["findings"])
        if not rows:
            rows = (
                '<tr><td colspan="3" class="empty">No test results were returned '
                'for this suite.</td></tr>'
            )

        suite_sections.append(f"""
        <section class="suite {suite_class}" data-vuln="{suite_vuln}"
                 data-errors="{suite_errors}">
          <button class="suite-header" type="button" aria-expanded="false">
            <span class="suite-number">{index:02d}</span>
            <span class="suite-heading">
              <span class="suite-name">{esc(suite_name)}</span>
              <span class="suite-count">{suite_total} tests · {suite_errors} errors</span>
            </span>
            <span class="suite-metrics">
              <span class="suite-vuln">{suite_vuln} / {suite_total} vulnerable</span>
              <span class="mini-track"><span style="width:{suite_pct}%"></span></span>
              <span class="chevron">⌄</span>
            </span>
          </button>
          <div class="suite-body">
            <div class="table-wrap">
              <table>
                <thead><tr><th>Status</th><th>Test</th><th>Details</th></tr></thead>
                <tbody>{rows}</tbody>
              </table>
            </div>
          </div>
        </section>""")

    generated_at = esc(meta.get("generated_at", meta.get("timestamp", "")))
    target_http = esc(meta.get("target_http", "Not configured"))
    target_tcp = esc(meta.get("target_tcp", "Not configured"))
    tool_name = esc(meta.get("tool", "Security Test Suite"))

    document = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="dark">
<title>Nexus Arena Security Report — {esc(meta.get("timestamp", ""))}</title>
<style>
:root{{--bg:#080b14;--panel:#111827;--border:#26334a;--text:#e5edf8;--muted:#8b9bb4;--red:#ff5574;--green:#00dfa0;--yellow:#ffc857;--blue:#53c8ff;--purple:#b9a0ff}}
*{{box-sizing:border-box}}
body{{margin:0;background:radial-gradient(ellipse at top,#121b31 0%,var(--bg) 55%);color:var(--text);font:14px/1.55 Inter,Segoe UI,Arial,sans-serif}}
main{{max-width:1200px;margin:auto;padding:28px 20px 60px}}
.hero{{text-align:center;padding:38px 0 26px}}
.kicker{{display:inline-block;padding:5px 12px;border:1px solid #7b3548;border-radius:99px;color:#ff8ba1;background:#ff557411;font-size:11px;font-weight:800;letter-spacing:1.8px;text-transform:uppercase}}
h1{{font-size:clamp(28px,5vw,48px);line-height:1.1;margin:17px 0 10px;letter-spacing:-1.5px}}
.subtitle{{color:var(--muted)}}
.meta{{display:flex;justify-content:center;gap:10px;flex-wrap:wrap;margin-top:20px}}
.meta span{{background:#121c2d;border:1px solid var(--border);padding:7px 11px;border-radius:9px;color:var(--muted);overflow-wrap:anywhere}}
.meta strong{{color:var(--blue);font-weight:600}}
.risk{{display:flex;align-items:center;justify-content:space-between;gap:24px;flex-wrap:wrap;margin:22px 0;padding:26px;border:1px solid var(--border);border-radius:18px;background:#111827cc}}
.risk h2{{font-size:11px;color:var(--muted);letter-spacing:2px;text-transform:uppercase;margin:0 0 6px}}
.risk-label{{font-size:clamp(28px,4vw,42px);font-weight:900;letter-spacing:-1px}}
.risk-label.high{{color:var(--red)}}.risk-label.medium{{color:var(--yellow)}}.risk-label.clean{{color:var(--green)}}
.risk-count{{color:var(--muted);font-family:Consolas,monospace}}
.gauge{{flex:1;min-width:200px;max-width:430px}}
.gauge-label{{display:flex;justify-content:space-between;color:var(--muted);font-size:11px;margin-bottom:8px}}
.track{{height:10px;background:#263247;border-radius:20px;overflow:hidden}}
.fill{{height:100%;width:{percentage}%;background:linear-gradient(90deg,var(--yellow),var(--red));border-radius:20px}}
.stats{{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:13px;margin:20px 0 34px}}
.stat{{background:var(--panel);border:1px solid var(--border);border-radius:15px;padding:20px}}
.stat-num{{font:800 34px/1.2 Consolas,monospace}}
.stat-label{{font-size:11px;color:var(--muted);letter-spacing:1.3px;text-transform:uppercase;margin-top:7px}}
.red{{color:var(--red)}}.green{{color:var(--green)}}.blue{{color:var(--blue)}}.purple{{color:var(--purple)}}.yellow{{color:var(--yellow)}}
.section-title{{display:flex;align-items:center;gap:12px;color:var(--muted);font-size:11px;letter-spacing:2px;text-transform:uppercase;margin:32px 0 14px}}
.section-title:after{{content:"";height:1px;flex:1;background:var(--border)}}
.filters{{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:14px}}
.filter{{border:1px solid var(--border);border-radius:99px;background:#111827;color:var(--muted);padding:8px 14px;cursor:pointer;font-weight:700}}
.filter.active,.filter:hover{{border-color:var(--blue);color:var(--blue)}}
.suite{{border:1px solid var(--border);background:#111827cc;border-radius:14px;margin:11px 0;overflow:hidden}}
.suite.has-vulns{{border-color:#793044}}.suite.has-errors{{border-color:#80652c}}
.suite-header{{display:flex;align-items:center;gap:13px;width:100%;text-align:left;padding:17px;background:transparent;color:inherit;border:0;cursor:pointer}}
.suite-header:hover{{background:#ffffff05}}
.suite-number{{display:grid;place-items:center;width:39px;height:39px;flex-shrink:0;border-radius:10px;background:#1b2a40;color:var(--blue);font-weight:900}}
.suite-heading{{display:flex;flex-direction:column;flex:1;min-width:0}}
.suite-name{{font-weight:750;overflow-wrap:anywhere}}
.suite-count{{color:var(--muted);font-size:12px}}
.suite-metrics{{display:flex;align-items:center;gap:12px;color:var(--muted);font-size:12px;white-space:nowrap}}
.suite-vuln{{color:var(--red);font-weight:800}}
.mini-track{{width:65px;height:5px;background:#29354a;border-radius:8px;overflow:hidden}}
.mini-track span{{display:block;height:100%;background:var(--red)}}
.chevron{{font-size:20px;transition:transform .2s}}
.suite.open .chevron{{transform:rotate(180deg)}}
.suite-body{{display:none;border-top:1px solid var(--border);padding:0 16px 16px}}
.suite.open .suite-body{{display:block}}
.table-wrap{{overflow-x:auto}}
table{{width:100%;border-collapse:collapse;margin-top:8px;text-align:left;font-size:13px}}
th{{font-size:10px;text-transform:uppercase;letter-spacing:1.2px;color:var(--muted)}}
th,td{{padding:11px 10px;border-bottom:1px solid #26334a;vertical-align:top}}
tr:last-child td{{border-bottom:0}}tbody tr:hover{{background:#ffffff05}}
.test-name{{font-family:Consolas,monospace;min-width:220px;overflow-wrap:anywhere}}
.detail{{color:#a9b7cc;overflow-wrap:anywhere;min-width:220px;white-space:pre-wrap}}
.pill{{display:inline-block;padding:3px 8px;border-radius:99px;font-size:10px;font-weight:900;letter-spacing:.5px;white-space:nowrap}}
.pill.vuln{{color:var(--red);background:#ff55741a;border:1px solid #ff55744d}}
.pill.safe{{color:var(--green);background:#00dfa014;border:1px solid #00dfa044}}
.pill.error{{color:var(--yellow);background:#ffc85714;border:1px solid #ffc85755}}
.empty{{color:var(--muted);text-align:center;padding:20px}}
.note{{border:1px solid #80652c;background:#ffc8570d;color:#d9c99f;border-radius:12px;padding:13px 16px;margin:20px 0}}
footer{{border-top:1px solid var(--border);text-align:center;color:var(--muted);padding:24px 0;margin-top:36px;font-size:12px}}
@media(max-width:700px){{main{{padding:12px 12px 40px}}.suite-header{{padding:12px;gap:9px}}.suite-metrics{{gap:5px;white-space:normal;justify-content:flex-end}}.mini-track{{display:none}}.suite-vuln{{max-width:90px;text-align:right}}.risk{{padding:19px}}th,td{{padding:9px 7px}}}}
@media print{{body{{background:white;color:#111}}main{{max-width:none;padding:0}}.suite,.stat,.risk{{background:white;border-color:#bbb;break-inside:avoid}}.filters{{display:none}}.suite-body{{display:block!important}}.suite-header{{color:#111}}.suite-count,.subtitle,.meta span,.detail,.section-title,footer{{color:#444}}.risk-label,.stat-num,.suite-vuln{{color:#111!important}}}}
</style>
</head>
<body>
<main>
  <header class="hero">
    <span class="kicker">⚠ Authorized Security Assessment</span>
    <h1>Nexus Arena Security Report</h1>
    <p class="subtitle">Generated automatically from the latest test run</p>
    <div class="meta">
      <span>HTTP: <strong>{target_http}</strong></span>
      <span>TCP: <strong>{target_tcp}</strong></span>
      <span>Generated: <strong>{generated_at}</strong></span>
      <span>Tool: <strong>{tool_name}</strong></span>
    </div>
  </header>

  <section class="risk">
    <div>
      <h2>Overall risk level</h2>
      <div class="risk-label {risk_class}">{esc(risk)}</div>
      <div class="risk-count">{vulnerable} vulnerable / {total} tests</div>
    </div>
    <div class="gauge">
      <div class="gauge-label"><span>0% vulnerable</span><span>{percentage}% vulnerable</span><span>100%</span></div>
      <div class="track"><div class="fill"></div></div>
    </div>
  </section>

  <section class="stats">
    <div class="stat"><div class="stat-num red">{vulnerable}</div><div class="stat-label">Vulnerable findings</div></div>
    <div class="stat"><div class="stat-num green">{passed}</div><div class="stat-label">Passed tests</div></div>
    <div class="stat"><div class="stat-num blue">{total}</div><div class="stat-label">Total test results</div></div>
    <div class="stat"><div class="stat-num yellow">{errors}</div><div class="stat-label">Runner errors</div></div>
    <div class="stat"><div class="stat-num purple">{len(report["suites"])}</div><div class="stat-label">Test suites</div></div>
  </section>

  <div class="note"><strong>Interpretation note:</strong> A test-runner error is counted separately and is not treated as a passing security test. An HTTP status code alone does not always prove a vulnerability; review the detail and validate findings against expected application behavior.</div>

  <div class="section-title">Test suite results</div>
  <div class="filters" role="group" aria-label="Filter test suites">
    <button class="filter active" data-filter="all">All suites</button>
    <button class="filter" data-filter="vuln">Vulnerable only</button>
    <button class="filter" data-filter="safe">No reported vulnerabilities</button>
    <button class="filter" data-filter="error">Runner errors</button>
  </div>
  <div id="suites">
    {''.join(suite_sections)}
  </div>
  <footer>{tool_name} · Authorized self-testing only · Report ID {esc(meta.get("timestamp", ""))}</footer>
</main>
<script>
document.querySelectorAll('.suite-header').forEach(function(button) {{
  button.addEventListener('click', function() {{
    const suite = button.closest('.suite');
    const open = suite.classList.toggle('open');
    button.setAttribute('aria-expanded', String(open));
  }});
}});
document.querySelectorAll('.filter').forEach(function(button) {{
  button.addEventListener('click', function() {{
    document.querySelectorAll('.filter').forEach(function(item) {{ item.classList.remove('active'); }});
    button.classList.add('active');
    const mode = button.dataset.filter;
    document.querySelectorAll('.suite').forEach(function(suite) {{
      const vuln = Number(suite.dataset.vuln || 0);
      const errors = Number(suite.dataset.errors || 0);
      const show = mode === 'all'
        || (mode === 'vuln' && vuln > 0)
        || (mode === 'safe' && vuln === 0 && errors === 0)
        || (mode === 'error' && errors > 0);
      suite.hidden = !show;
    }});
  }});
}});
</script>
</body>
</html>
"""
    with open(HTML_REPORT_FILE, "w", encoding="utf-8") as file:
        file.write(document)
    print(f"  {Fore.CYAN}HTML report saved: {HTML_REPORT_FILE}{Style.RESET_ALL}")


def run():
    banner()
    all_results = {}

    for name, filename in SUITES:
        all_results[name] = run_suite(name, filename)
        time.sleep(0.25)

    report = build_report_data(all_results)
    print_summary(all_results)
    save_json_report(report)
    generate_html_report(report)

    print()
    print(Fore.GREEN + "Both reports generated." + Style.RESET_ALL)
    print("Open the .html file in your browser to view the dashboard.")
    print()


if __name__ == "__main__":
    run()
