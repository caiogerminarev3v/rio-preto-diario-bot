"""AGENTE DESIGNER — monta a arte 1080x1350 (formato retrato do feed).

Dois layouts:
- COM FOTO: só quando a fonte permite (Agência Brasil, Prefeitura), com crédito.
- TIPOGRÁFICO: fundo com as cores da marca — usado em todo o resto,
  para nunca reaproveitar foto de jornal comercial.
"""
from __future__ import annotations

import io
import logging
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFont, ImageOps

from ..config import Conta
from ..modelos import Post

log = logging.getLogger("designer")
L, A = 1080, 1350
M = 72  # margem


def _hex(c: str, alpha: int = 255) -> tuple:
    c = c.lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4)) + (alpha,)


def _fonte(caminho: Path, tamanho: int, peso: str) -> ImageFont.FreeTypeFont:
    f = ImageFont.truetype(str(caminho), tamanho)
    try:
        f.set_variation_by_name(peso)
    except Exception:  # noqa: BLE001 — fonte não-variável
        pass
    return f


def _quebrar(draw, texto, fonte, largura) -> list[str]:
    linhas, atual = [], ""
    for palavra in texto.split():
        teste = f"{atual} {palavra}".strip()
        if draw.textlength(teste, font=fonte) <= largura:
            atual = teste
        else:
            if atual:
                linhas.append(atual)
            atual = palavra
    if atual:
        linhas.append(atual)
    return linhas


def _ajustar(draw, texto, caminho, peso, largura, max_linhas, maior, menor):
    """Maior fonte possível que caiba em max_linhas."""
    for t in range(maior, menor - 1, -2):
        f = _fonte(caminho, t, peso)
        linhas = _quebrar(draw, texto, f, largura)
        if len(linhas) <= max_linhas:
            return f, linhas
    f = _fonte(caminho, menor, peso)
    linhas = _quebrar(draw, texto, f, largura)[:max_linhas]
    linhas[-1] = linhas[-1].rstrip(".,;:") + "…"
    return f, linhas


def _baixar_foto(url: str) -> Image.Image | None:
    try:
        r = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        img = Image.open(io.BytesIO(r.content)).convert("RGB")
        if img.width < 500:
            return None
        return ImageOps.fit(img, (L, A), method=Image.LANCZOS, centering=(0.5, 0.35))
    except Exception as e:  # noqa: BLE001
        log.info("foto indisponível (%s) — usando layout tipográfico", e)
        return None


def _gradiente_vertical(cor_topo, cor_base, inicio=0.0) -> Image.Image:
    col = Image.new("RGBA", (1, A))
    px = col.load()
    for y in range(A):
        f = y / A
        t = 0.0 if f <= inicio else ((f - inicio) / (1 - inicio)) ** 1.15
        px[0, y] = tuple(int(cor_topo[i] + (cor_base[i] - cor_topo[i]) * t) for i in range(4))
    return col.resize((L, A))


def _logo(conta: Conta) -> Image.Image | None:
    p = conta.caminho(conta["visual"]["logo"])
    if not p.exists():
        return None
    logo = Image.open(p).convert("RGBA")
    logo.thumbnail((300, 120), Image.LANCZOS)
    return logo


