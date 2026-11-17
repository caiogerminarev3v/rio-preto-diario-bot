# Especificação Visual Detalhada — Rio Preto Diário (`1080×1350`)

Use este documento para recriar o layout com fidelidade absoluta no Figma, Photoshop, Canva ou em qualquer outro motor de renderização.

---

## 1. Pilha de Camadas (de baixo para cima)

1. **Camada 1 — Foto de Fundo (`bg-photo`):**
   - Tamanho: `1080 × 1350 px`, preenchimento *Cover / Fill*.
   - Ajuste sutil recomendado: `contrast(1.03) saturate(1.04)`.
   - Posicionamento dinâmico (`focus`): padrão `"center 25%"`, ajustado por matéria para preservar rostos.

2. **Camada 2 — Vinheta Superior Esquerda (`top-scrim`):**
   - Garante contraste da logo branca e do mosaico sobre fotos muito claras.
   - Gradiente radial elíptico centrado em `(18%, 12%)` com raio `(58%, 42%)`:
     - `0%`: `rgba(6, 7, 11, 0.72)`
     - `50%`: `rgba(6, 7, 11, 0.42)`
     - `80%`: `rgba(6, 7, 11, 0.10)`
     - `100%`: `rgba(6, 7, 11, 0.00)`

3. **Camada 3 — Mosaico Diagonal com o Stroke da Logo (`watermark-layer`):**
   - Ativo: `../resources/watermark-tile.png` (gerado a partir de `logo-rio-preto-diario-outline.png`, com espaçamento intercalado em tijolo).
   - Escala de exibição do tile: `206 × 224 px` (cada logo vazada mede ~`174 × 90 px`).
   - Rotação: `-14°`.
   - Opacidade base: `18%` (`0.18`).
   - Máscara radial circular (`circle 520px` centrada em `x=17%, y=14%`):
     - `0%`: `95%` visível
     - `48%`: `62%` visível
     - `78%`: `16%` visível
     - `100%`: `0%` (fade completo antes de invadir o centro/direita).

4. **Camada 4 — Degradê Inferior Editorial (`bottom-scrim` + `brand-glow`):**
   - Ocupa os `66%` inferiores do canvas (`y = 459 px` até `1350 px`).
   - Paradas lineares verticais (de cima para baixo):
     - `0%`: `rgba(7, 8, 12, 0.00)`
     - `24%`: `rgba(7, 8, 12, 0.14)`
     - `48%`: `rgba(7, 8, 12, 0.50)`
     - `74%`: `rgba(7, 8, 12, 0.84)`
     - `100%`: `rgba(5, 6, 9, 0.96)`
   - **Toque sutil de marca (`brand-glow`):** brilho radial quase imperceptível no canto inferior esquerdo (`rgba(218, 3, 21, 0.14)` → `0%`) apenas para aquecer o preto neutro com o DNA vermelho do jornal.

5. **Camada 5 — Logo Oficial Recortada (`brand-bug`):**
   - Ativo: `../resources/logo-rio-preto-diario.png` (`1110 × 572 px`, RGBA transparente).
   - Posição: `x = 88 px`, `y = 78 px`.
   - Dimensão exibida: `width = 242 px` (`height ≈ 125 px`).
   - Sombra de separação: `drop-shadow(0 4px 16px rgba(0, 0, 0, 0.60))`.

6. **Camada 6 — Bloco Tipográfico Inferior (`content`):**
   - Ancorado na base: `left = 88 px`, `right = 108 px` (largura útil `884 px`), `bottom = 70 px`.
   - Composto por 3 subelementos verticais:
     1. **Linha de Editoria (`kicker-row`, margem inferior `18 px`):**
        - Modo `padrao` / `editorial`: barra vertical `#FF1F34` (`6 × 22 px`, `border-radius: 3 px`, leve brilho `0 0 10px rgba(255,31,52,0.45)`) + espaço `12 px` + texto em caixa alta (`Plus Jakarta Sans Bold 700`, `20 px`, tracking `0.15em`, `rgba(255,255,255,0.92)`).
        - Modo `urgente`: pílula `#DA0315` (`padding: 5px 12px`, `border-radius: 5px`) com ponto branco `8 × 8 px` + `URGENTE` (`16 px`, peso `800`, tracking `0.14em`) + nome da editoria ao lado.
     2. **Manchete Principal (`headline`):**
        - Fonte: `Plus Jakarta Sans ExtraBold (800)` (ou `Playfair Display ExtraBold 800` na variante `editorial`).
        - Cor: `#FFFFFF`, sombra suave `0 3px 18px rgba(0, 0, 0, 0.55)`.
        - Tracking: `-0.025em` (`-0.015em` na variante serifada).
        - Quebra balanceada (`text-wrap: balance`), nunca excedendo `395 px` de altura total.
     3. **Assinatura de Rodapé (`footer-brand`, margem superior `26 px`):**
        - Filete horizontal `#FF1F34` (`44 × 4 px`, `border-radius: 2 px`) + espaço `14 px` + `@RIOPRETODIARIO` (`15 px`, peso `700`, tracking `0.22em`, `rgba(255,255,255,0.74)`).

---

## 2. Escalonamento Tipográfico da Manchete

| Comprimento do Título | `font-size` | `line-height` | Linhas Esperadas |
| :--- | :---: | :---: | :---: |
| `<= 50` caracteres | `60 px` | `1.12` | 2 linhas |
| `51 – 75` caracteres | `54 px` | `1.13` | 2–3 linhas |
| `76 – 100` caracteres | `48 px` | `1.15` | 3–4 linhas |
| `101 – 130` caracteres | `42 px` | `1.16` | 4 linhas |

> **Regra de segurança:** caso uma palavra muito longa ou caixa alta force o bloco acima de `395 px` de altura, reduza `2 px` por iteração até caber com folga (mínimo `34 px`).
