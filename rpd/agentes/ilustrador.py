"""DIRETOR DE IMAGEM — nunca deixa a arte "vazia".

Regra editorial do Rio Preto Diário:
  1. SEMPRE foto do local/assunto, de fonte liberada (divulgação oficial), com crédito;
  2. se não houver foto liberada, a arte leva ELEMENTOS VISUAIS que comunicam o tema
     (cones e barreira para trânsito/obras, mosquito para dengue, gota para água...).

Este módulo cobre o item 2: detecta o tema pela editoria + manchete e desenha a
ilustração (original, vetorial, em Pillow) na paleta da marca.
"""
from __future__ import annotations

import math
import re
import unicodedata

from PIL import Image, ImageDraw, ImageFilter

VERM = (218, 3, 21)
VERM2 = (255, 31, 52)
BRANCO = (255, 255, 255)
AZUL = (110, 185, 255)
AMARELO = (255, 196, 36)
TINTA = (20, 22, 30)

SS = 2          # supersampling para bordas suaves
LADO = 900      # área da ilustração (px, na arte final)

# tema -> palavras-chave (sem acento, minúsculas)
TEMAS: dict[str, list[str]] = {
    "signos": ["signo", "horoscopo", "astrologia", "zodiaco", "mapa astral"],
    "motivacional": ["motivacional", "motivacao", "inspira", "boa semana", "bom dia", "superacao"],
    "dengue": ["dengue", "mosquito", "aedes", "chikungunya", "zika", "arbovirose"],
    "saude": ["saude", "vacina", "ubs", "hospital", "medic", "doenca", "sus", "upa", "gripe"],
    "clima": ["chuva", "tempestade", "temporal", "calor", "inmet", "granizo", "clima", "queimada",
              "ventania", "frente fria", "onda de calor"],
    "dinheiro": ["divida", "imposto", "fiscal", "economia", "selic", "preco", "salario", "renda",
                 "feirao", "ppi", "iptu", "inflacao", "credito", "pix", "golpe", "fraude", "orcamento"],
    "emprego": ["vaga", "emprego", "concurso", "trabalho", "contrata", "carteira", "estagio"],
    "educacao": ["escola", "enem", "aluno", "educacao", "universidade", "matricula", "professor", "fies"],
    "agua": ["agua", "esgoto", "semae", "abastecimento", "reservatorio", "represa"],
    "politica": ["senado", "camara", "governo", "stf", "presidente", "congresso", "ministro", "lei ",
                 "eleicao", "prefeito", "vereador", "plenario"],
    "evento": ["evento", "festa", "show", "feira", "cultura", "forum", "natal", "praca", "exposicao",
               "festival", "oficina", "teatro", "mulheres"],
    "alerta": ["acidente", "morre", "tragedia", "incendio", "capota", "colisao", "resgate"],
    "transito": ["transito", "avenida", "rua ", "interdi", "obra", "desvio", "rodovia", "semaforo",
                 "onibus", "via ", "pista", "ciclovia", "viaduto"],
}
PRIORIDADE = ["signos", "motivacional", "dengue", "alerta", "clima", "dinheiro", "emprego", "educacao", "saude", "agua",
              "politica", "evento", "transito"]


