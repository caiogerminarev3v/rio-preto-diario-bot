"""AGENTE DESIGNER: monta a arte 1080x1350 no padrão oficial do Rio Preto Diário.

Segue a skill "rio-preto-diario-social" (docs/design/): pilha de 6 camadas.
  1. foto de fundo (cover + foco)        4. degradê inferior + brilho da marca
  2. vinheta superior esquerda           5. logo oficial com sombra
  3. mosaico diagonal da logo vazada     6. editoria + manchete + assinatura

Foto: só de fontes com licença de reuso (Agência Brasil CC BY, órgãos públicos).
Sem foto liberada, o fundo vira o "modo tipográfico": preto editorial com o
DNA vermelho da marca, mantendo exatamente as mesmas camadas por cima.
"""
from __future__ import annotations

import io
import logging
from pathlib import Path

import requests
from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageFont

from ..config import Conta
from ..modelos import Post

log = logging.getLogger("designer")

W, H = 1080, 1350
M_ESQ, M_DIR, M_TOPO, M_BASE = 88, 108, 78, 70
LARG_TEXTO = W - M_ESQ - M_DIR          # 884 px
ALTURA_MAX_MANCHETE = 395

VERMELHO_MARCA = (218, 3, 21)           # #DA0315
VERMELHO_PORTAL = (255, 31, 52)         # #FF1F34
TINTA = (6, 7, 11)

# escalonamento oficial da manchete (design-spec.md)
ESCALA = [(50, 60, 1.12), (75, 54, 1.13), (100, 48, 1.15), (10_000, 42, 1.16)]


# ======================================================================
# utilitários
# ======================================================================
def _fonte(caminho: Path, tamanho: int, peso: int) -> ImageFont.FreeTypeFont:
    f = ImageFont.truetype(str(caminho), tamanho)
    try:
        f.set_variation_by_axes([peso])
    except Exception:  # noqa: BLE001 (fonte estática)
        pass
    return f


def _hex(c: str) -> tuple:
    c = c.lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def _largura(texto: str, fonte, tracking: float) -> float:
    if not texto:
        return 0
    return sum(fonte.getlength(ch) for ch in texto) + tracking * (len(texto) - 1)


def _desenhar(draw, xy, texto, fonte, cor, tracking: float = 0.0) -> None:
    """Texto com espaçamento entre letras (letter-spacing do CSS)."""
    x, y = xy
    if not tracking:
        draw.text((x, y), texto, font=fonte, fill=cor)
        return
    for ch in texto:
        draw.text((x, y), ch, font=fonte, fill=cor)
        x += fonte.getlength(ch) + tracking


def _quebrar_balanceado(texto: str, fonte, tracking: float, largura: int) -> list[str]:
    """Equivalente a `text-wrap: balance`: mesmo nº de linhas, larguras parecidas."""
    palavras = texto.split()

    def guloso(lim: float) -> list[str]:
        linhas, atual = [], ""
        for p in palavras:
            t = f"{atual} {p}".strip()
            if _largura(t, fonte, tracking) <= lim or not atual:
                atual = t
            else:
                linhas.append(atual)
                atual = p
        if atual:
            linhas.append(atual)
        return linhas

    base = guloso(largura)
    n = len(base)
    lo, hi = largura * 0.45, largura
    for _ in range(18):                  # menor largura que mantém o mesmo nº de linhas
        meio = (lo + hi) / 2
        if len(guloso(meio)) <= n:
            hi = meio
        else:
            lo = meio
    return guloso(hi)


