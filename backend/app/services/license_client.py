"""Lizenz-Client fuer C3PO42-Produkte.

Einheitliches Modul, das in jedes kaufbare Projekt eingebunden wird.
Loest das alte, manuell in jede main.py kopierte Block-Pattern ab.

Verwendung in main.py:

    from license_client import LicenseClient

    LICENSE = LicenseClient(
        base_dir=Path(__file__).parent,
        product_code="ti-monitor",
        product_name="TI-Monitor",
        product_price="99",
        get_usage_count=lambda: None,   # None oder Callable () -> int (aktive MA)
    )

    @asynccontextmanager
    async def lifespan(app):
        # ...
        _lic_task = asyncio.create_task(LICENSE.check_loop())
        _usage_task = asyncio.create_task(LICENSE.usage_report_loop())
        yield
        _lic_task.cancel()
        _usage_task.cancel()

    app.middleware("http")(LICENSE.guard)
    LICENSE.register_routes(app)

Features:
- Lizenz-Pruefung gegen den LizenzServer, 7-Tage-Grace-Period
- Instance-Binding (.instance_id File)
- Trial-Fallback wenn kein Key gesetzt
- Key-Persistenz in `.license_key` File (alternativ ENV LICENSE_KEY)
- POST /api/license/install — setzt Key von der Buy-Widget-Seite
- GET /lizenz — laedt das zentrale Buy-Widget
- MA-Report (usage-report) fuer PRO_MA_MONAT-Produkte monatlich
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable, Optional

import httpx
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel


log = logging.getLogger("license_client")


class InstallRequest(BaseModel):
    license_key: str


class LicenseClient:
    def __init__(
        self,
        base_dir: Path,
        product_code: str,
        product_name: str,
        product_price: str,
        get_usage_count: Optional[Callable[[], Optional[int]]] = None,
        exempt_paths: tuple[str, ...] = (),
        license_server: Optional[str] = None,
    ) -> None:
        self.base_dir = Path(base_dir)
        self.product_code = product_code
        self.product_name = product_name
        self.product_price = product_price
        self.get_usage_count = get_usage_count
        self.license_server = license_server or os.environ.get(
            "LICENSE_SERVER", "https://license.c3po42.de"
        )

        self.key_file = self.base_dir / ".license_key"
        self.instance_file = self.base_dir / ".instance_id"

        # Priorisierung: ENV > File
        env_key = os.environ.get("LICENSE_KEY", "")
        if env_key:
            self.license_key = env_key
        elif self.key_file.exists():
            self.license_key = self.key_file.read_text(encoding="utf-8").strip()
        else:
            self.license_key = ""

        self._instance_id: Optional[str] = None

        self.cache: dict = {
            "valid": True,
            "type": "TRIAL",
            "expires": None,
            "checked": None,
            "grace_until": None,
            "features": [],
            "bound_to_other_instance": False,
        }

        self.exempt_paths = (
            "/api/version",
            "/api/update/check",
            "/api/update/install",
            "/api/auth/login",
            "/lizenz",
            "/api/license/install",
            "/api/license/status",
            "/docs/readme",
            "/docs/handbuch",
            "/buy-widget.js",
        ) + exempt_paths

    # ------------------------------------------------------------------
    # Instance-ID
    # ------------------------------------------------------------------
    def get_instance_id(self) -> str:
        if self._instance_id:
            return self._instance_id
        if self.instance_file.exists():
            self._instance_id = self.instance_file.read_text(encoding="utf-8").strip()
            return self._instance_id
        raw = f"{os.environ.get('COMPUTERNAME', '')}{os.environ.get('HOSTNAME', '')}{uuid.getnode()}"
        self._instance_id = hashlib.sha256(raw.encode()).hexdigest()[:16]
        try:
            self.instance_file.write_text(self._instance_id, encoding="utf-8")
        except Exception as e:
            log.warning(f"Instance-ID konnte nicht gespeichert werden: {e}")
        return self._instance_id

    # ------------------------------------------------------------------
    # Key-Persistenz
    # ------------------------------------------------------------------
    def set_license_key(self, key: str) -> None:
        self.license_key = key.strip()
        try:
            self.key_file.write_text(self.license_key, encoding="utf-8")
        except Exception as e:
            log.error(f"Lizenz-Key konnte nicht gespeichert werden: {e}")

    # ------------------------------------------------------------------
    # Lizenz-Verifikation
    # ------------------------------------------------------------------
    async def verify(self) -> None:
        """Prueft Lizenz gegen den LizenzServer. Fallback: Trial."""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                if self.license_key:
                    r = await client.post(
                        f"{self.license_server}/api/license/verify",
                        json={
                            "license_key": self.license_key,
                            "product_code": self.product_code,
                            "instance_id": self.get_instance_id(),
                        },
                    )
                else:
                    r = await client.post(
                        f"{self.license_server}/api/license/trial",
                        json={
                            "product_code": self.product_code,
                            "instance_id": self.get_instance_id(),
                        },
                    )
                if r.status_code == 200:
                    data = r.json()
                    self.cache["valid"] = data.get("valid", False)
                    self.cache["type"] = data.get("type", "UNKNOWN")
                    self.cache["expires"] = data.get("expires")
                    self.cache["features"] = data.get("features", [])
                    self.cache["checked"] = datetime.now().isoformat()
                    self.cache["grace_until"] = None
                    self.cache["bound_to_other_instance"] = bool(
                        data.get("bound_to_other_instance")
                    )
                    self.cache["error"] = data.get("error")
                    return
        except Exception as e:
            log.warning(f"Lizenz-Check fehlgeschlagen: {e}")
        # Grace Period: 7 Tage bei Nicht-Erreichbarkeit
        if self.cache.get("checked") and not self.cache.get("grace_until"):
            self.cache["grace_until"] = (datetime.now() + timedelta(days=7)).isoformat()
            log.info("Lizenz-Server nicht erreichbar — 7 Tage Grace Period aktiv")
        elif self.cache.get("grace_until"):
            if datetime.now().isoformat() > self.cache["grace_until"]:
                self.cache["valid"] = False
                self.cache["type"] = "GRACE_EXPIRED"
                log.warning("Grace Period abgelaufen — Lizenz ungueltig")

    async def check_loop(self) -> None:
        """Hintergrund-Task: Prueft Lizenz alle 24h."""
        await self.verify()
        while True:
            await asyncio.sleep(86400)
            await self.verify()

    # ------------------------------------------------------------------
    # MA-Report (nur fuer PRO_MA_MONAT-Produkte)
    # ------------------------------------------------------------------
    async def report_usage(self) -> None:
        if not self.get_usage_count or not self.license_key:
            return
        try:
            count = self.get_usage_count()
        except Exception as e:
            log.warning(f"Usage-Count konnte nicht ermittelt werden: {e}")
            return
        if count is None:
            return
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                await client.post(
                    f"{self.license_server}/api/license/usage-report",
                    json={
                        "license_key": self.license_key,
                        "product_code": self.product_code,
                        "instance_id": self.get_instance_id(),
                        "mitarbeiter_anzahl": int(count),
                    },
                )
        except Exception as e:
            log.warning(f"Usage-Report fehlgeschlagen: {e}")

    async def usage_report_loop(self) -> None:
        """Meldet einmal pro Tag die aktuelle Nutzung. Server zaehlt Monats-Peak."""
        if not self.get_usage_count:
            return
        # Erster Report nach 60 Sekunden (damit App gestartet ist)
        await asyncio.sleep(60)
        await self.report_usage()
        while True:
            await asyncio.sleep(86400)
            await self.report_usage()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def has_feature(self, name: str) -> bool:
        return name in self.cache.get("features", [])

    # ------------------------------------------------------------------
    # Middleware
    # ------------------------------------------------------------------
    async def guard(self, request: Request, call_next):
        path = request.url.path
        if any(path.startswith(e) for e in self.exempt_paths) or path.startswith(
            "/static/produkt"
        ):
            return await call_next(request)
        if not self.cache.get("valid", True):
            if path.startswith("/api/"):
                raise HTTPException(status_code=403, detail="Lizenz abgelaufen oder ungueltig")
            return RedirectResponse("/lizenz")
        return await call_next(request)

    # ------------------------------------------------------------------
    # Routes
    # ------------------------------------------------------------------
    def register_routes(self, app: FastAPI) -> None:
        product_code = self.product_code
        product_name = self.product_name
        product_price = self.product_price
        license_server = self.license_server
        cache_ref = self.cache
        client = self

        @app.get("/lizenz")
        async def _lizenz_page():
            html = _LIZENZ_PAGE_TEMPLATE.format(
                product_name=product_name,
                product_code=product_code,
                product_price=product_price,
                license_server=license_server,
                cache_json=json.dumps(cache_ref),
            )
            return HTMLResponse(html)

        @app.get("/api/license/status")
        async def _license_status():
            return {
                **cache_ref,
                "product_code": product_code,
                "product_name": product_name,
                "instance_id": client.get_instance_id(),
                "has_key": bool(client.license_key),
            }

        @app.post("/api/license/install")
        async def _license_install(req: InstallRequest):
            """Empfaengt den Lizenzschluessel vom Buy-Widget und speichert ihn lokal.

            Der Key wird NUR gespeichert, wenn die Server-Pruefung valid=True zurueckgibt
            oder Status AKTIV/GESPERRT (GESPERRT = bestellt, Zahlungseingang steht aus).
            So kann ein Nutzer sich nicht versehentlich mit einem fremden/falschen Key aussperren.
            """
            if not req.license_key or len(req.license_key) < 20:
                raise HTTPException(status_code=400, detail="Ungueltiger Lizenzschluessel")
            # Vorab gegen den Server pruefen, OHNE den Key lokal zu speichern
            try:
                async with httpx.AsyncClient(timeout=10) as http:
                    r = await http.post(
                        f"{client.license_server}/api/license/verify",
                        json={
                            "license_key": req.license_key,
                            "product_code": client.product_code,
                            "instance_id": client.get_instance_id(),
                        },
                    )
                    if r.status_code != 200:
                        raise HTTPException(status_code=400, detail="Lizenz-Server nicht erreichbar")
                    data = r.json()
            except HTTPException:
                raise
            except Exception:
                raise HTTPException(status_code=503, detail="Lizenz-Server nicht erreichbar")

            accept = bool(data.get("valid")) or data.get("type") in ("AKTIV", "GESPERRT")
            if not accept:
                detail = data.get("error") or "Lizenz ungueltig"
                raise HTTPException(status_code=400, detail=detail)

            # Erst jetzt persistieren + Cache aktualisieren
            client.set_license_key(req.license_key)
            await client.verify()
            return {
                "ok": True,
                "valid": cache_ref.get("valid"),
                "type": cache_ref.get("type"),
                "expires": cache_ref.get("expires"),
            }


# ----------------------------------------------------------------------
# Lizenz-Seite (laedt das zentrale Buy-Widget vom LizenzServer)
# ----------------------------------------------------------------------

_LIZENZ_PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="de"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Lizenz — {product_name}</title>
<style>
:root{{--bg:#0a1929;--bg2:#0d2137;--bg3:#132f4c;--cyan:#00e5ff;--cyan2:#00b8d4;--green:#66bb6a;--yellow:#ffa726;--red:#ef5350;--text:#e0e0e0;--text2:#90a4ae;--r:10px}}
*{{margin:0;padding:0;box-sizing:border-box}}body{{font-family:'Segoe UI',system-ui,sans-serif;background:var(--bg);color:var(--text);min-height:100vh;display:flex;align-items:center;justify-content:center;padding:20px}}
a{{color:var(--cyan)}}.container{{width:100%;max-width:520px}}
.card{{background:var(--bg2);border:1px solid rgba(0,229,255,0.2);border-radius:var(--r);padding:32px;margin-bottom:16px}}
h1{{color:var(--cyan);font-size:1.4rem;margin-bottom:6px;text-align:center}}
.subtitle{{color:var(--text2);text-align:center;font-size:0.85rem;margin-bottom:20px}}
.status{{padding:12px;border-radius:6px;margin-bottom:16px;font-size:0.85rem;text-align:center}}
.status.trial{{background:rgba(0,229,255,0.1);border:1px solid rgba(0,229,255,0.3);color:var(--cyan)}}
.status.expired{{background:rgba(239,83,80,0.1);border:1px solid rgba(239,83,80,0.3);color:var(--red)}}
.status.active{{background:rgba(102,187,106,0.1);border:1px solid rgba(102,187,106,0.3);color:var(--green)}}
.status.pending{{background:rgba(255,167,38,0.1);border:1px solid rgba(255,167,38,0.3);color:var(--yellow)}}
.status.bound{{background:rgba(239,83,80,0.15);border:1px solid rgba(239,83,80,0.4);color:var(--red)}}
.btn{{width:100%;padding:12px;border:none;border-radius:6px;font-size:0.95rem;font-weight:600;cursor:pointer;background:var(--cyan);color:var(--bg)}}
.btn:hover{{background:var(--cyan2)}}
.btn-outline{{background:none;border:1px solid rgba(0,229,255,0.3);color:var(--text);display:inline-block;padding:8px 16px;border-radius:6px;text-decoration:none;font-size:0.85rem}}
.btn-outline:hover{{border-color:var(--cyan);color:var(--cyan)}}
.price-tag{{text-align:center;margin:10px 0}}
.price-tag .amount{{font-size:1.6rem;font-weight:700;color:var(--cyan)}}
.price-tag .detail{{color:var(--text2);font-size:0.75rem}}
.sep{{border-top:1px solid rgba(0,229,255,0.15);margin:18px 0}}
.manual-key{{margin-top:14px}}
.manual-key input{{width:100%;padding:9px 11px;background:var(--bg);border:1px solid rgba(0,229,255,0.2);border-radius:6px;color:var(--text);font-size:0.85rem;margin-bottom:8px;font-family:monospace}}
.err{{color:var(--red);font-size:0.8rem;margin-top:6px;display:none}}
.ok{{color:var(--green);font-size:0.8rem;margin-top:6px;display:none}}
</style></head>
<body><div class="container">
<div class="card">
<h1>{product_name}</h1>
<p class="subtitle">Lizenz-Verwaltung</p>
<div id="lic-status"></div>
<div class="price-tag"><div class="amount" id="price-display">ab {product_price} EUR</div><div class="detail" id="price-detail">pro Jahr zzgl. 19% USt.</div></div>
<div class="sep"></div>
<button class="btn" onclick="openBuyWidget()">Jetzt kaufen / Testen</button>
<div style="text-align:center;margin-top:10px"><a href="/" class="btn-outline">Zurueck zur App</a></div>
<div class="manual-key">
<details><summary style="color:var(--text2);font-size:0.8rem;cursor:pointer">Lizenzschluessel manuell eingeben</summary>
<div style="margin-top:10px">
<input id="manual-key" placeholder="eyJhbGciOi...">
<button class="btn" onclick="installKey()" style="font-size:0.85rem;padding:9px">Lizenz aktivieren</button>
<div class="err" id="key-err"></div>
<div class="ok" id="key-ok"></div>
</div>
</details>
</div>
</div>
</div>
<script>
const LS='{license_server}';
const PC='{product_code}';
const cache={cache_json};

function initStatus(){{
 const el=document.getElementById('lic-status');
 const t=cache.type,v=cache.valid,exp=cache.expires;
 if(cache.bound_to_other_instance){{
  el.innerHTML='<div class="status bound">Diese Lizenz ist bereits an eine andere Installation gebunden.<br><small>Bitte im Kunden-Portal die Lizenz umziehen.</small></div>';
 }} else if(t==='TRIAL'&&v){{
  const d=exp?Math.ceil((new Date(exp)-new Date())/86400000):0;
  el.innerHTML='<div class="status trial">Testversion — noch '+d+' Tage</div>';
 }} else if(t==='TRIAL_EXPIRED'||(!v&&t!=='AKTIV')){{
  el.innerHTML='<div class="status expired">Testversion abgelaufen</div>';
 }} else if(v){{
  el.innerHTML='<div class="status active">Lizenz aktiv'+(exp?' bis '+exp:' (unbegrenzt)')+'</div>';
 }} else if(t==='GESPERRT'){{
  el.innerHTML='<div class="status pending">Lizenz bestellt — Zahlung ausstehend</div>';
 }} else {{
  el.innerHTML='<div class="status expired">Keine gueltige Lizenz</div>';
 }}
}}

function openBuyWidget(){{
 if(window.C3POBuy){{
  window.C3POBuy.open({{
   productCode: PC,
   localInstallEndpoint: '/api/license/install',
   onSuccess: function(){{ setTimeout(()=>location.reload(), 1500); }}
  }});
 }} else {{
  alert('Buy-Widget konnte nicht geladen werden. Bitte Seite neu laden.');
 }}
}}

async function installKey(){{
 const key=document.getElementById('manual-key').value.trim();
 const errEl=document.getElementById('key-err'), okEl=document.getElementById('key-ok');
 errEl.style.display='none'; okEl.style.display='none';
 if(!key){{ errEl.textContent='Bitte Schluessel eingeben.'; errEl.style.display='block'; return; }}
 try{{
  const r=await fetch('/api/license/install',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{license_key:key}})}});
  const data=await r.json();
  if(!r.ok){{ errEl.textContent=data.detail||'Aktivierung fehlgeschlagen'; errEl.style.display='block'; return; }}
  if(data.valid){{ okEl.textContent='Lizenz aktiv!'; okEl.style.display='block'; setTimeout(()=>location.reload(),1500); }}
  else {{ errEl.textContent='Lizenz noch nicht aktiv (Zahlung ausstehend?)'; errEl.style.display='block'; }}
 }}catch(e){{ errEl.textContent='Verbindung fehlgeschlagen.'; errEl.style.display='block'; }}
}}

initStatus();
</script>
<script src="{license_server}/buy-widget.js" defer></script>
</body></html>"""
