import time
import json
import requests
import jwt  # PyJWT
from typing import List, Dict, Any

from api.notifications_mobile.config import get_fcm_project_id, get_fcm_sa_info


def mobile_notifications_health() -> Dict[str, Any]:
    """
    Health simple para el submódulo de notificaciones móviles.
    No hace requests externos; solo valida que la config esté cargable.
    """
    resp: Dict[str, Any] = {
        "ok": True,
        "service": "mobile_notifications",
        "status": "healthy",
    }
    try:
        project_id = get_fcm_project_id()
        resp["project_id_configured"] = bool(project_id)
        try:
            sa = get_fcm_sa_info()  # intenta leer/decodificar el SA (base64 o JSON)
            resp["sa_loaded"] = True
            resp["sa_client_email"] = sa.get("client_email")
        except Exception as e:
            resp["sa_loaded"] = False
            resp["error"] = f"SA load error: {str(e)}"
    except Exception as e:
        resp["project_id_configured"] = False
        resp["error"] = f"Config error: {str(e)}"
    return resp


def _get_google_oauth_token(sa_info: dict) -> str:
    """
    Intercambia un JWT firmado (service account) por un access_token OAuth2 de Google
    con scope de Firebase Cloud Messaging.
    """
    now = int(time.time())
    payload = {
        "iss": sa_info["client_email"],
        "scope": "https://www.googleapis.com/auth/firebase.messaging",
        "aud": "https://oauth2.googleapis.com/token",
        "iat": now,
        "exp": now + 3600,
    }
    additional_headers = {"kid": sa_info.get("private_key_id")}
    signed_jwt = jwt.encode(
        payload,
        sa_info["private_key"],
        algorithm="RS256",
        headers=additional_headers,
    )

    resp = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
            "assertion": signed_jwt,
        },
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["access_token"]


def mobile_send_push_fcm(
    tokens: List[str],
    title: str,
    body: str,
    data: Dict[str, Any] | None = None,
    android_channel_id: str | None = "smilestudio_default",
) -> Dict[str, Any]:
    """
    Envía notificaciones FCM (HTTP v1) a una lista de tokens.

    Retorna:
      {
        "sent": <int>,      # cantidad de envíos exitosos
        "errors": [ ... ]   # lista de errores por token (si hubo)
      }
    """
    if not tokens:
        return {"sent": 0, "errors": ["NO_TOKENS"]}

    project_id = get_fcm_project_id()
    sa_info = get_fcm_sa_info()
    access_token = _get_google_oauth_token(sa_info)

    url = f"https://fcm.googleapis.com/v1/projects/{project_id}/messages:send"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json; charset=UTF-8",
    }

    sent = 0
    errors: List[str] = []

    for tok in tokens:
        message: Dict[str, Any] = {
            "message": {
                "token": tok,
                "notification": {"title": title, "body": body},
                "data": {k: str(v) for (k, v) in (data or {}).items()},
                "android": {"priority": "HIGH"},
                "apns": {"headers": {"apns-priority": "10"}},
            }
        }

        if android_channel_id:
            message["message"].setdefault("android", {})
            message["message"]["android"]["notification"] = {
                "channel_id": android_channel_id,
                "sound": "default",
            }

        try:
            r = requests.post(url, headers=headers, data=json.dumps(message), timeout=15)
            if r.status_code in (200, 201):
                sent += 1
            else:
                errors.append(f"{tok[:12]}… -> {r.status_code}: {r.text[:200]}")
        except Exception as e:
            errors.append(f"{tok[:12]}… -> EXC: {str(e)[:200]}")

    return {"sent": sent, "errors": errors}