def _norm(t: str) -> str:
    t = unicodedata.normalize("NFD", t or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", t) + " "


def detectar_tema(categoria: str = "", titulo: str = "") -> str:
    alvo = _norm(f"{categoria} {titulo}")
    melhor, pontos = "generico", 0
    for tema in PRIORIDADE:
        p = sum(1 for k in TEMAS[tema] if k in alvo)
        if p > pontos:
            melhor, pontos = tema, p
    return melhor


# ---------------------------------------------------------------- primitivas
class _Tela:
    def __init__(self):
        n = LADO * SS
        self.im = Image.new("RGBA", (n, n), (0, 0, 0, 0))
        self.d = ImageDraw.Draw(self.im)
        self.u = n / 100.0

    def P(self, x, y):
        return (x * self.u, y * self.u)

    def pts(self, lista):
        return [self.P(x, y) for x, y in lista]

    def poly(self, lista, fill):
        self.d.polygon(self.pts(lista), fill=fill)

    def rect(self, x0, y0, x1, y1, fill, r=0):
        box = (*self.P(x0, y0), *self.P(x1, y1))
        if r:
            self.d.rounded_rectangle(box, radius=r * self.u, fill=fill)
        else:
            self.d.rectangle(box, fill=fill)

    def ell(self, x0, y0, x1, y1, fill=None, outline=None, w=0):
        self.d.ellipse((*self.P(x0, y0), *self.P(x1, y1)), fill=fill, outline=outline,
                       width=int(w * self.u))

    def line(self, lista, fill, w):
        self.d.line(self.pts(lista), fill=fill, width=int(w * self.u), joint="curve")

    def arc(self, x0, y0, x1, y1, a0, a1, fill, w):
        self.d.arc((*self.P(x0, y0), *self.P(x1, y1)), a0, a1, fill=fill, width=int(w * self.u))


def _solo(t: _Tela):
    t.rect(4, 90, 96, 93.5, BRANCO + (70,), r=1.7)


def _cone(t: _Tela, cx, base, h, w):
    t.rect(cx - w * 0.66, base - 3.2, cx + w * 0.66, base, BRANCO + (235,), r=1)
    top = w * 0.14
    def lado(y):  # largura meia do cone na altura y (0 = base, h = topo)
        f = y / h
        return (w / 2) * (1 - f) + top * f
    t.poly([(cx - lado(0), base - 3), (cx + lado(0), base - 3), (cx + top, base - h), (cx - top, base - h)], VERM2 + (255,))
    for a, b in ((0.30, 0.46), (0.58, 0.72)):
        y0, y1 = a * h, b * h
        t.poly([(cx - lado(y0), base - 3 - y0), (cx + lado(y0), base - 3 - y0),
                (cx + lado(y1), base - 3 - y1), (cx - lado(y1), base - 3 - y1)], BRANCO + (245,))


def _faixas(t: _Tela, x0, y0, x1, y1, n=7):
    t.rect(x0, y0, x1, y1, BRANCO + (245,), r=1.2)
    larg = (x1 - x0) / n
    for i in range(0, n, 2):
        xa = x0 + i * larg
        t.poly([(xa, y1), (xa + larg * 0.9, y1), (xa + larg * 0.9 + (y1 - y0) * 0.6, y0), (xa + (y1 - y0) * 0.6, y0)],
               VERM2 + (255,))


# ---------------------------------------------------------------- temas
def _transito(t: _Tela):
    _solo(t)
    # placa de proibido
    t.ell(56, 6, 94, 44, fill=VERM2 + (255,))
    t.ell(60, 10, 90, 40, fill=BRANCO + (255,))
    t.ell(63, 13, 87, 37, fill=VERM2 + (255,))
    t.rect(67, 22.5, 83, 27.5, BRANCO + (255,), r=1)
    t.rect(73, 44, 77, 90, BRANCO + (200,))
    # barreira
    _faixas(t, 34, 56, 78, 66)
    t.rect(38, 66, 41, 90, BRANCO + (235,))
    t.rect(71, 66, 74, 90, BRANCO + (235,))
    _faixas(t, 34, 70, 78, 77)
    # cones
    _cone(t, 16, 90, 30, 17)
    _cone(t, 90, 90, 22, 13)


def _alerta(t: _Tela):
    _solo(t)
    t.poly([(50, 8), (92, 80), (8, 80)], AMARELO + (255,))
    t.poly([(50, 20), (80, 74), (20, 74)], TINTA + (255,))
    t.rect(47, 36, 53, 58, AMARELO + (255,), r=2.5)
    t.ell(46.5, 62, 53.5, 69, fill=AMARELO + (255,))


def _dengue(t: _Tela):
    from .mosquito_arte import mosquito
    m = mosquito(LADO * SS, 0.15)
    t.im.alpha_composite(m)
    # placa "proibido" discreta por trás
    t.ell(2, 2, 40, 40, outline=VERM2 + (255,), w=2.6)
    t.line([(6, 36), (36, 6)], VERM2 + (255,), 2.6)


def _saude(t: _Tela):
    t.ell(10, 10, 90, 90, fill=BRANCO + (40,))
    t.rect(38, 18, 62, 82, VERM2 + (255,), r=5)
    t.rect(18, 38, 82, 62, VERM2 + (255,), r=5)
    t.line([(6, 50), (30, 50), (38, 32), (48, 70), (56, 44), (62, 50), (94, 50)], BRANCO + (255,), 2.6)


def _clima(t: _Tela):
    t.ell(14, 28, 52, 66, fill=BRANCO + (245,))
    t.ell(34, 14, 78, 58, fill=BRANCO + (245,))
    t.ell(56, 30, 92, 66, fill=BRANCO + (245,))
    t.rect(24, 44, 84, 66, BRANCO + (245,), r=10)
    t.poly([(52, 54), (36, 82), (48, 82), (40, 98), (66, 70), (53, 70), (62, 54)], AMARELO + (255,))
    for x in (22, 70, 84):
        t.line([(x, 74), (x - 5, 88)], AZUL + (255,), 2.6)


def _dinheiro(t: _Tela):
    _solo(t)
    for i, y in enumerate((80, 70, 60, 50)):  # pilha de moedas
        t.ell(8, y - 3, 56, y + 9, fill=AMARELO + (255,))
        t.ell(8, y - 6, 56, y + 6, fill=(255, 220, 90, 255), outline=(180, 120, 0, 255), w=0.8)
    t.ell(18, 40, 46, 52, fill=(255, 220, 90, 255), outline=(180, 120, 0, 255), w=0.8)
    # selo de porcentagem
    t.ell(52, 14, 94, 56, fill=VERM2 + (255,))
    t.ell(70, 20, 77, 27, fill=BRANCO + (255,))
    t.ell(70, 43, 77, 50, fill=BRANCO + (255,))
    t.line([(80, 24), (66, 48)], BRANCO + (255,), 3.2)
    # seta de queda
    t.line([(60, 82), (72, 70), (80, 77), (92, 62)], BRANCO + (240,), 2.8)
    t.poly([(92, 62), (84, 62), (92, 70)], BRANCO + (240,))


def _emprego(t: _Tela):
    t.rect(34, 18, 66, 30, None or BRANCO + (0,), r=2)
    t.arc(36, 12, 64, 40, 180, 360, BRANCO + (255,), 3.4)
    t.rect(8, 30, 92, 84, BRANCO + (245,), r=6)
    t.rect(8, 52, 92, 56, VERM2 + (255,))
    t.rect(44, 48, 56, 62, VERM2 + (255,), r=2)
    t.rect(8, 30, 92, 40, BRANCO + (255,), r=6)


def _educacao(t: _Tela):
    t.poly([(50, 18), (96, 40), (50, 62), (4, 40)], BRANCO + (250,))
    t.poly([(24, 52), (50, 66), (76, 52), (76, 72), (50, 84), (24, 72)], BRANCO + (225,))
    t.line([(88, 44), (88, 70)], VERM2 + (255,), 2.2)
    t.ell(85, 68, 91, 76, fill=VERM2 + (255,))


def _agua(t: _Tela):
    t.poly([(50, 6), (80, 52), (20, 52)], AZUL + (255,))
    t.ell(20, 34, 80, 94, fill=AZUL + (255,))
    t.arc(30, 48, 62, 84, 100, 190, BRANCO + (200,), 3)
    t.rect(0, 80, 100, 96, BRANCO + (230,), r=3)
    t.rect(0, 84, 100, 92, AZUL + (255,), r=2)


def _politica(t: _Tela):
    """Palácio com frontão e colunas (instituições/governo)."""
    _solo(t)
    t.poly([(50, 8), (94, 34), (6, 34)], BRANCO + (250,))
    t.poly([(50, 16), (80, 31), (20, 31)], VERM2 + (255,))
    t.rect(8, 34, 92, 40, BRANCO + (250,), r=1)
    for i in range(6):
        x = 14 + i * 13.4
        t.rect(x, 42, x + 7, 80, BRANCO + (245,), r=1.2)
    t.rect(8, 80, 92, 85, BRANCO + (250,), r=1)
    t.rect(3, 85, 97, 90, BRANCO + (225,), r=1)


def _evento(t: _Tela):
    t.rect(10, 16, 90, 88, BRANCO + (250,), r=6)
    t.rect(10, 16, 90, 36, VERM2 + (255,), r=6)
    t.rect(10, 28, 90, 36, VERM2 + (255,))
    for x in (28, 72):
        t.rect(x - 2, 6, x + 2, 24, BRANCO + (255,), r=2)
    for r_ in range(3):
        for c in range(4):
            cor = VERM2 + (255,) if (r_, c) == (1, 2) else TINTA + (60,)
            t.rect(18 + c * 18, 44 + r_ * 14, 28 + c * 18, 52 + r_ * 14, cor, r=1.4)


def _generico(t: _Tela):
    _solo(t)
    for x, h in ((6, 26), (20, 40), (34, 30), (48, 56), (64, 36), (78, 46)):  # skyline
        t.rect(x, 90 - h, x + 12, 90, BRANCO + (200,))
        for j in range(3):
            t.rect(x + 3, 90 - h + 5 + j * 9, x + 9, 90 - h + 8 + j * 9, TINTA + (140,))
    # alfinete de localização
    t.ell(60, 4, 92, 36, fill=VERM2 + (255,))
    t.poly([(62, 26), (90, 26), (76, 52)], VERM2 + (255,))
    t.ell(70, 13, 82, 25, fill=BRANCO + (255,))


def _signos(t: _Tela):
    """Roda zodiacal: círculo com 12 marcas, estrelas e lua crescente."""
    cx, cy = 50, 52
    t.ell(10, 12, 90, 92, outline=BRANCO + (235,), w=2.2)
    t.ell(20, 22, 80, 82, outline=BRANCO + (150,), w=1.2)
    for i in range(12):
        a = math.radians(i * 30 - 90)
        x0, y0 = cx + 40 * math.cos(a), cy + 40 * math.sin(a)
        x1, y1 = cx + 30 * math.cos(a), cy + 30 * math.sin(a)
        t.line([(x0, y0), (x1, y1)], BRANCO + (200,), 1.3)
        t.ell(x0 - 2.2, y0 - 2.2, x0 + 2.2, y0 + 2.2, fill=AMARELO + (255,))
    # lua crescente no centro
    t.ell(36, 38, 64, 66, fill=BRANCO + (250,))
    t.ell(43, 34, 71, 62, fill=(0, 0, 0, 0))
    # estrelas de quatro pontas
    for (x, y, r) in ((86, 14, 5), (8, 78, 4), (92, 70, 3.5), (18, 10, 3)):
        t.poly([(x, y - r), (x + r * .3, y - r * .3), (x + r, y), (x + r * .3, y + r * .3),
                (x, y + r), (x - r * .3, y + r * .3), (x - r, y), (x - r * .3, y - r * .3)],
               AMARELO + (255,))


def _motivacional(t: _Tela):
    """Escada de degraus com bandeira no topo e sol nascendo."""
    t.ell(48, 6, 88, 46, fill=AMARELO + (235,))
    for i in range(5):
        x0 = 6 + i * 17
        topo = 80 - i * 13
        t.rect(x0, topo, x0 + 17, 92, BRANCO + (235 - i * 8,))
        t.rect(x0, topo, x0 + 17, topo + 2.2, VERM2 + (255,))
    # bandeira no último degrau
    t.rect(76.5, 8, 78, 28, BRANCO + (255,))
    t.poly([(78, 9), (92, 14), (78, 20)], VERM2 + (255,))


_DESENHOS = {
    "transito": _transito, "alerta": _alerta, "dengue": _dengue, "saude": _saude, "clima": _clima,
    "dinheiro": _dinheiro, "emprego": _emprego, "educacao": _educacao, "agua": _agua,
    "politica": _politica, "evento": _evento, "signos": _signos, "motivacional": _motivacional, "generico": _generico,
}


def camada(tema: str, w: int, h: int) -> Image.Image:
    """Camada RGBA w×h com a ilustração do tema posicionada na metade superior-direita."""
    t = _Tela()
    _DESENHOS.get(tema, _generico)(t)
    ilu = t.im.resize((LADO, LADO), Image.LANCZOS)
    ilu = ilu.rotate(-5, resample=Image.BICUBIC, expand=False)
    brilho = Image.new("RGBA", ilu.size, (0, 0, 0, 0))
    brilho.putalpha(ilu.getchannel("A").point(lambda v: int(v * 0.55)))
    brilho = brilho.filter(ImageFilter.GaussianBlur(26))
    ilu = ilu.copy()
    tela = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    x = w - LADO + 20
    y = int(h * 0.16)
    tela.alpha_composite(Image.new("RGBA", (1, 1), (0, 0, 0, 0)))
    # brilho vermelho atrás (identidade da marca)
    cor = Image.new("RGBA", ilu.size, VERM2 + (0,))
    cor.putalpha(brilho.getchannel("A"))
    tela.alpha_composite(cor, (x, y))
    tela.alpha_composite(ilu, (x, y))
    return tela
