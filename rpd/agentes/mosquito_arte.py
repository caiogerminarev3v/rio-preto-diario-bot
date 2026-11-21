from PIL import Image, ImageDraw, ImageFilter
import math

def mosquito(tam=700, asa=0.0, cor_corpo=(34,30,38), listra=(245,245,248), olho=(255,31,52)):
    """Desenho original de um Aedes cartunesco, olhando para a esquerda. asa: 0..1 (batida)."""
    S = 4
    w = h = tam * S
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    u = w / 100.0
    def P(x, y): return (x * u, y * u)
    # pernas (6), com joelho
    pernas = [((50,56),(62,76),(54,96)), ((54,57),(70,72),(68,94)), ((58,56),(78,68),(84,88)),
              ((48,55),(36,74),(42,94)), ((44,53),(26,70),(24,90)), ((60,50),(82,56),(94,72))]
    for a, b, c in pernas:
        d.line([P(*a), P(*b), P(*c)], fill=cor_corpo, width=int(2.0*u), joint="curve")
        d.line([P(*(b[0]-1.4, b[1]-0.4)), P(*(b[0]+1.4, b[1]+0.4))], fill=listra, width=int(1.7*u))
    # asas (atrás do corpo), batendo
    ang = math.sin(asa * math.pi * 2) * 14
    for sinal, alpha in ((-1, 150), (1, 200)):
        asa_im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        ad = ImageDraw.Draw(asa_im)
        ad.ellipse((P(54, 8)[0], P(54, 8)[1], P(92, 40)[0], P(92, 40)[1]), fill=(210, 225, 255, alpha),
                   outline=(255, 255, 255, 230), width=int(0.9*u))
        asa_im = asa_im.rotate(ang * sinal, center=P(56, 40), resample=Image.BICUBIC)
        im.alpha_composite(asa_im)
    d = ImageDraw.Draw(im)
    # abdômen com listras
    d.ellipse((*P(48, 40), *P(88, 66)), fill=cor_corpo)
    for i, x in enumerate((56, 64, 72, 80)):
        d.arc((*P(x-4, 40), *P(x+4, 66)), 300, 60, fill=listra, width=int(1.8*u))
    # tórax
    d.ellipse((*P(32, 36), *P(58, 64)), fill=cor_corpo)
    d.arc((*P(38, 36), *P(52, 64)), 270, 90, fill=listra, width=int(1.3*u))
    # cabeça
    d.ellipse((*P(18, 38), *P(40, 60)), fill=cor_corpo)
    # olho
    d.ellipse((*P(21, 41), *P(32, 52)), fill=(255, 255, 255))
    d.ellipse((*P(22.5, 43), *P(30, 51)), fill=olho)
    d.ellipse((*P(24, 44), *P(27, 48)), fill=(20, 20, 24))
    d.ellipse((*P(24.6, 44.4), *P(25.8, 45.6)), fill=(255, 255, 255))
    # probóscide
    d.line([P(20, 54), P(8, 62), P(3, 70)], fill=(70,64,78), width=int(2.2*u), joint="curve")
    # antenas
    d.line([P(28, 39), P(26, 28), P(20, 22)], fill=cor_corpo, width=int(1.0*u))
    d.line([P(32, 38), P(34, 28), P(30, 20)], fill=cor_corpo, width=int(1.0*u))
    return im.resize((tam, tam), Image.LANCZOS)