def criar_arte(conta: Conta, post: Post, destino: Path) -> Path:
    v = conta["visual"]
    cores = v["cores"]
    ft = conta.caminho(v["fonte_titulo"])
    fx = conta.caminho(v["fonte_texto"])
    prim, sec = _hex(cores["primaria"]), _hex(cores["secundaria"])
    dest, branco = _hex(cores["destaque"]), _hex(cores["texto"])

    foto = _baixar_foto(post.pauta.get("imagem_url", "")) if post.pauta.get("imagem_url") else None
    com_foto = foto is not None

    # ---------- fundo ----------
    if com_foto:
        base = foto.convert("RGBA")
        sombra_cor = _hex(cores.get("sombra_foto", cores["primaria"]))
        base = Image.alpha_composite(base, _gradiente_vertical(sombra_cor[:3] + (0,), sombra_cor[:3] + (245,), inicio=0.30))
        # faixa vermelha da marca no rodapé
        ImageDraw.Draw(base).rectangle((0, A - 14, L, A), fill=_hex(cores["secundaria"]))
        sombra = _gradiente_vertical((0, 0, 0, 150), (0, 0, 0, 0)).crop((0, 0, L, 260))
        base.alpha_composite(sombra, (0, 0))
    else:
        base = _gradiente_vertical(sec, prim)
        # textura: listras diagonais sutis
        tex = Image.new("RGBA", (L, A), (0, 0, 0, 0))
        dt = ImageDraw.Draw(tex)
        for x in range(-A, L, 46):
            dt.line([(x, A), (x + A, 0)], fill=branco[:3] + (10,), width=14)
        base = Image.alpha_composite(base, tex)
        # marca d'água com a editoria
        wm = Image.new("RGBA", (L, A), (0, 0, 0, 0))
        fw = _fonte(ft, 200, "Black")
        ImageDraw.Draw(wm).text((M - 14, A - 400), post.editoria, font=fw, fill=branco[:3] + (14,))
        base = Image.alpha_composite(base, wm)

    d = ImageDraw.Draw(base)
    larg = L - 2 * M

    # ---------- topo: logo + selo ----------
    logo = _logo(conta)
    if logo:
        base.alpha_composite(logo, (M, 64))
    else:
        d.text((M, 70), conta["nome"].upper(), font=_fonte(ft, 40, "ExtraBold"), fill=branco)
    if post.urgente:
        fu = _fonte(ft, 34, "Black")
        w = d.textlength("URGENTE", font=fu) + 48
        d.rounded_rectangle((L - M - w, 64, L - M, 124), radius=8, fill=_hex(cores["urgente"]))
        d.text((L - M - w + 24, 74), "URGENTE", font=fu, fill=branco)

    # ---------- bloco de texto (montado de baixo para cima) ----------
    ff = _fonte(fx, 26, "Medium")
    rodape_y = A - M - 30
    fonte_txt = f"Fonte: {post.pauta.get('fonte', '')}"
    cred = post.pauta.get("credito_foto", "")
    if cred and com_foto:
        if cred == post.pauta.get("fonte"):
            fonte_txt = f"Texto e foto: {cred}"
        else:
            fonte_txt += f"  •  Foto: {cred}"
    d.line((M, rodape_y - 26, L - M, rodape_y - 26), fill=branco[:3] + (70,), width=2)
    d.text((M, rodape_y), conta["arroba"], font=_fonte(fx, 26, "Bold"), fill=branco)
    tw = d.textlength(fonte_txt, font=ff)
    if tw > larg - 320:
        fonte_txt = fonte_txt[: int(len(fonte_txt) * (larg - 320) / tw) - 1] + "…"
        tw = d.textlength(fonte_txt, font=ff)
    d.text((L - M - tw, rodape_y), fonte_txt, font=ff, fill=branco[:3] + (190,))

    # subtítulo e título
    fs, ls = (None, [])
    if post.subtitulo_arte:
        fs, ls = _ajustar(d, post.subtitulo_arte, fx, "Medium", larg, 3, 36, 28)
    alt_s = int(fs.size * 1.32) if fs else 0
    maior, menor = (78, 50) if com_foto else (96, 58)
    titulo = post.titulo_arte.upper() if len(post.titulo_arte) <= 42 else post.titulo_arte
    ft_t, lt = _ajustar(d, titulo, ft, "ExtraBold", larg, 4 if com_foto else 5, maior, menor)
    alt_t = int(ft_t.size * 1.12)
    bloco = alt_t * len(lt) + (34 + alt_s * len(ls) if ls else 0)

    if com_foto:
        y = rodape_y - 70 - bloco          # ancorado embaixo, sobre o degradê
    else:
        y = max(250, int((A - bloco) / 2) - 10)   # centralizado no tipográfico
    for i, linha in enumerate(lt):
        d.text((M, y + i * alt_t), linha, font=ft_t, fill=branco)
    ys = y + alt_t * len(lt) + 34
    if not com_foto and ls:
        d.rectangle((M, ys - 14, M + 90, ys - 8), fill=dest)
        ys += 10
    for i, linha in enumerate(ls):
        d.text((M, ys + i * alt_s), linha, font=fs, fill=branco[:3] + (225,))

    # chapéu da editoria
    fc = _fonte(ft, 30, "Black")
    cw = d.textlength(post.editoria, font=fc) + 44
    cy = y - 78
    d.rounded_rectangle((M, cy, M + cw, cy + 54), radius=6,
                        fill=_hex(cores["secundaria"]) if com_foto else dest)
    d.text((M + 22, cy + 9), post.editoria, font=fc, fill=branco)

    destino.parent.mkdir(parents=True, exist_ok=True)
    base.convert("RGB").save(destino, "JPEG", quality=92, optimize=True, progressive=True)
    return destino
