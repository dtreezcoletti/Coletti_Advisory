from __future__ import annotations

import json
import os

import requests
import streamlit as st
from starlette.applications import Starlette
from starlette.responses import HTMLResponse, JSONResponse, Response
from starlette.routing import Mount, Route


ICON_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">
<rect width="512" height="512" rx="104" fill="#F2EEE5"/>
<circle cx="256" cy="256" r="174" fill="none" stroke="#35312C" stroke-width="18"/>
<path d="M331 174c-25-23-54-34-87-34-68 0-119 50-119 116s51 116 119 116c34 0 64-11 89-34l-31-38c-16 14-34 21-56 21-39 0-67-27-67-65s28-65 67-65c21 0 39 7 55 21z" fill="#35312C"/>
<path d="M329 174h43v164h-43z" fill="#B08A4A"/>
</svg>"""


AUTH_PAGE_STYLE = """
:root{color-scheme:light}*{box-sizing:border-box}body{margin:0;background:#f2eee5;color:#302c28;font-family:Georgia,'Times New Roman',serif;min-height:100vh;display:grid;place-items:center;padding:24px}.card{width:min(560px,100%);background:#faf8f3;border:1px solid #d8d0c2;padding:34px;border-radius:8px;box-shadow:0 16px 50px rgba(40,35,30,.08)}.mark{width:64px;height:64px;margin-bottom:22px}.over{font:600 11px/1.2 Arial,sans-serif;letter-spacing:.22em;text-transform:uppercase;color:#8b7651}.title{font-size:38px;line-height:1.05;margin:8px 0 12px}.copy,.status{font:15px/1.6 Arial,sans-serif;color:#6c655c}.field{margin:18px 0}.field label{display:block;font:600 13px/1.4 Arial,sans-serif;margin-bottom:8px}.field input{width:100%;padding:14px 15px;border:1px solid #cbc2b4;background:#fffdf8;border-radius:4px;font:16px Arial,sans-serif}.button{width:100%;padding:15px 18px;background:#302c28;color:#fff;border:0;font:600 13px/1 Arial,sans-serif;letter-spacing:.08em;text-transform:uppercase;border-radius:3px}.button:disabled{opacity:.55}.link{display:block;margin-top:18px;text-align:center;color:#6c655c;font:13px Arial,sans-serif}.status{margin-top:18px;padding:12px;border:1px solid #d8d0c2;background:#fffdf8;display:none}.error{border-color:#c99b94;background:#fbefec;color:#7e3129}.success{border-color:#9caf98;background:#f0f5ee;color:#36523a}
"""


def _supabase_url() -> str:
    return os.getenv("SUPABASE_URL", "").rstrip("/")


def _supabase_key() -> str:
    return os.getenv("SUPABASE_PUBLISHABLE_KEY") or os.getenv("SUPABASE_ANON_KEY", "")


async def landing(_request):
    return HTMLResponse(
        """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#2f2b27">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<meta name="apple-mobile-web-app-title" content="ColettiOS">
<link rel="manifest" href="/manifest.webmanifest">
<link rel="icon" href="/pwa-icon.svg" type="image/svg+xml">
<title>ColettiOS</title>
<style>
:root{color-scheme:light}*{box-sizing:border-box}body{margin:0;background:#f2eee5;color:#302c28;font-family:Georgia,'Times New Roman',serif;min-height:100vh;display:grid;place-items:center;padding:24px}.card{width:min(560px,100%);background:#faf8f3;border:1px solid #d8d0c2;padding:38px;border-radius:8px;box-shadow:0 16px 50px rgba(40,35,30,.08)}.mark{width:72px;height:72px;margin-bottom:28px}.over{font:600 11px/1.2 Arial,sans-serif;letter-spacing:.22em;text-transform:uppercase;color:#8b7651}.title{font-size:42px;line-height:1.02;margin:8px 0 12px}.copy{font:15px/1.6 Arial,sans-serif;color:#6c655c;margin-bottom:28px}.button{display:block;width:100%;padding:15px 18px;background:#302c28;color:#fff;text-decoration:none;text-align:center;font:600 13px/1 Arial,sans-serif;letter-spacing:.08em;text-transform:uppercase;border-radius:3px}.note{font:12px/1.5 Arial,sans-serif;color:#81786d;margin-top:18px}.install{display:none;margin-top:12px;width:100%;padding:14px 18px;background:transparent;color:#302c28;border:1px solid #a9987c;font:600 13px/1 Arial,sans-serif;letter-spacing:.06em;text-transform:uppercase;border-radius:3px}</style>
</head>
<body>
<main class="card">
<img class="mark" src="/pwa-icon.svg" alt="ColettiOS">
<div class="over">Owner Operating Environment</div>
<div class="title">ColettiOS</div>
<div class="copy">Authenticated Owner Console for institutional control, private owner work, Dispatcher, DARI, and continuity.</div>
<a class="button" href="/app/">Open Owner Console</a>
<button class="install" id="installButton">Install ColettiOS</button>
<div class="note" id="installNote">On Android, Chrome can install this as a standalone app. If the install button is not shown, open Chrome's menu and choose <strong>Install app</strong> or <strong>Add to Home screen</strong>.</div>
</main>
<script>
if ('serviceWorker' in navigator) { navigator.serviceWorker.register('/sw.js', {scope:'/'}).catch(()=>{}); }
let deferredPrompt;
const button=document.getElementById('installButton');
window.addEventListener('beforeinstallprompt',(event)=>{event.preventDefault();deferredPrompt=event;button.style.display='block';});
button.addEventListener('click',async()=>{if(!deferredPrompt)return;deferredPrompt.prompt();await deferredPrompt.userChoice;deferredPrompt=null;button.style.display='none';});
if(window.matchMedia('(display-mode: standalone)').matches){window.location.replace('/app/');}
</script>
</body>
</html>""",
        headers={"Cache-Control": "no-store"},
    )


async def forgot_password(_request):
    return HTMLResponse(
        f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><meta name="theme-color" content="#2f2b27"><title>Reset ColettiOS password</title><style>{AUTH_PAGE_STYLE}</style></head><body>
<main class="card"><img class="mark" src="/pwa-icon.svg" alt="ColettiOS"><div class="over">Secure Account Recovery</div><div class="title">Forgot password?</div><div class="copy">Enter the email address for your ColettiOS account. We will ask Supabase Auth to send a secure recovery email.</div>
<div class="field"><label for="email">Email</label><input id="email" type="email" autocomplete="email" inputmode="email" value="dtreezcoletti@gmail.com"></div><button class="button" id="send">Send reset email</button><div class="status" id="status"></div><a class="link" href="/app/">Back to login</a></main>
<script>
const send=document.getElementById('send'), status=document.getElementById('status');
function show(msg,kind){{status.textContent=msg;status.className='status '+kind;status.style.display='block';}}
send.addEventListener('click',async()=>{{const email=document.getElementById('email').value.trim();if(!email){{show('Enter your email address.','error');return;}}send.disabled=true;try{{const r=await fetch('/api/password-reset-request',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{email}})}});const d=await r.json();show(d.message||'Check your email.',''+(r.ok?'success':'error'));}}catch(e){{show('Could not send the reset request. Try again.','error');}}finally{{send.disabled=false;}}}});
</script></body></html>""",
        headers={"Cache-Control": "no-store"},
    )


async def reset_password(_request):
    return HTMLResponse(
        f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><meta name="theme-color" content="#2f2b27"><title>Choose new ColettiOS password</title><style>{AUTH_PAGE_STYLE}</style></head><body>
<main class="card"><img class="mark" src="/pwa-icon.svg" alt="ColettiOS"><div class="over">Secure Account Recovery</div><div class="title">Choose a new password</div><div class="copy" id="intro">Use the secure recovery link from your email, then choose a new password below.</div><div id="form" style="display:none"><div class="field"><label for="password">New password</label><input id="password" type="password" autocomplete="new-password" minlength="12"></div><div class="field"><label for="confirm">Confirm new password</label><input id="confirm" type="password" autocomplete="new-password" minlength="12"></div><button class="button" id="save">Change password</button></div><div class="status" id="status"></div><a class="link" href="/app/">Back to login</a></main>
<script>
const params=new URLSearchParams(location.hash.replace(/^#/,''));const query=new URLSearchParams(location.search);const token=params.get('access_token')||query.get('access_token');const type=params.get('type')||query.get('type');const form=document.getElementById('form'),status=document.getElementById('status');
function show(msg,kind){{status.textContent=msg;status.className='status '+kind;status.style.display='block';}}
if(token && (!type || type==='recovery')){{form.style.display='block';}}else{{show('This reset link is missing or expired. Go back to login and request a new reset email.','error');}}
document.getElementById('save').addEventListener('click',async()=>{{const p=document.getElementById('password').value,c=document.getElementById('confirm').value;if(p.length<12){{show('Use at least 12 characters.','error');return;}}if(p!==c){{show('The passwords do not match.','error');return;}}const b=document.getElementById('save');b.disabled=true;try{{const r=await fetch('/api/password-update',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{access_token:token,password:p}})}});const d=await r.json();if(r.ok){{form.style.display='none';show('Password changed. You can now return to ColettiOS and log in with the new password.','success');history.replaceState(null,'','/reset-password');}}else{{show(d.message||'Could not change the password. Request a new reset email.','error');}}}}catch(e){{show('Could not change the password. Try again.','error');}}finally{{b.disabled=false;}}}});
</script></body></html>""",
        headers={"Cache-Control": "no-store"},
    )


async def password_reset_request(request):
    if not _supabase_url() or not _supabase_key():
        return JSONResponse({"message": "Password recovery is not configured."}, status_code=503)
    try:
        payload = await request.json()
    except Exception:
        return JSONResponse({"message": "Enter a valid email address."}, status_code=400)
    email = str(payload.get("email") or "").strip().lower()
    if "@" not in email or len(email) > 254:
        return JSONResponse({"message": "Enter a valid email address."}, status_code=400)
    origin = str(request.base_url).rstrip("/")
    try:
        response = requests.post(
            f"{_supabase_url()}/auth/v1/recover",
            headers={"apikey": _supabase_key(), "Content-Type": "application/json"},
            json={"email": email, "redirect_to": f"{origin}/reset-password"},
            timeout=20,
        )
    except requests.RequestException:
        return JSONResponse({"message": "Could not reach the authentication service. Try again."}, status_code=502)
    if response.status_code >= 400:
        return JSONResponse({"message": "Supabase could not send the reset email. The recovery redirect may still need to be approved."}, status_code=400)
    return JSONResponse({"message": "Reset email requested. Check your inbox and spam folder."})


async def password_update(request):
    if not _supabase_url() or not _supabase_key():
        return JSONResponse({"message": "Password recovery is not configured."}, status_code=503)
    try:
        payload = await request.json()
    except Exception:
        return JSONResponse({"message": "Invalid reset request."}, status_code=400)
    token = str(payload.get("access_token") or "").strip()
    password = str(payload.get("password") or "")
    if not token or len(password) < 12:
        return JSONResponse({"message": "The reset token is missing or the password is too short."}, status_code=400)
    try:
        response = requests.put(
            f"{_supabase_url()}/auth/v1/user",
            headers={"apikey": _supabase_key(), "Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={"password": password},
            timeout=20,
        )
    except requests.RequestException:
        return JSONResponse({"message": "Could not reach the authentication service. Try again."}, status_code=502)
    if response.status_code >= 400:
        return JSONResponse({"message": "The reset link is invalid or expired. Request a new reset email."}, status_code=400)
    return JSONResponse({"message": "Password changed successfully."})


async def manifest(_request):
    payload = {
        "id": "/",
        "name": "ColettiOS Owner Console",
        "short_name": "ColettiOS",
        "description": "Authenticated ColettiOS Owner Console",
        "start_url": "/app/",
        "scope": "/",
        "display": "standalone",
        "orientation": "any",
        "background_color": "#F2EEE5",
        "theme_color": "#2F2B27",
        "icons": [{"src": "/pwa-icon.svg", "sizes": "any", "type": "image/svg+xml", "purpose": "any maskable"}],
    }
    return Response(json.dumps(payload), media_type="application/manifest+json", headers={"Cache-Control": "no-store"})


async def service_worker(_request):
    script = """self.addEventListener('install', event => { self.skipWaiting(); });
self.addEventListener('activate', event => { event.waitUntil(self.clients.claim()); });
// Authenticated ColettiOS pages are deliberately not cached by the service worker.
self.addEventListener('fetch', event => {});
"""
    return Response(script, media_type="application/javascript", headers={"Cache-Control": "no-store", "Service-Worker-Allowed": "/"})


async def icon(_request):
    return Response(ICON_SVG, media_type="image/svg+xml", headers={"Cache-Control": "public, max-age=86400"})


async def health(_request):
    return JSONResponse({"ok": True, "service": "colettios-owner-pwa"})


streamlit_app = st.App("owner_pwa_streamlit.py")

app = Starlette(
    routes=[
        Route("/", landing),
        Route("/forgot-password", forgot_password),
        Route("/reset-password", reset_password),
        Route("/api/password-reset-request", password_reset_request, methods=["POST"]),
        Route("/api/password-update", password_update, methods=["POST"]),
        Route("/manifest.webmanifest", manifest),
        Route("/sw.js", service_worker),
        Route("/pwa-icon.svg", icon),
        Route("/healthz", health),
        Mount("/app", app=streamlit_app),
    ],
    lifespan=streamlit_app.lifespan(),
)
