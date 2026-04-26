"""
Smoke-Tests für die MVA Produktionsumgebung.
Prüft grundlegende Erreichbarkeit und Login.

Verwendung:
    python tests/e2e/smoke_test.py [BASE_URL]
    python tests/e2e/smoke_test.py https://mva.c3po42.de
"""

import sys
import json
import urllib.request
import urllib.error

BASE_URL = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else "https://mva.c3po42.de"

RESULTS = []


def check(name: str, passed: bool, detail: str = "") -> bool:
    status = "✓ PASS" if passed else "✗ FAIL"
    RESULTS.append((name, passed, detail))
    print(f"  {status}  {name}" + (f" — {detail}" if detail else ""))
    return passed


def http_get(path: str, headers: dict = None, timeout: int = 10) -> tuple:
    req = urllib.request.Request(f"{BASE_URL}{path}", headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, b""
    except Exception as e:
        return 0, str(e).encode()


def http_post_json(path: str, data: dict, timeout: int = 10) -> tuple:
    body = json.dumps(data).encode()
    req = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=body,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read())
        except Exception:
            return e.code, None
    except Exception:
        return 0, None


print(f"\n=== MVA Smoke-Test — {BASE_URL} ===\n")

# 1. Frontend erreichbar
code, _ = http_get("/")
check("Frontend GET /", code == 200, f"HTTP {code}")

# 2. Health-Endpoint
code, body = http_get("/api/health")
if code == 200:
    try:
        data = json.loads(body)
        version = data.get("version", "?")
        check("Health-Check GET /api/health", data.get("status") == "ok", f"Version {version}")
    except Exception:
        check("Health-Check GET /api/health", False, "Ungültige JSON-Antwort")
else:
    check("Health-Check GET /api/health", False, f"HTTP {code}")

# 3. Login mit Admin-Credentials
code, data = http_post_json(
    "/api/v1/auth/login",
    {"username": "admin", "password": "!1j$f0SYQIVhBH"},
)
login_ok = code == 200 and data and "access_token" in data
check("Login POST /api/v1/auth/login", login_ok, f"HTTP {code}")

# 4. Geschützter Endpoint ohne Token → 401
code, _ = http_get("/api/v1/employees")
check("Kein Token → 401", code == 401, f"HTTP {code}")

# 5. Geschützter Endpoint mit Token
if login_ok:
    token = data["access_token"]
    code, _ = http_get("/api/v1/employees", headers={"Authorization": f"Bearer {token}"})
    check("Mitarbeiter-Liste mit Token", code == 200, f"HTTP {code}")
else:
    check("Mitarbeiter-Liste mit Token", False, "Übersprungen (Login fehlgeschlagen)")

# Zusammenfassung
print()
passed = sum(1 for _, ok, _ in RESULTS if ok)
total = len(RESULTS)
print(f"Ergebnis: {passed}/{total} Tests bestanden")

if passed < total:
    print("\nFehlgeschlagene Tests:")
    for name, ok, detail in RESULTS:
        if not ok:
            print(f"  - {name}: {detail}")
    sys.exit(1)

print("Alle Smoke-Tests bestanden.")
sys.exit(0)
