"""Deployed Mitarbeiterverwaltung (Backend + Frontend) auf mva.c3po42.de."""
import paramiko
import os
import time

VPS_HOST = "187.77.84.94"
VPS_USER = "root"
VPS_PASS = "Nicole1312##"
AGENT_REPO = "/opt/agents/Mitarbeiterverwaltung"
REMOTE_DIR = "/opt/mva"
LOCAL_DIR = os.path.dirname(os.path.abspath(__file__))

print("=" * 50)
print("  MVA -> mva.c3po42.de")
print("=" * 50)
print()

# 1. Lokaler Git Push
print("[1/6] Git push origin master...")
ret = os.system("git push origin master")
if ret != 0:
    print("  WARNUNG: git push fehlgeschlagen (ggf. manuell pushen)")
else:
    print("  Push erfolgreich!")
print()

# 2. Verbinden
print("[2/6] Verbinde zum VPS...")
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(VPS_HOST, username=VPS_USER, password=VPS_PASS)
sftp = client.open_sftp()
print("  Verbunden!")
print()


def ssh_exec(cmd, timeout=300):
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode(errors="replace")[:3000]
    err = stderr.read().decode(errors="replace")[:3000]
    return out, err


def ensure_remote_dir(path):
    try:
        sftp.stat(path)
    except FileNotFoundError:
        ensure_remote_dir(os.path.dirname(path))
        sftp.mkdir(path)


# 3. Git fetch + reset auf VPS
print("[3/6] Git fetch auf VPS...")
out, err = ssh_exec(f"cd {AGENT_REPO} && git fetch origin master && git reset --hard origin/master")
if "error" in (out + err).lower() and "already up to date" not in (out + err).lower():
    print(f"  WARNUNG: {err[:300]}")
else:
    print("  Repo aktualisiert!")
print()

# 4. Dateien nach /opt/mva/ kopieren
print("[4/6] Dateien nach /opt/mva/ kopieren...")

# Backend-App
out, err = ssh_exec(f"cp -r {AGENT_REPO}/backend/app/ {REMOTE_DIR}/backend/app/")
print(f"  backend/app/ kopiert")

# Backend requirements.txt
out, err = ssh_exec(f"cp {AGENT_REPO}/backend/requirements.txt {REMOTE_DIR}/backend/requirements.txt")
print(f"  backend/requirements.txt kopiert")

# Backend Dockerfile
out, err = ssh_exec(f"cp {AGENT_REPO}/backend/Dockerfile {REMOTE_DIR}/backend/Dockerfile")
print(f"  backend/Dockerfile kopiert")

# Backend Alembic
out, err = ssh_exec(f"cp -r {AGENT_REPO}/backend/alembic/ {REMOTE_DIR}/backend/alembic/ 2>/dev/null")
out, err = ssh_exec(f"cp {AGENT_REPO}/backend/alembic.ini {REMOTE_DIR}/backend/alembic.ini 2>/dev/null")
print(f"  backend/alembic/ kopiert")

# Frontend
out, err = ssh_exec(f"cp -r {AGENT_REPO}/frontend/src/ {REMOTE_DIR}/frontend/src/")
print(f"  frontend/src/ kopiert")

out, err = ssh_exec(f"cp {AGENT_REPO}/frontend/package.json {REMOTE_DIR}/frontend/package.json")
out, err = ssh_exec(f"cp {AGENT_REPO}/frontend/package-lock.json {REMOTE_DIR}/frontend/package-lock.json 2>/dev/null")
print(f"  frontend/package.json kopiert")

out, err = ssh_exec(f"cp {AGENT_REPO}/frontend/Dockerfile {REMOTE_DIR}/frontend/Dockerfile")
print(f"  frontend/Dockerfile kopiert")

out, err = ssh_exec(f"cp {AGENT_REPO}/frontend/nginx.conf {REMOTE_DIR}/frontend/nginx.conf")
print(f"  frontend/nginx.conf kopiert")

for f in ["index.html", "vite.config.ts", "tsconfig.json", "tsconfig.app.json", "tsconfig.node.json", "eslint.config.js"]:
    ssh_exec(f"cp {AGENT_REPO}/frontend/{f} {REMOTE_DIR}/frontend/{f} 2>/dev/null")
print(f"  frontend/ Config-Dateien kopiert")

# Frontend public/
out, err = ssh_exec(f"cp -r {AGENT_REPO}/frontend/public/ {REMOTE_DIR}/frontend/public/ 2>/dev/null")
print(f"  frontend/public/ kopiert")

# docker-compose.prod.yml
out, err = ssh_exec(f"cp {AGENT_REPO}/docker-compose.prod.yml {REMOTE_DIR}/docker-compose.prod.yml")
print(f"  docker-compose.prod.yml kopiert")

# docs/ (fuer Support-Bot)
out, err = ssh_exec(f"cp -r {AGENT_REPO}/docs/ {REMOTE_DIR}/docs/")
print(f"  docs/ kopiert")

# static/ (Produktseite)
out, err = ssh_exec(f"mkdir -p {REMOTE_DIR}/static && cp -r {AGENT_REPO}/static/ {REMOTE_DIR}/static/")
print(f"  static/ kopiert")

print()

# 5. Docker Build + Restart
print("[5/6] Docker Build + Restart...")
print("  Backend wird gebaut (kann 1-2 Minuten dauern)...")
out, err = ssh_exec(f"cd {REMOTE_DIR} && docker compose -f docker-compose.prod.yml build --no-cache backend", timeout=600)
if "error" in err.lower() and "warning" not in err.lower():
    print(f"  WARNUNG Backend Build: {err[:500]}")
else:
    print("  Backend Build OK!")

print("  Frontend wird gebaut...")
out, err = ssh_exec(f"cd {REMOTE_DIR} && docker compose -f docker-compose.prod.yml build --no-cache frontend", timeout=600)
if "error" in err.lower() and "warning" not in err.lower():
    print(f"  WARNUNG Frontend Build: {err[:500]}")
else:
    print("  Frontend Build OK!")

print("  Container starten...")
out, err = ssh_exec(f"cd {REMOTE_DIR} && docker compose -f docker-compose.prod.yml up -d")
print(f"  {out[:300]}")
print()

# 6. Test
print("[6/6] Teste...")
time.sleep(5)

out, err = ssh_exec("curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8090/")
print(f"  HTTP Status Frontend (8090): {out}")

out, err = ssh_exec("curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8090/api/health")
print(f"  HTTP Status Backend Health: {out}")

out, err = ssh_exec("curl -s http://127.0.0.1:8090/api/health 2>/dev/null | python3 -m json.tool 2>/dev/null || echo 'JSON parse error'")
print(f"  Health: {out[:300]}")

out, err = ssh_exec("docker compose -f /opt/mva/docker-compose.prod.yml ps --format 'table {{.Name}}\t{{.Status}}'")
print(f"  Container:\n{out}")
print()

print("=" * 50)
print("  DEPLOY FERTIG!")
print("  https://mva.c3po42.de")
print("=" * 50)

sftp.close()
client.close()
