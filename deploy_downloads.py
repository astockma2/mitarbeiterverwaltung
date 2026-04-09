"""Deployed MVA Download-Seite auf downloads.c3po42.de/mva/."""
import paramiko
import os

VPS_HOST = "187.77.84.94"
VPS_USER = "root"
VPS_PASS = "Nicole1312##"
REMOTE_DIR = "/var/www/downloads/mva"
LOCAL_DIR = os.path.dirname(os.path.abspath(__file__))

DOWNLOAD_HTML = """<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mitarbeiterverwaltung — Download</title>
    <link href="https://fonts.googleapis.com/css2?family=Fredoka:wght@400;500;600;700&family=Space+Mono:wght@400;700&display=swap" rel="stylesheet">
    <style>
        *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
        :root {
            --bg: #0f172a; --bg-deep: #020617; --card: #1e293b;
            --card-hover: #273548; --border: #334155;
            --accent: #06b6d4; --accent-light: #67e8f9;
            --success: #10b981; --text: #e2e8f0; --text-dim: #94a3b8;
        }
        body {
            font-family: 'Fredoka', sans-serif;
            background: var(--bg-deep); color: var(--text);
            min-height: 100vh;
        }
        body::before {
            content: ''; position: fixed; inset: 0; z-index: 0; pointer-events: none;
            background:
                radial-gradient(ellipse at 20% 50%, rgba(6,182,212,0.08) 0%, transparent 50%),
                radial-gradient(ellipse at 80% 20%, rgba(16,185,129,0.06) 0%, transparent 50%);
        }
        .container { max-width: 700px; margin: 0 auto; padding: 40px 20px; position: relative; z-index: 1; }
        header { text-align: center; margin-bottom: 40px; }
        header h1 {
            font-size: 2.2rem; font-weight: 700;
            background: linear-gradient(135deg, var(--accent-light), var(--accent), var(--success));
            -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
        }
        header p { color: var(--text-dim); font-size: 1rem; margin-top: 8px; line-height: 1.6; }
        .card {
            background: var(--card); border: 1px solid var(--border); border-radius: 16px;
            padding: 28px; margin-bottom: 20px;
        }
        .card h2 { font-size: 1.2rem; color: var(--accent-light); margin-bottom: 12px; }
        .card p { color: var(--text-dim); font-size: 0.9rem; line-height: 1.6; margin-bottom: 16px; }
        .badge {
            display: inline-block; background: rgba(6,182,212,0.15); color: var(--accent);
            padding: 2px 10px; border-radius: 6px; font-size: 0.75rem;
            font-family: 'Space Mono', monospace; margin-right: 6px; margin-bottom: 8px;
        }
        .download-btn {
            display: inline-flex; align-items: center; gap: 8px;
            background: var(--accent); color: var(--bg-deep); border: none;
            padding: 12px 24px; border-radius: 10px; cursor: pointer;
            font-family: 'Fredoka', sans-serif; font-weight: 600; font-size: 1rem;
            text-decoration: none; transition: all 0.2s;
        }
        .download-btn:hover { background: var(--accent-light); transform: translateY(-1px); }
        .download-btn svg { width: 20px; height: 20px; }
        .features { list-style: none; padding: 0; margin-bottom: 20px; }
        .features li {
            color: var(--text-dim); font-size: 0.88rem; padding: 4px 0;
            padding-left: 20px; position: relative;
        }
        .features li::before {
            content: '✓'; position: absolute; left: 0; color: var(--success); font-weight: 700;
        }
        .install-box {
            background: var(--bg); border: 1px solid var(--border); border-radius: 10px;
            padding: 12px 16px; display: flex; align-items: center; gap: 10px;
            margin-top: 16px;
        }
        .install-box code {
            font-family: 'Space Mono', monospace; font-size: 0.78rem; color: var(--success);
            flex: 1; white-space: nowrap; overflow-x: auto;
        }
        .install-box button {
            background: var(--accent); color: var(--bg-deep); border: none;
            padding: 6px 14px; border-radius: 8px; cursor: pointer;
            font-family: 'Fredoka', sans-serif; font-weight: 500; font-size: 0.8rem;
            transition: background 0.2s; white-space: nowrap;
        }
        .install-box button:hover { background: var(--accent-light); }
        .links { margin-top: 24px; display: flex; gap: 16px; flex-wrap: wrap; }
        .links a {
            color: var(--accent); text-decoration: none; font-size: 0.85rem;
            border-bottom: 1px solid transparent; transition: border-color 0.2s;
        }
        .links a:hover { border-color: var(--accent); }
        footer {
            text-align: center; margin-top: 40px; padding-top: 20px;
            border-top: 1px solid var(--border); color: var(--text-dim); font-size: 0.8rem;
        }
        footer a { color: var(--accent); text-decoration: none; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Mitarbeiterverwaltung</h1>
            <p>Zeiterfassung, Schichtplanung und Chat für Kliniken und Gesundheitseinrichtungen</p>
        </header>

        <div class="card">
            <h2>Android App</h2>
            <span class="badge">Android</span>
            <span class="badge">Flutter</span>
            <span class="badge">APK</span>
            <ul class="features">
                <li>Zeiterfassung per Fingerabdruck-Login</li>
                <li>Schichtplan einsehen und Tausch beantragen</li>
                <li>Abwesenheiten beantragen und verwalten</li>
                <li>Chat mit Kollegen und KI-Support-Bot</li>
                <li>Push-Benachrichtigungen für Schichtänderungen</li>
            </ul>
            <a href="app-release.apk" class="download-btn">
                <svg viewBox="0 0 24 24" fill="currentColor"><path d="M19 9h-4V3H9v6H5l7 7 7-7zM5 18v2h14v-2H5z"/></svg>
                APK herunterladen
            </a>
        </div>

        <div class="card">
            <h2>Windows / Server Installation</h2>
            <span class="badge">Windows</span>
            <span class="badge">PowerShell</span>
            <p>Einzeiler-Installation per PowerShell (installiert Backend + Frontend lokal):</p>
            <div class="install-box">
                <code>irm https://downloads.c3po42.de/mva/install.ps1 | iex</code>
                <button onclick="copyCmd(this)">Kopieren</button>
            </div>
        </div>

        <div class="links">
            <a href="https://mva.c3po42.de">→ Live-Demo</a>
            <a href="https://mva.c3po42.de/produkt">→ Produktseite</a>
            <a href="https://mva.c3po42.de/api/docs">→ API-Dokumentation</a>
            <a href="https://downloads.c3po42.de">← Alle Downloads</a>
        </div>

        <footer>
            <p>IKK Kliniken IT — <a href="https://mva.c3po42.de">mva.c3po42.de</a></p>
        </footer>
    </div>

    <script>
    function copyCmd(btn) {
        const code = btn.parentElement.querySelector('code').textContent;
        navigator.clipboard.writeText(code).then(() => {
            btn.textContent = 'Kopiert!';
            setTimeout(() => btn.textContent = 'Kopieren', 2000);
        });
    }
    </script>
</body>
</html>
"""

