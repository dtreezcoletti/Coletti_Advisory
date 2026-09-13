from __future__ import annotations

import json

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
        "icons": [
            {
                "src": "/pwa-icon.svg",
                "sizes": "any",
                "type": "image/svg+xml",
                "purpose": "any maskable",
            }
        ],
    }
    return Response(
        json.dumps(payload),
        media_type="application/manifest+json",
        headers={"Cache-Control": "no-store"},
    )


async def service_worker(_request):
    script = """self.addEventListener('install', event => { self.skipWaiting(); });
self.addEventListener('activate', event => { event.waitUntil(self.clients.claim()); });
// Authenticated ColettiOS pages are deliberately not cached by the service worker.
self.addEventListener('fetch', event => {});
"""
    return Response(
        script,
        media_type="application/javascript",
        headers={
            "Cache-Control": "no-store",
            "Service-Worker-Allowed": "/",
        },
    )


async def icon(_request):
    return Response(ICON_SVG, media_type="image/svg+xml", headers={"Cache-Control": "public, max-age=86400"})


async def health(_request):
    return JSONResponse({"ok": True, "service": "colettios-owner-pwa"})


streamlit_app = st.App("owner_pwa_streamlit.py")

app = Starlette(
    routes=[
        Route("/", landing),
        Route("/manifest.webmanifest", manifest),
        Route("/sw.js", service_worker),
        Route("/pwa-icon.svg", icon),
        Route("/healthz", health),
        Mount("/app", app=streamlit_app),
    ],
    lifespan=streamlit_app.lifespan(),
)
