"""AGENTE EDITOR-CHEFE — decide o que vira post.

1. Remove duplicadas (a mesma notícia em vários veículos).
2. Pede ao Claude para escolher as pautas mais relevantes para o público,
   classificar a editoria e marcar pautas sensíveis.
"""
from __future__ import annotations

import json
import logging
from difflib import SequenceMatcher

from .. import llm
from ..config import Conta
from ..estado import Estado
from ..modelos import Pauta

log = logging.getLogger("editor")

EDITORIAS = ["CIDADE", "SAÚDE", "SEGURANÇA", "POLÍTICA", "ECONOMIA", "EDUCAÇÃO",
             "TRÂNSITO", "CLIMA", "ESPORTE", "CULTURA", "EMPREGO", "BRASIL", "MUNDO",
             "TRAGÉDIA", "ACIDENTE", "POLÍCIA", "DEFESA CIVIL"]
# editorias de tragédia: sempre aprovação humana e arte sem foto
EDITORIAS_TRAGEDIA = {"TRAGÉDIA", "ACIDENTE", "POLÍCIA", "DEFESA CIVIL"}


def _parecido(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def remover_duplicadas(pautas: list[Pauta], estado: Estado) -> list[Pauta]:
    recentes = [x["t"] for x in estado.titulos_recentes]
    unicas: list[Pauta] = []
    for p in pautas:
        if any(_parecido(p.titulo, t) > 0.72 for t in recentes):
            continue
        dup = next((u for u in unicas if _parecido(p.titulo, u.titulo) > 0.72), None)
        if dup:
            # prefere a versão com foto liberada
            if p.imagem_url and not dup.imagem_url:
                unicas[unicas.index(dup)] = p
            continue
        unicas.append(p)
    return unicas


def escolher(conta: Conta, estado: Estado, pautas: list[Pauta]) -> list[tuple[Pauta, dict]]:
    if not pautas:
        return []
    ed = conta["editorial"]
    n = conta["publicacao"]["max_novas_pautas_por_ciclo"]
    hoje = estado.publicados_hoje()
    locais_hoje = sum(1 for p in hoje if p.escopo == "local")

    lista = [
        {"i": i, "titulo": p.titulo, "resumo": p.resumo[:280], "fonte": p.fonte, "escopo": p.escopo}
        for i, p in enumerate(pautas[:60])
    ]
    sistema = (
        f"Você é editor-chefe do perfil de notícias '{conta['nome']}' no Instagram, "
        f"focado em {ed['cidade']}. Público: {ed['publico']}.\n"
        "Escolha as pautas com maior interesse público e engajamento para esse público:\n"
        "1) TRAGÉDIAS e fatos graves — acidentes com vítimas, incêndios, desastres, temporais, "
        "afogamentos, crimes graves — em Rio Preto (municipal), nas cidades da região noroeste "
        "paulista (regional) e de grande repercussão no país (nacional). Têm alta prioridade.\n"
        "2) Política (municipal, estadual e nacional) e decisões que afetam a vida das pessoas.\n"
        "3) Serviços, saúde, trânsito, obras, economia local, emprego.\n"
        "Notícias nacionais só se forem de grande impacto. "
        "Descarte: fofoca, publieditorial, conteúdo pago, notas sem informação, "
        "notícias de cidades fora da região sem repercussão nacional, e conteúdo velho."
    )
    usuario = (
        f"Já publicamos hoje {len(hoje)} posts ({locais_hoje} locais). Mix desejado: "
        f"{int(ed['mix']['local']*100)}% local / {int(ed['mix']['brasil']*100)}% Brasil.\n"
        f"Títulos já publicados recentemente (não repita o assunto): "
        f"{json.dumps([x['t'] for x in estado.titulos_recentes[-25:]], ensure_ascii=False)}\n\n"
        f"Pautas candidatas:\n{json.dumps(lista, ensure_ascii=False)}\n\n"
        f"Escolha no máximo {n}. Para cada uma devolva:\n"
        '{"escolhidas":[{"i":0,"editoria":"' + "|".join(EDITORIAS) + '",'
        '"sensivel":true/false,"urgente":true/false,"motivo":"curto"}],'
        '"descartadas_motivo":"resumo curto"}\n'
        "Para tragédias use editoria TRAGÉDIA, ACIDENTE, POLÍCIA ou DEFESA CIVIL.\n"
        "sensivel=true quando envolve: crime com suspeito/vítima identificável, morte, menor de idade, "
        "acusação contra pessoa, saúde de pessoa identificada, política eleitoral, ou qualquer risco jurídico.\n"
        "urgente=true só para fatos de altíssimo impacto imediato (ex.: alerta de defesa civil, "
        "interdição grande, emergência de saúde pública)."
    )
    resposta = llm.pedir_json(sistema, usuario, max_tokens=1500)
    escolhidas = []
    for item in resposta.get("escolhidas", [])[:n]:
        i = item.get("i")
        if isinstance(i, int) and 0 <= i < len(pautas):
            if str(item.get("editoria", "")).upper() in EDITORIAS_TRAGEDIA:
                item["sensivel"] = True   # tragédia sempre passa pela aprovação humana
            escolhidas.append((pautas[i], item))
    log.info("Editor escolheu %d de %d pautas. Descartes: %s", len(escolhidas), len(pautas),
             resposta.get("descartadas_motivo", "")[:200])
    return escolhidas
