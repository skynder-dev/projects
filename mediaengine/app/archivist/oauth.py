from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import socket
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlparse

from .db import db, init_db
from .secret_store import delete_secret, get_secret, set_secret

SUPPORTED_PROVIDERS={"youtube","instagram","tiktok","facebook"}
DEFAULT_CALLBACK_PATH="/oauth/callback"

class OAuthError(RuntimeError):
    pass
class OAuthStateError(OAuthError):
    pass
class OAuthExpiredError(OAuthError):
    pass
class OAuthReplayError(OAuthError):
    pass
class OAuthProviderError(OAuthError):
    pass

def _utcnow():
    return datetime.now(timezone.utc)

def _iso(dt):
    return dt.astimezone(timezone.utc).isoformat()

def _parse_iso(value):
    return datetime.fromisoformat(str(value))

def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")

def new_state() -> str:
    return secrets.token_urlsafe(32)

def new_pkce_verifier() -> str:
    # token_urlsafe(64) is URL-safe and comfortably inside RFC 7636's 43-128 char range.
    value=secrets.token_urlsafe(64)
    return value[:128]

def pkce_challenge(verifier: str) -> str:
    value=str(verifier or "")
    if not (43 <= len(value) <= 128):
        raise ValueError("PKCE verifier length must be 43..128")
    return _b64url(hashlib.sha256(value.encode("ascii")).digest())

def state_sha256(state: str) -> str:
    return hashlib.sha256(str(state).encode("utf-8")).hexdigest()

def validate_loopback_redirect_uri(uri: str, callback_path: str = DEFAULT_CALLBACK_PATH) -> str:
    p=urlparse(str(uri))
    if p.scheme!="http" or p.hostname!="127.0.0.1" or p.port is None:
        raise ValueError("OAuth redirect must use http://127.0.0.1:<port>")
    if p.path!=callback_path:
        raise ValueError("Unexpected OAuth callback path")
    if p.username or p.password or p.fragment:
        raise ValueError("Invalid OAuth redirect URI")
    return p.geturl()

@contextmanager
def reserve_loopback_callback(callback_path: str = DEFAULT_CALLBACK_PATH):
    s=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
    s.bind(("127.0.0.1",0))
    s.listen(1)
    try:
        port=int(s.getsockname()[1])
        yield {"socket":s,"redirect_uri":f"http://127.0.0.1:{port}{callback_path}","port":port,"host":"127.0.0.1"}
    finally:
        s.close()

def parse_loopback_callback(url: str, callback_path: str = DEFAULT_CALLBACK_PATH) -> dict:
    p=urlparse(str(url))
    validate_loopback_redirect_uri(f"{p.scheme}://{p.netloc}{p.path}",callback_path)
    q=parse_qs(p.query,keep_blank_values=True)
    def one(name):
        vals=q.get(name) or []
        return vals[0] if len(vals)==1 else (None if not vals else vals[0])
    return {"state":one("state"),"code":one("code"),"error":one("error"),"error_description":one("error_description")}

def begin_oauth_attempt(provider: str, redirect_uri: str, scopes, ttl_seconds: int = 600) -> dict:
    init_db()
    provider=str(provider or "").strip().lower()
    if provider not in SUPPORTED_PROVIDERS:
        raise ValueError("Unsupported OAuth provider")
    redirect_uri=validate_loopback_redirect_uri(redirect_uri)
    scopes=[str(x).strip() for x in (scopes or []) if str(x).strip()]
    attempt_id=secrets.token_hex(16)
    state=new_state()
    verifier=new_pkce_verifier()
    verifier_ref=f"oauth/attempt/{attempt_id}/verifier"
    created=_utcnow()
    expires=created+timedelta(seconds=int(ttl_seconds))
    set_secret(verifier_ref,verifier)
    try:
        with db() as con:
            con.execute(
                """INSERT INTO social_oauth_attempts(
                    id,provider,state_sha256,verifier_secret_ref,redirect_uri,scopes_json,
                    created_at,expires_at,status,terminal_error
                ) VALUES(?,?,?,?,?,?,?,?,?,NULL)""",
                (attempt_id,provider,state_sha256(state),verifier_ref,redirect_uri,json.dumps(scopes,separators=(",",":")),_iso(created),_iso(expires),"pending")
            )
            con.commit()
    except Exception:
        delete_secret(verifier_ref)
        raise
    return {
        "attempt_id":attempt_id,
        "provider":provider,
        "state":state,
        "code_challenge":pkce_challenge(verifier),
        "code_challenge_method":"S256",
        "redirect_uri":redirect_uri,
        "scopes":scopes,
        "expires_at":_iso(expires),
    }

def _finish_attempt(con, attempt_id: str, status: str, terminal_error: str | None = None):
    con.execute("UPDATE social_oauth_attempts SET status=?,terminal_error=? WHERE id=?",(status,terminal_error,attempt_id))

def consume_loopback_callback(attempt_id: str, callback_url: str) -> dict:
    init_db()
    parsed=parse_loopback_callback(callback_url)
    with db() as con:
        row=con.execute("SELECT * FROM social_oauth_attempts WHERE id=?",(str(attempt_id),)).fetchone()
        if not row:
            raise OAuthError("OAuth attempt not found")
        if row["status"]!="pending":
            raise OAuthReplayError("OAuth attempt is no longer pending")
        if _utcnow() > _parse_iso(row["expires_at"]):
            _finish_attempt(con,attempt_id,"expired","expired")
            con.commit()
            delete_secret(row["verifier_secret_ref"])
            raise OAuthExpiredError("OAuth attempt expired")
        returned_state=parsed.get("state") or ""
        if not hmac.compare_digest(state_sha256(returned_state),str(row["state_sha256"])):
            raise OAuthStateError("OAuth state mismatch")
        if parsed.get("error"):
            _finish_attempt(con,attempt_id,"provider_error",str(parsed.get("error"))[:120])
            con.commit()
            delete_secret(row["verifier_secret_ref"])
            raise OAuthProviderError(str(parsed.get("error")))
        code=str(parsed.get("code") or "")
        if not code:
            _finish_attempt(con,attempt_id,"failed","missing_code")
            con.commit()
            delete_secret(row["verifier_secret_ref"])
            raise OAuthError("OAuth callback did not contain a code")
        verifier=get_secret(row["verifier_secret_ref"])
        if not verifier:
            _finish_attempt(con,attempt_id,"failed","verifier_missing")
            con.commit()
            raise OAuthError("PKCE verifier is unavailable")
        _finish_attempt(con,attempt_id,"consumed",None)
        con.commit()
        delete_secret(row["verifier_secret_ref"])
        return {
            "provider":row["provider"],
            "authorization_code":code,
            "pkce_verifier":verifier,
            "redirect_uri":row["redirect_uri"],
            "scopes":json.loads(row["scopes_json"] or "[]"),
        }

def abort_oauth_attempt(attempt_id: str) -> bool:
    init_db()
    with db() as con:
        row=con.execute("SELECT status,verifier_secret_ref FROM social_oauth_attempts WHERE id=?",(str(attempt_id),)).fetchone()
        if not row:
            return False
        if row["status"]=="pending":
            _finish_attempt(con,attempt_id,"aborted","aborted")
            con.commit()
        delete_secret(row["verifier_secret_ref"])
        return True
