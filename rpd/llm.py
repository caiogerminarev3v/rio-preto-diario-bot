"""Acesso ao Claude (API da Anthropic) — o "cérebro" dos agentes jornalistas."""
from __future__ import annotations

import json
import os
import re

import anthropic

MODELO = os.environ.get("RPD_MODELO", "claude-sonnet-5-5")

_cliente: anthropic.Anthropic | None = None


def cliente() -> anthropic.Anthropic:
    global _cliente
    if _cliente is None:
        _cliente = anthropic.Anthropic()  # lê ANTHROPIC_API_KEY
    return _cliente


def pedir_json(sistema: str, usuario: str, max_tokens: int = 2000) -> dict | list:
    """Pede uma resposta em JSON e devolve já convertida."""
    resp = cliente().messages.create(
        model=MODELO,
        max_tokens=max_tokens,
        system=sistema + "\n\nResponda SOMENTE com JSON válido, sem texto antes ou depois.",
        messages=[{"role": "user", "content": usuario}],
    )
    texto = "".join(b.text for b in resp.content if b.type == "text").strip()
    texto = re.sub(r"^```(?:json)?|```$", "", texto, flags=re.M).strip()
    return json.loads(texto)
