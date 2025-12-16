# main.py
import os
import base64
import json
import secrets
import time
from urllib.parse import urlencode

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware


load_dotenv()

CLIENT_ID = os.getenv("PINTEREST_CLIENT_ID")
CLIENT_SECRET = os.getenv("PINTEREST_CLIENT_SECRET")
REDIRECT_URI = os.getenv("PINTEREST_REDIRECT_URI", "http://localhost:8000/auth/callback")
SCOPES = os.getenv("PINTEREST_SCOPES", "pins:read,pins:write,boards:read")
FRONTEND_SUCCESS = os.getenv("FRONTEND_SUCCESS_URL", "http://localhost:3000/auth/success")

if not CLIENT_ID or not CLIENT_SECRET:
    raise RuntimeError("Set PINTEREST_CLIENT_ID and PINTEREST_CLIENT_SECRET in .env")

TOKEN_URL = "https://api.pinterest.com/v5/oauth/token"
API_BASE = "https://api.pinterest.com/v5"
TOKEN_FILE = os.getenv("TOKEN_FILE", "tokens.json")

app = FastAPI(title="Pinterest OAuth Demo (no DB)")


# allow local dev from Next
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["GET","POST","OPTIONS"],
    allow_headers=["*"],
)

# lightweight state store (in-memory)
state_store = {}

def basic_auth_header():
    creds = f"{CLIENT_ID}:{CLIENT_SECRET}".encode()
    b64 = base64.b64encode(creds).decode()
    return {"Authorization": f"Basic {b64}", "Content-Type": "application/x-www-form-urlencoded"}

def save_tokens(token_json: dict):
    # add computed expires_at
    now = time.time()
    expires_in = token_json.get("expires_in")
    token_json["obtained_at"] = now
    token_json["expires_at"] = now + expires_in if expires_in else None
    with open(TOKEN_FILE, "w") as f:
        json.dump(token_json, f, indent=2)

def load_tokens():
    try:
        with open(TOKEN_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return None

def refresh_tokens_if_needed(token_json: dict):
    # returns updated token_json or False on failure
    if not token_json:
        return False
    # if no refresh token, can't refresh
    refresh_token = token_json.get("refresh_token")
    if not refresh_token:
        return False
    expires_at = token_json.get("expires_at")
    # refresh when expired or within 60s
    if expires_at and expires_at > time.time() + 60:
        return token_json  # still valid
    payload = {"grant_type": "refresh_token", "refresh_token": refresh_token}
    headers = basic_auth_header()
    r = requests.post(TOKEN_URL, data=payload, headers=headers, timeout=15)
    if r.status_code != 200:
        return False
    new = r.json()
    # merge: keep refresh_token if not provided
    if "refresh_token" not in new:
        new["refresh_token"] = refresh_token
    save_tokens(new)
    return new

@app.get("/auth/start")
def auth_start():
    state = secrets.token_urlsafe(16)
    state_store[state] = {"ts": time.time()}
    params = {
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPES,
        "state": state,
    }
    url = "https://www.pinterest.com/oauth/?" + urlencode(params)
    return RedirectResponse(url)


@app.post("/logout")
def logout():
    # demo: delete token file to "disconnect"
    try:
        if os.path.exists(TOKEN_FILE):
            os.remove(TOKEN_FILE)
    except Exception:
        pass
    return {"ok": True}


@app.get("/auth/callback")
def auth_callback(request: Request):
    params = request.query_params
    error = params.get("error")
    if error:
        raise HTTPException(status_code=400, detail=f"OAuth error: {error}")

    code = params.get("code")
    state = params.get("state")
    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing code or state")
    if state not in state_store:
        raise HTTPException(status_code=400, detail="Invalid or expired state")
    # remove state to prevent reuse
    state_store.pop(state, None)

    payload = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
    }
    headers = basic_auth_header()
    resp = requests.post(TOKEN_URL, data=payload, headers=headers, timeout=15)
    if resp.status_code != 200:
        raise HTTPException(status_code=500, detail=f"Token exchange failed: {resp.status_code} {resp.text}")

    token_data = resp.json()
    save_tokens(token_data)

    return RedirectResponse(f"{FRONTEND_SUCCESS}?status=ok")

@app.get("/tokens")
def get_tokens():
    t = load_tokens()
    if not t:
        return {"error": "no tokens saved yet"}
    # return limited fields for demo
    return {
        "has_tokens": True,
        "scopes": t.get("scope") or SCOPES,
        "expires_at": t.get("expires_at"),
        "pinterest_user_id": t.get("user_id") or None,
    }

@app.get("/boards")
def list_boards():
    t = load_tokens()
    if not t:
        raise HTTPException(status_code=404, detail="no tokens stored")
    # refresh if needed
    updated = refresh_tokens_if_needed(t)
    if not updated:
        # maybe still valid if t had access_token and not expired
        if not t.get("access_token"):
            raise HTTPException(status_code=401, detail="No access token and refresh failed")
    else:
        t = updated

    headers = {"Authorization": f"Bearer {t.get('access_token')}"}
    r = requests.get(f"{API_BASE}/boards", headers=headers, timeout=10)
    if r.status_code == 401:
        # try refresh once
        new = refresh_tokens_if_needed(t)
        if not new:
            raise HTTPException(status_code=401, detail="Unauthorized - refresh failed")
        headers = {"Authorization": f"Bearer {new.get('access_token')}"}
        r = requests.get(f"{API_BASE}/boards", headers=headers, timeout=10)

    if r.status_code != 200:
        raise HTTPException(status_code=r.status_code, detail=f"Pinterest API error: {r.text}")
    return JSONResponse(status_code=200, content=r.json())