def _gradiente_radial(tam, centro, raios, paradas, cor) -> Image.Image:
    """Máscara radial elíptica em escala reduzida (rápido) → RGBA."""
    esc = 4
    w, h = tam[0] // esc, tam[1] // esc
    cx, cy = centro[0] / esc, centro[1] / esc
    rx, ry = raios[0] / esc, raios[1] / esc
    alfa = Image.new("L", (w, h))
    px = alfa.load()
    for y in range(h):
        for x in range(w):
            d = (((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2) ** 0.5
            px[x, y] = int(255 * _interp(paradas, min(d, 1.0)))
    alfa = alfa.resize(tam, Image.BILINEAR)
    camada = Image.new("RGBA", tam, cor + (0,))
    camada.putalpha(alfa)
    return camada


def _interp(paradas, t):
    for (t0, a0), (t1, a1) in zip(paradas, paradas[1:]):
        if t <= t1:
            return a0 + (a1 - a0) * ((t - t0) / (t1 - t0) if t1 > t0 else 0)
    return paradas[-1][1]


def _gradiente_vertical(altura, paradas, cor_topo, cor_base) -> Image.Image:
    col = Image.new("RGBA", (1, altura))
    px = col.load()
    for y in range(altura):
        t = y / (altura - 1)
        a = _interp(paradas, t)
        c = tuple(int(cor_topo[i] + (cor_base[i] - cor_topo[i]) * t) for i in range(3))
        px[0, y] = c + (int(255 * a),)
    return col.resize((W, altura))


# ======================================================================
# camadas
# ======================================================================
def _foco(foco: str) -> tuple[float, float]:
    """'34% 16%' | 'center 25%' → (0.34, 0.16)."""
    mapa = {"left": 0.0, "center": 0.5, "right": 1.0, "top": 0.0, "bottom": 1.0}
    partes = (foco or "center 25%").split()
    vals = []
    for p in partes[:2]:
        vals.append(float(p.rstrip("%")) / 100 if p.endswith("%") else mapa.get(p, 0.5))
    while len(vals) < 2:
        vals.append(0.25)
    return vals[0], vals[1]


def _baixar_foto(url: str) -> Image.Image | None:
    try:
        r = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        img = Image.open(io.BytesIO(r.content)).convert("RGB")
        if img.width < 600:
            log.info("foto pequena demais (%dpx), usando modo tipográfico", img.width)
            return None
        return img
    except Exception as e:  # noqa: BLE001
        log.info("foto indisponível (%s), usando modo tipográfico", e)
        return None


def _camada_foto(img: Image.Image, foco: str) -> Image.Image:
    fx, fy = _foco(foco)
    esc = max(W / img.width, H / img.height)
    nova = img.resize((round(img.width * esc), round(img.height * esc)), Image.LANCZOS)
    x = round((nova.width - W) * fx)
    y = round((nova.height - H) * fy)
    foto = nova.crop((x, y, x + W, y + H))
    foto = ImageEnhance.Contrast(foto).enhance(1.03)
    foto = ImageEnhance.Color(foto).enhance(1.04)
    return foto.convert("RGBA")


def _fundo_tipografico(outline: Path) -> Image.Image:
    """Sem foto liberada: preto editorial com o vermelho da marca."""
    base = _gradiente_vertical(H, [(0, 1), (1, 1)], (16, 10, 14), (6, 7, 10))
    base = Image.alpha_composite(base, _gradiente_radial(
        (W, H), (W * 0.92, H * 0.18), (W * 0.95, H * 0.62),
        [(0, 0.55), (0.55, 0.22), (1, 0)], VERMELHO_MARCA))
    base = Image.alpha_composite(base, _gradiente_radial(
        (W, H), (W * 0.05, H * 0.98), (W * 0.8, H * 0.45),
        [(0, 0.28), (1, 0)], VERMELHO_MARCA))
    # logo vazada grande, discreta, preenchendo o centro-direita
    if outline.exists():
        lg = Image.open(outline).convert("RGBA")
        lg = lg.resize((980, round(980 * lg.height / lg.width)), Image.LANCZOS)
        a = lg.getchannel("A").point(lambda v: int(v * 0.10))
        lg.putalpha(a)
        lg = lg.rotate(-6, expand=True, resample=Image.BICUBIC)
        base.alpha_composite(lg, (W - lg.width + 160, int(H * 0.22)))
    return base


def _camada_vinheta() -> Image.Image:
    return _gradiente_radial((W, H), (W * 0.18, H * 0.12), (W * 0.58, H * 0.42),
                             [(0, 0.72), (0.5, 0.42), (0.8, 0.10), (1, 0)], TINTA)


def _camada_mosaico(tile_path: Path) -> Image.Image | None:
    if not tile_path.exists():
        return None
    tile = Image.open(tile_path).convert("RGBA").resize((206, 224), Image.LANCZOS)
    grande = Image.new("RGBA", (W * 2, H * 2), (0, 0, 0, 0))
    for y in range(0, grande.height, tile.height):
        for x in range(0, grande.width, tile.width):
            grande.alpha_composite(tile, (x, y))
    grande = grande.rotate(14, resample=Image.BICUBIC)       # CSS rotate(-14deg)
    camada = grande.crop((W // 2, H // 2, W // 2 + W, H // 2 + H))
    # opacidade 0.18 × máscara circular 520px em (17%, 14%)
    mascara = _gradiente_radial((W, H), (W * 0.17, H * 0.14), (520, 520),
                                [(0, 0.95), (0.48, 0.62), (0.78, 0.16), (1, 0)], (0, 0, 0))
    m = mascara.getchannel("A").point(lambda v: int(v * 0.18))
    final = Image.new("RGBA", (W, H), (255, 255, 255, 0))
    final.putalpha(ImageChops.multiply(camada.getchannel("A"), m))
    return final


def _camada_degrade_inferior() -> Image.Image:
    topo = 459
    g = _gradiente_vertical(H - topo, [(0, 0), (0.24, 0.14), (0.48, 0.50), (0.74, 0.84), (1, 0.96)],
                            (7, 8, 12), (5, 6, 9))
    camada = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    camada.alpha_composite(g, (0, topo))
    brilho = _gradiente_radial((W, H), (0, H), (W * 0.62, H * 0.40), [(0, 0.14), (1, 0)], VERMELHO_MARCA)
    return Image.alpha_composite(camada, brilho)


def _camada_logo(logo_path: Path) -> Image.Image | None:
    if not logo_path.exists():
        return None
    logo = Image.open(logo_path).convert("RGBA")
    logo = logo.resize((242, round(242 * logo.height / logo.width)), Image.LANCZOS)
    camada = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sombra = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    s = Image.new("RGBA", logo.size, (0, 0, 0, 0))
    s.putalpha(logo.getchannel("A").point(lambda v: int(v * 0.60)))
    sombra.alpha_composite(s, (M_ESQ, M_TOPO + 4))
    sombra = sombra.filter(ImageFilter.GaussianBlur(8))
    camada = Image.alpha_composite(camada, sombra)
    camada.alpha_composite(logo, (M_ESQ, M_TOPO))
    return camada


# ======================================================================
# composição
# ======================================================================
def criar_arte(conta: Conta, post: Post, destino: Path) -> Path:
    v = conta["visual"]
    f_titulo = conta.caminho(v.get("fonte_titulo", "assets/fonts/PlusJakartaSans.ttf"))
    f_editorial = conta.caminho(v.get("fonte_editorial", "assets/fonts/PlayfairDisplay.ttf"))
    acento = _hex(v.get("cores", {}).get("acento", "#FF1F34"))
    variante = "urgente" if post.urgente else post.pauta.get("variante", "padrao")

    # ---------- 1. fundo ----------
    url = post.pauta.get("imagem_url", "")
    foto = _baixar_foto(url) if url else None
    if foto is not None:
        base = _camada_foto(foto, post.pauta.get("foco", "center 25%"))
    else:
        base = _fundo_tipografico(conta.caminho(v.get("logo_outline", "assets/rio_preto_diario/logo-outline.png")))

    # ---------- 2 a 5 ----------
    base = Image.alpha_composite(base, _camada_vinheta())
    mosaico = _camada_mosaico(conta.caminho(v.get("mosaico", "assets/rio_preto_diario/watermark-tile.png")))
    if mosaico:
        base = Image.alpha_composite(base, mosaico)
    base = Image.alpha_composite(base, _camada_degrade_inferior())
    logo = _camada_logo(conta.caminho(v["logo"]))
    if logo:
        base = Image.alpha_composite(base, logo)

    # ---------- 6. bloco tipográfico (de baixo para cima) ----------
    texto_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(texto_layer)

    # assinatura
    f_rod = _fonte(f_titulo, 15, 700)
    rod_txt = v.get("rodape", conta["arroba"]).upper()
    rod_h = 15
    y_rod = H - M_BASE - rod_h
    d.rounded_rectangle((M_ESQ, y_rod + 6, M_ESQ + 44, y_rod + 10), radius=2, fill=acento + (255,))
    _desenhar(d, (M_ESQ + 44 + 14, y_rod - 2), rod_txt, f_rod, (255, 255, 255, 189), 15 * 0.22)
    cred = post.pauta.get("credito_foto") if foto is not None else ""
    if cred:  # licença CC BY exige crédito visível
        f_cred = _fonte(f_titulo, 13, 600)
        t = f"FOTO: {cred.upper()}"
        _desenhar(d, (W - M_DIR - _largura(t, f_cred, 1.3), y_rod), t, f_cred, (255, 255, 255, 140), 1.3)

    # manchete
    manchete = post.titulo_arte.strip()
    n = len(manchete)
    tam, lh = next((t, l) for lim, t, l in ESCALA if n <= lim)
    fonte_m = f_editorial if variante == "editorial" else f_titulo
    track_em = -0.015 if variante == "editorial" else -0.025
    while True:
        fm = _fonte(fonte_m, tam, 800)
        linhas = _quebrar_balanceado(manchete, fm, tam * track_em, LARG_TEXTO)
        alt = round(tam * lh) * len(linhas)
        if alt <= ALTURA_MAX_MANCHETE or tam <= 34:
            break
        tam -= 2
    passo = round(tam * lh)
    y_man_fim = y_rod - 26
    y_man = y_man_fim - passo * len(linhas)
    sombra = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ds = ImageDraw.Draw(sombra)
    for i, linha in enumerate(linhas):
        yy = y_man + i * passo - round(tam * 0.08)
        _desenhar(ds, (M_ESQ, yy + 3), linha, fm, (0, 0, 0, 140), tam * track_em)
        _desenhar(d, (M_ESQ, yy), linha, fm, (255, 255, 255, 255), tam * track_em)
    sombra = sombra.filter(ImageFilter.GaussianBlur(9))

    # editoria
    cat = post.pauta.get("categoria") or post.editoria
    cat = cat.upper()[:36]
    y_kick = y_man - 18 - 24
    f_kick = _fonte(f_titulo, 20, 700)
    if variante == "urgente":
        f_urg = _fonte(f_titulo, 16, 800)
        pw = 12 + 8 + 8 + _largura("URGENTE", f_urg, 16 * 0.14) + 12
        d.rounded_rectangle((M_ESQ, y_kick - 3, M_ESQ + pw, y_kick + 27), radius=5, fill=VERMELHO_MARCA + (255,))
        d.ellipse((M_ESQ + 12, y_kick + 8, M_ESQ + 20, y_kick + 16), fill=(255, 255, 255, 255))
        _desenhar(d, (M_ESQ + 28, y_kick + 2), "URGENTE", f_urg, (255, 255, 255, 255), 16 * 0.14)
        if cat:
            _desenhar(d, (M_ESQ + pw + 14, y_kick), cat, f_kick, (255, 255, 255, 235), 20 * 0.15)
    elif cat:
        glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(glow).rounded_rectangle((M_ESQ, y_kick + 1, M_ESQ + 6, y_kick + 23), radius=3,
                                               fill=acento + (115,))
        sombra = Image.alpha_composite(sombra, glow.filter(ImageFilter.GaussianBlur(5)))
        d.rounded_rectangle((M_ESQ, y_kick + 1, M_ESQ + 6, y_kick + 23), radius=3, fill=acento + (255,))
        _desenhar(d, (M_ESQ + 18, y_kick), cat, f_kick, (255, 255, 255, 235), 20 * 0.15)

    base = Image.alpha_composite(base, sombra)
    base = Image.alpha_composite(base, texto_layer)

    destino.parent.mkdir(parents=True, exist_ok=True)
    base.convert("RGB").save(destino, "JPEG", quality=94, optimize=True, progressive=True)
    return destino
