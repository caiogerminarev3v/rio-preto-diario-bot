"""AGENTE CHECADOR — confere o texto do redator contra a fonte.

Um segundo olhar independente: se encontrar qualquer afirmação que não
está na fonte, ou risco jurídico, o post é forçado a passar por aprovação
humana (mesmo que seja nacional/automático).
"""
from __future__ import annotations

import json
import logging

from .. import llm
from ..modelos import Post

log = logging.getLogger("checador")


def checar(post: Post) -> Post:
    pauta = post.pauta
    material = pauta.get("texto_completo") or pauta.get("resumo") or ""
    sistema = (
        "Você é checador de fatos de uma redação. Compare o POST com o MATERIAL DA FONTE. "
        "Seja rigoroso e objetivo."
    )
    usuario = f"""MATERIAL DA FONTE ({pauta.get('fonte')}):
Manchete: {pauta.get('titulo')}
\"\"\"{material[:6000]}\"\"\"

POST:
{json.dumps({'titulo_arte': post.titulo_arte, 'subtitulo_arte': post.subtitulo_arte, 'legenda': post.legenda}, ensure_ascii=False)}

Devolva JSON:
{{"aprovado": true/false,
  "problemas": ["afirmações sem respaldo na fonte, números/nomes divergentes, ofensa à presunção de inocência, exposição de menor, tom opinativo"],
  "correcoes": {{"titulo_arte": "versão corrigida ou null", "subtitulo_arte": "ou null"}}
}}"""
    try:
        r = llm.pedir_json(sistema, usuario, max_tokens=900)
    except Exception as e:  # noqa: BLE001
        log.warning("checador falhou (%s) — post vai para aprovação humana", e)
        post.sensivel = True
        post.historico.append("checador indisponível")
        return post

    corr = r.get("correcoes") or {}
    if corr.get("titulo_arte"):
        post.titulo_arte = corr["titulo_arte"].rstrip(".")
    if corr.get("subtitulo_arte"):
        post.subtitulo_arte = corr["subtitulo_arte"]
    if not r.get("aprovado", False):
        post.sensivel = True
        post.historico.append("checador: " + "; ".join(r.get("problemas", []))[:500])
        log.info("Checador sinalizou %s: %s", post.id, r.get("problemas"))
    return post
