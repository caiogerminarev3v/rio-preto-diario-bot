"""AGENTE PAUTEIRO — vasculha as fontes e traz notícias novas.

Não usa IA: lê RSS / Google Notícias, descarta o que já foi visto e
o que é velho, e (quando permitido) pega a foto da fonte.
"""
from __future__ import annotations

import html
import logging
import re
from datetime import datetime, timedelta, timezone
from urllib.parse import quote_plus

import feedparser
import requests

from ..config import Conta
from ..estado import Estado
from ..modelos import Pauta

log = logging.getLogger("pauteiro")
UA = {"User-Agent": "Mozilla/5.0 (RioPretoDiarioBot; +https://instagram.com)"}
IDADE_MAXIMA_HORAS = 18


def _limpar(texto: str) -> str:
    texto = re.sub(r"<[^>]+>", " ", texto or "")
    return re.sub(r"\s+", " ", html.unescape(texto)).strip()


def _data(entry) -> datetime | None:
    for campo in ("published_parsed", "updated_parsed"):
        t = entry.get(campo)
        if t:
            return datetime(*t[:6], tzinfo=timezone.utc)
    return None


def _imagem(entry) -> str:
    # padrões RSS comuns
    for m in entry.get("media_content", []) + entry.get("media_thumbnail", []):
        if m.get("url"):
            return m["url"]
    for enc in entry.get("enclosures", []):
        if enc.get("type", "").startswith("image") and enc.get("href"):
            return enc["href"]
    # Agência Brasil usa <imagem-destaque>
    for chave in ("imagem-destaque", "imagem_destaque", "imagemdestaque"):
        if entry.get(chave):
            return entry[chave]
    m = re.search(r'<img[^>]+src="([^"]+)"', entry.get("summary", "") + str(entry.get("content", "")))
    if m and "pixel" not in m.group(1) and "logo" not in m.group(1).lower():
        return m.group(1)
    return ""


def _url_feed(fonte: dict) -> str:
    if fonte["tipo"] == "google_news":
        q = quote_plus(fonte["consulta"] + " when:1d")
        return f"https://news.google.com/rss/search?q={q}&hl=pt-BR&gl=BR&ceid=BR:pt-419"
    return fonte["url"]


def _resolver_google(link: str) -> str:
    """Links do Google Notícias vêm codificados; tenta achar o link real."""
    if "news.google.com" not in link:
        return link
    try:
        from googlenewsdecoder import gnewsdecoder
        r = gnewsdecoder(link, interval=1)
        if r.get("status"):
            return r["decoded_url"]
    except Exception as e:  # noqa: BLE001
        log.debug("não decodificou link do Google: %s", e)
    return link


def ler_fonte(fonte: dict) -> list[Pauta]:
    url = _url_feed(fonte)
    resp = requests.get(url, headers=UA, timeout=25)
    resp.raise_for_status()
    feed = feedparser.parse(resp.content)
    limite = datetime.now(timezone.utc) - timedelta(hours=fonte.get("idade_maxima_horas", IDADE_MAXIMA_HORAS))
    filtro = [w.lower() for w in fonte.get("filtro_palavras", [])]
    pautas = []
    for e in feed.entries[:30]:
        dt = _data(e)
        if dt and dt < limite:
            continue
        titulo = _limpar(e.get("title", ""))
        if filtro:
            alvo = (titulo + " " + _limpar(e.get("summary", ""))).lower()
            if not any(w in alvo for w in filtro):
                continue
        fonte_nome = fonte["nome"]
        if fonte["tipo"] == "google_news":
            # título vem como "Manchete - Veículo"
            src = e.get("source", {}).get("title") if isinstance(e.get("source"), dict) else None
            if src:
                fonte_nome = src
                titulo = re.sub(rf"\s+-\s+{re.escape(src)}$", "", titulo)
        pautas.append(Pauta(
            titulo=titulo,
            link=e.get("link", ""),
            fonte=fonte_nome,
            escopo=fonte["escopo"],
            resumo=_limpar(e.get("summary", ""))[:600],
            publicado_em=dt.isoformat() if dt else "",
            imagem_url=_imagem(e) if fonte.get("usar_foto") else "",
            credito_foto=fonte.get("credito_foto", "") if fonte.get("usar_foto") else "",
        ))
    return pautas


def coletar(conta: Conta, estado: Estado) -> list[Pauta]:
    novas: list[Pauta] = []
    for fonte in conta["fontes"]:
        try:
            pautas = ler_fonte(fonte)
        except Exception as e:  # noqa: BLE001
            log.warning("Fonte falhou: %s (%s)", fonte["nome"], e)
            continue
        for p in pautas:
            if p.link and not estado.ja_visto(p.id):
                novas.append(p)
        log.info("%-40s %d itens, %d novos", fonte["nome"], len(pautas),
                 sum(1 for p in pautas if not estado.ja_visto(p.id)))
    return novas


def buscar_texto_completo(pauta: Pauta, conta: Conta | None = None) -> None:
    """Baixa a matéria para o redator ter contexto (não é republicado).
    Se o site estiver em `fotos_liberadas` da conta, pega a foto de destaque
    (og:image) com o crédito configurado."""
    try:
        import trafilatura
        pauta.link = _resolver_google(pauta.link)
        baixado = trafilatura.fetch_url(pauta.link)
        if not baixado:
            return
        texto = trafilatura.extract(baixado, include_comments=False) or ""
        pauta.texto_completo = texto[:6000]
        if conta and not pauta.imagem_url:
            credito = _credito_liberado(conta, pauta.link)
            if credito:
                m = re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)', baixado) \
                    or re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image', baixado)
                if m and not re.search(r"logo|default|placeholder", m.group(1), re.I):
                    pauta.imagem_url = html.unescape(m.group(1))
                    pauta.credito_foto = credito
    except Exception as e:  # noqa: BLE001
        log.debug("sem texto completo para %s: %s", pauta.link, e)


def _credito_liberado(conta: Conta, link: str) -> str:
    from urllib.parse import urlparse
    host = urlparse(link).netloc.lower().removeprefix("www.")
    for dominio, credito in (conta.get("fotos_liberadas") or {}).items():
        if host == dominio or host.endswith("." + dominio):
            return credito
    return ""


def testar_fontes(conta: Conta) -> None:
    """Diagnóstico: mostra quais fontes estão respondendo."""
    for fonte in conta["fontes"]:
        try:
            itens = ler_fonte(fonte)
            print(f"✅ {fonte['nome']}: {len(itens)} notícias recentes")
            for p in itens[:3]:
                print(f"     • {p.titulo[:90]}  [{p.fonte}]{'  📷' if p.imagem_url else ''}")
        except Exception as e:  # noqa: BLE001
            print(f"❌ {fonte['nome']}: {e}")
