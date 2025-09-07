# api/supabase_client.py
import os
import requests

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")

if not SUPABASE_URL:
    raise RuntimeError("Falta SUPABASE_URL en .env")
if not SUPABASE_ANON_KEY:
    raise RuntimeError("Falta SUPABASE_ANON_KEY en .env (anon public key)")

COMMON_HEADERS = {
    "apikey": SUPABASE_ANON_KEY,
    "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
    "Content-Type": "application/json",
}

class SupabaseAuthError(Exception):
    """Error de autenticación/reportado por Supabase"""
    def __init__(self, payload):
        super().__init__(str(payload))
        self.payload = payload

def supabase_signup(email: str, password: str, metadata: dict | None = None) -> dict:
    """
    Crea un usuario en Supabase Auth.
    Si tu proyecto exige verificación de email, no dará sesión hasta confirmar.
    Devuelve el JSON de Supabase (contiene "user" y, según política, "session").
    """
    payload = {"email": email, "password": password}
    if metadata:
        payload["data"] = metadata

    r = requests.post(
        f"{SUPABASE_URL}/auth/v1/signup",
        headers=COMMON_HEADERS,
        json=payload,
        timeout=15,
    )
    try:
        data = r.json()
    except Exception:
        data = {"raw": r.text}

    if r.status_code >= 400:
        raise SupabaseAuthError(data)
    return data

def supabase_password_grant(email: str, password: str) -> dict:
    """
    Inicia sesión (password grant). Devuelve access_token/refresh_token y user.
    """
    r = requests.post(
        f"{SUPABASE_URL}/auth/v1/token?grant_type=password",
        headers=COMMON_HEADERS,
        json={"email": email, "password": password},
        timeout=15,
    )
    try:
        data = r.json()
    except Exception:
        data = {"raw": r.text}

    if r.status_code != 200:
        raise SupabaseAuthError(data)
    return data
