"""AGENTE PUBLICADOR — sobe o post no Instagram pela API oficial da Meta.

Fluxo da API: cria o contêiner de mídia -> espera processar -> publica.
"""
from __future__ import annotations

import logging
import time

import requests

from ..config import Conta

log = logging.getLogger("publicador")


class ErroInstagram(RuntimeError):
    pass


def _base(conta: Conta) -> str:
    ig = conta["instagram"]
    return f"https://{ig.get('api_host', 'graph.facebook.com')}/{ig.get('api_versao', 'v23.0')}"


def _checar(r: requests.Response) -> dict:
    try:
        dados = r.json()
    except ValueError:
        raise ErroInstagram(f"HTTP {r.status_code}: {r.text[:300]}")
    if r.status_code >= 400 or "error" in dados:
        raise ErroInstagram(dados.get("error", {}).get("message", str(dados))[:400])
    return dados


def publicar(conta: Conta, image_url: str, legenda: str, alt_text: str = "") -> str:
    token = conta.segredo("instagram", "env_token")
    user_id = conta.segredo("instagram", "env_user_id")
    base = _base(conta)

    dados = {"image_url": image_url, "caption": legenda, "access_token": token}
    if alt_text:
        dados["alt_text"] = alt_text
    r = requests.post(f"{base}/{user_id}/media", data=dados, timeout=60)
    try:
        container = _checar(r)["id"]
    except ErroInstagram as e:
        if alt_text and "alt_text" in str(e):
            dados.pop("alt_text")
            container = _checar(requests.post(f"{base}/{user_id}/media", data=dados, timeout=60))["id"]
        else:
            raise

    for _ in range(20):
        st = _checar(requests.get(f"{base}/{container}",
                                  params={"fields": "status_code", "access_token": token}, timeout=30))
        if st.get("status_code") == "FINISHED":
            break
        if st.get("status_code") == "ERROR":
            raise ErroInstagram("Instagram não conseguiu processar a imagem")
        time.sleep(3)

    pub = _checar(requests.post(f"{base}/{user_id}/media_publish",
                                data={"creation_id": container, "access_token": token}, timeout=60))
    log.info("Publicado no Instagram: %s", pub["id"])
    return pub["id"]


def renovar_token(conta: Conta) -> str:
    """Só para tokens de login do Instagram (graph.instagram.com, 60 dias).
    Tokens de usuário do sistema (graph.facebook.com) não expiram e não usam isto."""
    if not conta["instagram"].get("renovar_token", False):
        raise RuntimeError("Esta conta usa token que não expira — renovação desnecessária")
    import os
    token = os.environ.get("IG_TOKEN_ATUAL") or conta.segredo("instagram", "env_token")
    r = requests.get("https://graph.instagram.com/refresh_access_token",
                     params={"grant_type": "ig_refresh_token", "access_token": token}, timeout=30)
    return _checar(r)["access_token"]


def testar_conexao(conta: Conta) -> None:
    """Confere token e conta sem publicar nada."""
    token = conta.segredo("instagram", "env_token")
    user_id = conta.segredo("instagram", "env_user_id")
    base = _base(conta)
    try:
        info = _checar(requests.get(f"{base}/{user_id}",
                                    params={"fields": "username,followers_count,media_count",
                                            "access_token": token}, timeout=30))
        print(f"✅ Conectado como @{info.get('username')} "
              f"({info.get('followers_count', '?')} seguidores, {info.get('media_count', '?')} posts)")
        lim = _checar(requests.get(f"{base}/{user_id}/content_publishing_limit",
                                   params={"fields": "quota_usage,config", "access_token": token}, timeout=30))
        d = (lim.get("data") or [{}])[0]
        total = d.get("config", {}).get("quota_total", 100)
        print(f"📊 Publicações via API nas últimas 24h: {d.get('quota_usage', 0)} de {total}")
    except ErroInstagram as e:
        print(f"❌ Falhou: {e}")