print("=" * 50)
print("  MVA -> downloads.c3po42.de/mva/")
print("=" * 50)
print()

# 1. Verbinden
print("[1/4] Verbinde zum VPS...")
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(VPS_HOST, username=VPS_USER, password=VPS_PASS)
sftp = client.open_sftp()
print("  Verbunden!")
print()


def ssh_exec(cmd, timeout=120):
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode(errors="replace")[:500]
    err = stderr.read().decode(errors="replace")[:500]
    return out, err


def ensure_remote_dir(path):
    try:
        sftp.stat(path)
    except FileNotFoundError:
        ensure_remote_dir(os.path.dirname(path))
        sftp.mkdir(path)


# 2. Dateien hochladen
print("[2/4] Dateien hochladen...")
ensure_remote_dir(REMOTE_DIR)

# Download-Seite
with sftp.open(f"{REMOTE_DIR}/index.html", "w") as f:
    f.write(DOWNLOAD_HTML)
print(f"  {REMOTE_DIR}/index.html")

# APK hochladen
apk_local = os.path.join(LOCAL_DIR, "releases", "app-release.apk")
if os.path.exists(apk_local):
    apk_size = os.path.getsize(apk_local) / (1024 * 1024)
    print(f"  APK hochladen ({apk_size:.1f} MB)...")
    sftp.put(apk_local, f"{REMOTE_DIR}/app-release.apk")
    print(f"  {REMOTE_DIR}/app-release.apk")
else:
    print(f"  WARNUNG: {apk_local} nicht gefunden — APK wird nicht hochgeladen")

# install.ps1 hochladen (falls vorhanden)
install_local = os.path.join(LOCAL_DIR, "install.ps1")
if os.path.exists(install_local):
    sftp.put(install_local, f"{REMOTE_DIR}/install.ps1")
    print(f"  {REMOTE_DIR}/install.ps1")
else:
    print(f"  WARNUNG: install.ps1 nicht gefunden")
print()

# 3. Nginx reload
print("[3/4] Nginx reload...")
ssh_exec("systemctl reload nginx")
print("  OK")
print()

# 4. Test
print("[4/4] Teste...")
out, err = ssh_exec("curl -s -o /dev/null -w '%{http_code}' http://localhost/mva/ -H 'Host: downloads.c3po42.de'")
print(f"  HTTP Status index.html: {out}")

out, err = ssh_exec("curl -s -o /dev/null -w '%{http_code}' http://localhost/mva/app-release.apk -H 'Host: downloads.c3po42.de'")
print(f"  HTTP Status APK: {out}")
print()

print("=" * 50)
print("  DEPLOY FERTIG!")
print("  https://downloads.c3po42.de/mva/")
print()
print("  APK-Download:")
print("  https://downloads.c3po42.de/mva/app-release.apk")
print("=" * 50)

sftp.close()
client.close()
