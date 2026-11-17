#!/usr/bin/env python3
"""Minimal Zoho Books API client (stdlib only).

Credentials come from environment variables, never from files:
  ZOHO_CLIENT_ID, ZOHO_CLIENT_SECRET, ZOHO_REFRESH_TOKEN   (required)
  ZOHO_ORG_ID   (default 945108048 = OVO Consultants LLC)
  ZOHO_DC       (default "com"; US data center)

Usage:
  python3 zoho/zoho_client.py check      # read-only: token refresh + uncategorized counts
"""
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

DC = os.environ.get("ZOHO_DC", "com")
ORG_ID = os.environ.get("ZOHO_ORG_ID", "945108048")
ACCOUNTS = f"https://accounts.zoho.{DC}"
API = f"https://www.zohoapis.{DC}/books/v3"

_token = {"value": None, "expires": 0.0}


def _need(name):
    v = os.environ.get(name)
    if not v:
        sys.exit(f"Missing env var {name}. See zoho/README.md.")
    return v


_CACHE = os.environ.get("ZOHO_TOKEN_CACHE", "/tmp/zoho_token_cache.json")   # shared by every script on this machine; outside the repo


def _read_cache():
    try:
        d = json.load(open(_CACHE))
        if d.get("value") and time.time() < d.get("expires", 0) - 120:
            return d
    except Exception:
        pass
    return None


def access_token():
    """Return a cached access token (in-process, then shared on-disk cache), minting a new one only when stale.
    Zoho rate-limits token minting, so scripts must share one token instead of each asking for their own."""
    if _token["value"] and time.time() < _token["expires"] - 60:
        return _token["value"]
    d = _read_cache()
    if d:
        _token["value"], _token["expires"] = d["value"], d["expires"]
        return _token["value"]
    data = urllib.parse.urlencode({
        "grant_type": "refresh_token",
        "client_id": _need("ZOHO_CLIENT_ID"),
        "client_secret": _need("ZOHO_CLIENT_SECRET"),
        "refresh_token": _need("ZOHO_REFRESH_TOKEN"),
    }).encode()
    req = urllib.request.Request(f"{ACCOUNTS}/oauth/v2/token", data=data, method="POST")
    with urllib.request.urlopen(req, timeout=30) as r:
        body = json.load(r)
    if "access_token" not in body:
        sys.exit(f"Token refresh failed: {body.get('error', body)}")
    _token["value"] = body["access_token"]
    _token["expires"] = time.time() + int(body.get("expires_in", 3600))
    try:
        fd = os.open(_CACHE, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as f:
            json.dump({"value": _token["value"], "expires": _token["expires"]}, f)
    except Exception:
        pass
    return _token["value"]


def call(method, path, params=None, body=None, _retry=False):
    """Call a Books endpoint. organization_id is added automatically."""
    q = {"organization_id": ORG_ID, **(params or {})}
    url = f"{API}/{path.lstrip('/')}?{urllib.parse.urlencode(q)}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={
        "Authorization": f"Zoho-oauthtoken {access_token()}",
        "Content-Type": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        if e.code == 401 and not _retry:
            _token["value"] = None; _token["expires"] = 0.0          # token invalidated: drop caches, mint a fresh one, retry once
            try: os.remove(_CACHE)
            except Exception: pass
            return call(method, path, params, body, _retry=True)
        sys.exit(f"{method} {path} -> HTTP {e.code}: {e.read().decode()[:500]}")


def get(path, **params):
    return call("GET", path, params)


def check():
    """Read-only smoke test."""
    accts = get("bankaccounts", filter_by="Status.Active", per_page=200)["bankaccounts"]
    rows = sorted(accts, key=lambda a: -a.get("uncategorized_transactions", 0))
    total = sum(a.get("uncategorized_transactions", 0) for a in accts)
    print(f"OK: token works, org {ORG_ID}, {len(accts)} active accounts, {total} uncategorized lines\n")
    for a in rows:
        n = a.get("uncategorized_transactions", 0)
        if n:
            print(f"{n:>6}  {a['account_name']}")


if __name__ == "__main__":
    if sys.argv[1:] == ["check"]:
        check()
    else:
        sys.exit(__doc__)
