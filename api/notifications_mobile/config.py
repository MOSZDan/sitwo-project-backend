# api/notifications_mobile/config.py
import os
import json
import base64
from functools import lru_cache


class _ConfigError(RuntimeError):
    pass


@lru_cache(maxsize=1)
def get_fcm_project_id() -> str:
    try:
        return os.environ["FCM_PROJECT_ID"].strip()
    except KeyError as e:
        raise _ConfigError("Falta variable de entorno FCM_PROJECT_ID") from e


@lru_cache(maxsize=1)
def get_fcm_sa_info() -> dict:
    """
    Devuelve el dict del service-account.json decodificado desde FCM_SA_JSON_B64.
    """
    try:
        b64 = os.environ["FCM_SA_JSON_B64"]
    except KeyError as e:
        raise _ConfigError("Falta variable de entorno FCM_SA_JSON_B64") from e

    try:
        raw = base64.b64decode(b64).decode("utf-8")
        data = json.loads(raw)
        # sanity checks mínimos
        _ = data["client_email"]
        _ = data["private_key"]
        _ = data["project_id"]
        return data
    except Exception as e:
        raise _ConfigError("FCM_SA_JSON_B64 inválido o mal decodificado") from e
