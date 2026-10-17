NEXUS ARENA CHAT SERVER — SECURITY TEST SUITE
===============================================
Authorized self-penetration testing only.
Target: http://localhost:8090  |  TCP: localhost:8888

PREREQUISITES
-------------
  pip install requests colorama websocket-client

START THE SERVER FIRST
-----------------------
  cd ..
  java -jar target/realtime-chat-server-1.0.0.jar

RUN ALL TESTS + GENERATE REPORT
---------------------------------
  python 10_full_report.py        <- MASTER RUNNER (recommended)

RUN INDIVIDUAL TESTS
---------------------
  python 01_bruteforce.py         <- Credential brute force, lockout, timing oracle
  python 02_sqli.py               <- SQL injection (login, register, stories)
  python 03_xss.py                <- Stored/Reflected XSS, missing security headers
  python 04_auth_bypass.py        <- Auth bypass, H2 console, IDOR, sender spoof
  python 05_rate_limit.py         <- DoS, flood, connection exhaustion, large payload
  python 06_mass_assign.py        <- Mass assignment, XP inflation, INT overflow
  python 07_idor.py               <- Insecure Direct Object Ref (stories, DMs, users)
  python 08_tcp_flood.py          <- TCP flood, malformed commands, nick injection
  python 09_websocket.py          <- STOMP auth, sender spoof, topic hijack
  python 10_full_report.py        <- Master runner -> saves report_YYYYMMDD.json

ATTACK COVERAGE
----------------
  Script  | Category                    | Key Tests
  --------|-----------------------------|-----------------------------------------
  01      | Brute Force                 | Wordlist, lockout, timing oracle, enum
  02      | SQL Injection               | Tautology, UNION, blind, error-based
  03      | XSS                         | Stored, reflected, JS URI, CSP headers
  04      | Auth Bypass                 | H2 console, unauth endpoints, spoofing
  05      | Rate Limiting / DoS         | Login flood, register spam, large body
  06      | Mass Assignment             | XP inflation, privilege field injection
  07      | IDOR                        | Story enum, delete by non-owner, DMs
  08      | TCP Abuse                   | Flood, malformed cmds, binary, race
  09      | WebSocket / STOMP           | Unauth CONNECT, sender spoof, hijack
  10      | Master Report               | Runs 01-09, saves JSON report

OUTPUT
-------
  After running 10_full_report.py, a file report_YYYYMMDD_HHMMSS.json
  is created in this folder with all findings.

DISCLAIMER
-----------
  These tests are for authorized self-assessment of your own server only.
  Do NOT run against systems you do not own or have explicit permission to test.
