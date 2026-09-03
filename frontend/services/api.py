"""Centralized HTTP client for the Streamlit frontend.

All backend requests flow through here so that authentication headers,
timeouts, URLs and error handling live in a single place instead of being
duplicated across pages.
"""
import os

import requests
import streamlit as st

API_URL = os.getenv("API_URL", "http://localhost:8000")
DEFAULT_TIMEOUT = 90
DOWNLOAD_TIMEOUT = 30

_SERVER_UNAVAILABLE = "Servidor indisponível. Verifique se o backend está rodando."
_SESSION_EXPIRED = "Sessão expirada. Clique em 'Sair da conta' e faça login novamente."


def get_auth_headers() -> dict:
    headers = {}
    token = st.session_state.get("token")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def request(method: str, path: str, timeout: int = DEFAULT_TIMEOUT, **kwargs) -> "requests.Response | None":
    """Low-level request executor.

    Returns the ``requests.Response`` on success and ``None`` when the server
    is unreachable. HTTP error statuses are handled by the caller-level
    helpers (``api_call`` / ``api_download``).
    """
    url = f"{API_URL}{path}"
    kwargs.setdefault("headers", {})
    kwargs["headers"].update(get_auth_headers())
    try:
        return getattr(requests, method)(url, timeout=timeout, **kwargs)
    except requests.ConnectionError:
        st.error(_SERVER_UNAVAILABLE)
        return None
    except Exception as e:  # noqa: BLE001 - any request failure surfaces as an error
        st.error(f"Erro: {e}")
        return None


def api_call(method: str, path: str, **kwargs):
    """Perform an API call that expects a JSON response.

    Returns the parsed JSON body (``dict``/``list``) or ``None`` on any
    failure, showing a Streamlit error to the user. This is the contract every
    page relies on.
    """
    response = request(method, path, **kwargs)
    if response is None:
        return None
    if response.status_code >= 400:
        try:
            detail = response.json().get("detail", f"Erro HTTP {response.status_code}")
        except (ValueError, AttributeError):
            detail = f"Erro HTTP {response.status_code}"
        if response.status_code == 401:
            detail = _SESSION_EXPIRED
        st.error(detail)
        return None
    try:
        return response.json()
    except (ValueError, AttributeError):
        st.error("Erro: resposta inválida do servidor")
        return None


def api_download(path: str, payload: dict, timeout: int = DOWNLOAD_TIMEOUT) -> "requests.Response | None":
    """Perform an authenticated request that returns a binary response.

    Returns the full ``requests.Response`` (caller reads ``.content``) or
    ``None`` on failure. Used by the report exports.
    """
    response = request("post", path, timeout=timeout, json=payload)
    return response
