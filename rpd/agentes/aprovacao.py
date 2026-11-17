"""AGENTE DE APROVAÇÃO — manda a arte + legenda para o seu Telegram.

Você toca em ✅ Publicar ou ❌ Descartar. A cada ciclo do robô as respostas
são lidas (getUpdates) e o post segue para a fila de publicação.
Um único bot atende todas as contas; cada conta pode ter seu próprio grupo/chat.
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path

import requests

from ..config import PASTA_DADOS, Conta
from ..modelos import Post

log = logging.getLogger("aprovacao")
OFFSET_ARQ = PASTA_DADOS / "telegram_offset.json"


def _api(metodo: str) -> str:
    return f"https://api.telegram.org/bot{os.environ['TELEGRAM_BOT_TOKEN']}/{metodo}"


def disponivel() -> bool:
    return bool(os.environ.get("TELEGRAM_BOT_TOKEN"))


def pedir_aprovacao(conta: Conta, post: Post) -> None:
    chat = conta.segredo("telegram", "env_chat_id")
    motivos = []
    if post.escopo == "local":
        motivos.append("notícia local")
    if post.sensivel:
        motivos.append("⚠️ pauta sensível")
    if post.historico:
        motivos.append(post.historico[-1][:300])
    urgente = "🚨 URGENTE\n" if post.urgente else ""
    cabecalho = (f"🗞 {conta['nome']} — {post.editoria}\n{urgente}"
                 f"Motivo da revisão: {'; '.join(motivos)}\n"
                 f"Fonte: {post.pauta.get('fonte')}\n{post.pauta.get('link')}")
    with open(post.arte_path, "rb") as f:
        requests.post(_api("sendPhoto"), data={"chat_id": chat, "caption": cabecalho[:1024]},
                      files={"photo": f}, timeout=60).raise_for_status()
    teclado = {"inline_keyboard": [[
        {"text": "✅ Publicar", "callback_data": f"ok|{conta.id}|{post.id}"},
        {"text": "❌ Descartar", "callback_data": f"no|{conta.id}|{post.id}"},
    ]]}
    r = requests.post(_api("sendMessage"), data={
        "chat_id": chat, "text": post.legenda[:4000],
        "reply_markup": json.dumps(teclado)}, timeout=30)
    r.raise_for_status()
    post.telegram_msg_id = r.json()["result"]["message_id"]
    post.status = "aguardando_aprovacao"


def avisar(conta: Conta, texto: str) -> None:
    if not disponivel():
        return
    try:
        chat = conta.segredo("telegram", "env_chat_id")
        requests.post(_api("sendMessage"), data={"chat_id": chat, "text": texto[:4000]}, timeout=30)
    except Exception as e:  # noqa: BLE001
        log.warning("não avisou no Telegram: %s", e)


def marcar_mensagem(conta: Conta, post: Post, texto: str) -> None:
    if not (disponivel() and post.telegram_msg_id):
        return
    try:
        chat = conta.segredo("telegram", "env_chat_id")
        requests.post(_api("editMessageReplyMarkup"), data={
            "chat_id": chat, "message_id": post.telegram_msg_id,
            "reply_markup": json.dumps({"inline_keyboard": [[{"text": texto, "callback_data": "x"}]]})},
            timeout=30)
    except Exception as e:  # noqa: BLE001
        log.debug("não editou mensagem: %s", e)


def ler_respostas() -> list[dict]:
    """Devolve [{acao, conta, post, chat_id, callback_id}] e avança o offset."""
    if not disponivel():
        return []
    offset = json.loads(OFFSET_ARQ.read_text())["offset"] if OFFSET_ARQ.exists() else 0
    r = requests.get(_api("getUpdates"), params={
        "offset": offset, "timeout": 0, "allowed_updates": json.dumps(["callback_query"])}, timeout=30)
    r.raise_for_status()
    respostas = []
    for up in r.json().get("result", []):
        offset = max(offset, up["update_id"] + 1)
        cq = up.get("callback_query")
        if not cq or "|" not in cq.get("data", ""):
            continue
        acao, conta_id, post_id = cq["data"].split("|", 2)
        respostas.append({"acao": acao, "conta": conta_id, "post": post_id,
                          "chat_id": str(cq["message"]["chat"]["id"]), "callback_id": cq["id"],
                          "quem": cq.get("from", {}).get("first_name", "")})
    OFFSET_ARQ.parent.mkdir(parents=True, exist_ok=True)
    Path(OFFSET_ARQ).write_text(json.dumps({"offset": offset}))
    return respostas


def responder_clique(callback_id: str, texto: str) -> None:
    try:
        requests.post(_api("answerCallbackQuery"),
                      data={"callback_query_id": callback_id, "text": texto}, timeout=15)
    except Exception:  # noqa: BLE001
        pass


def listar_chats() -> None:
    """Mostra os chats que mandaram mensagem ao bot (para descobrir o CHAT_ID)."""
    if not disponivel():
        print("❌ TELEGRAM_BOT_TOKEN não configurado")
        return
    me = requests.get(_api("getMe"), timeout=20).json()
    if not me.get("ok"):
        print(f"❌ Token do Telegram inválido: {me.get('description')}")
        return
    print(f"✅ Bot: @{me['result']['username']}")
    r = requests.get(_api("getUpdates"), params={"timeout": 0}, timeout=20).json()
    vistos = {}
    for up in r.get("result", []):
        msg = up.get("message") or up.get("my_chat_member") or {}
        chat = msg.get("chat")
        if chat:
            nome = chat.get("title") or " ".join(filter(None, [chat.get("first_name"), chat.get("last_name")]))
            vistos[chat["id"]] = f"{chat.get('type')}: {nome}"
    if not vistos:
        print("⚠️  Nenhuma mensagem encontrada. Mande 'oi' para o bot no Telegram e rode de novo.")
    for cid, desc in vistos.items():
        print(f"💬 CHAT_ID = {cid}   ({desc})")
