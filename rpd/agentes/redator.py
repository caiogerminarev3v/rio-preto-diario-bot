"""AGENTE REDATOR — escreve o texto da arte e a legenda.

Reescreve com palavras próprias, só com fatos presentes na fonte,
e sempre credita o veículo de origem.
"""
from __future__ import annotations

import logging

from .. import llm
from ..config import Conta
from ..estado import agora
from ..modelos import Pauta, Post

log = logging.getLogger("redator")

REGRAS = """
REGRAS JORNALÍSTICAS (obrigatórias):
- Use SOMENTE fatos presentes no material da fonte. Não invente números, nomes, datas, falas ou locais.
  Se algo não está claro na fonte, não afirme.
- Reescreva com suas palavras. Não copie frases da fonte (no máximo uma citação curta entre aspas,
  atribuída a quem falou).
- Presunção de inocência: use "suspeito", "investigado", "segundo a polícia". Nunca chame alguém de criminoso
  sem condenação.
- Não identifique menores de idade nem vítimas de violência sexual. Sem detalhes mórbidos.
- Neutralidade: sem adjetivos opinativos, sem juízo de valor sobre políticos ou partidos.
- Português do Brasil correto, frases curtas, voz ativa.

TRAGÉDIAS (acidentes, mortes, desastres, crimes):
- Tom sóbrio e respeitoso. Informe o essencial: o que aconteceu, onde, quando, número de vítimas
  e estado de saúde SEGUNDO AS AUTORIDADES (polícia, bombeiros, Defesa Civil, hospital).
- Nada de detalhes mórbidos, descrição de ferimentos ou de corpos. Não especule causas.
- Nomes de vítimas só se divulgados oficialmente; NUNCA nomes de menores.
- Inclua informação útil quando houver: trecho interditado, desvio, telefone de ajuda,
  alerta da Defesa Civil, como doar.
- Manchete forte e direta, mas sem adjetivos sensacionalistas ("horror", "chocante", "macabro").
- NÃO termine com pergunta de engajamento nem emoji em tragédias.
"""


def escrever(conta: Conta, pauta: Pauta, decisao: dict) -> Post:
    ed = conta["editorial"]
    sistema = (
        f"Você é repórter-redator do perfil '{conta['nome']}' ({conta['arroba']}) no Instagram, "
        f"cobrindo {ed['cidade']}. Tom: {ed['tom']}\n{REGRAS}"
    )
    material = pauta.texto_completo or pauta.resumo or "(somente a manchete disponível)"
    usuario = f"""Fonte: {pauta.fonte}
Link: {pauta.link}
Manchete original: {pauta.titulo}
Material da fonte:
\"\"\"{material}\"\"\"

Editoria sugerida: {decisao.get('editoria', 'CIDADE')}

Produza o post. Formato JSON:
{{
 "editoria": "1 palavra em MAIÚSCULAS (ex.: SAÚDE, TRÂNSITO, ECONOMIA)",
 "categoria": "linha de editoria da arte, máx. 36 caracteres: '{'RIO PRETO' if pauta.escopo == 'local' else 'BRASIL'} • EDITORIA' (ex.: 'RIO PRETO • SAÚDE'); se o fato for de outra cidade da região, use o nome dela",
 "titulo_arte": "manchete da arte: ENTRE 55 E 90 CARACTERES, fiel, direta, sem ponto final, sem prefixos como VÍDEO:/VEJA:/SAIBA",
 "subtitulo_arte": "linha de apoio com o dado principal, até 110 caracteres (vai só na legenda)",
 "legenda": "legenda do Instagram: 1ª linha = manchete forte; depois 2 a 4 parágrafos curtos com o essencial (o quê, quem, quando, onde, por quê, o que muda para o morador); se houver serviço (telefone, endereço, prazo) destaque; termine com 'Fonte: {pauta.fonte}' e uma pergunta curta de engajamento quando fizer sentido. Máximo 1 emoji. Sem hashtags aqui.",
 "hashtags": ["até 5 hashtags específicas do assunto, sem as fixas"],
 "alt_text": "descrição acessível da arte em 1 frase"
}}
Se o material for insuficiente para um post confiável, devolva {{"insuficiente": true}}."""
    r = llm.pedir_json(sistema, usuario, max_tokens=1800)
    if r.get("insuficiente"):
        raise ValueError("material insuficiente")

    tags = list(dict.fromkeys(ed.get("hashtags_fixas", []) + [
        h if h.startswith("#") else f"#{h}" for h in r.get("hashtags", [])
    ]))[:8]
    legenda = r["legenda"].strip()
    if pauta.credito_foto and dados_pauta_tem_foto(pauta, r, decisao):
        legenda += f"\n\n📷 Foto: {pauta.credito_foto}"
    legenda += "\n\n" + " ".join(tags)

    dados_pauta = pauta.__dict__.copy()
    from .editor import EDITORIAS_TRAGEDIA
    if r.get("editoria", decisao.get("editoria", "")).upper() in EDITORIAS_TRAGEDIA \
            or str(decisao.get("editoria", "")).upper() in EDITORIAS_TRAGEDIA:
        # tragédia: arte tipográfica (sem risco de expor vítimas em foto)
        dados_pauta["imagem_url"] = ""
        dados_pauta["credito_foto"] = ""
    dados_pauta["categoria"] = (r.get("categoria") or "").upper()[:36]
    titulo = r["titulo_arte"].strip().rstrip(".")
    if len(titulo) > 125:  # limite rígido da skill
        titulo = titulo[:122].rsplit(" ", 1)[0] + "…"
    return Post(
        id=pauta.id,
        pauta=dados_pauta,
        escopo=pauta.escopo,
        editoria=r.get("editoria", decisao.get("editoria", "CIDADE")).upper()[:14],
        titulo_arte=titulo,
        subtitulo_arte=r.get("subtitulo_arte", "").strip(),
        legenda=legenda[:2150],
        alt_text=r.get("alt_text", "")[:900],
        sensivel=bool(decisao.get("sensivel")),
        urgente=bool(decisao.get("urgente")),
        criado_em=agora().isoformat(),
    )


def dados_pauta_tem_foto(pauta: Pauta, r: dict, decisao: dict) -> bool:
    from .editor import EDITORIAS_TRAGEDIA
    ed = {str(r.get("editoria", "")).upper(), str(decisao.get("editoria", "")).upper()}
    return bool(pauta.imagem_url) and not (ed & EDITORIAS_TRAGEDIA)
