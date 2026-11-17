---
name: rio-preto-diario-social
description: >-
  Guia completo de direção de arte, layout e produção em massa de artes de
  notícias para o Instagram (1080x1350) do jornal Rio Preto Diário. Use sempre
  que criar, revisar, adaptar no Figma/Canva ou gerar em lote posts editoriais
  no padrão oficial do Rio Preto Diário.
---

# Rio Preto Diário — Skill Oficial de Design & Produção Social

Esta skill padroniza a linguagem visual e o fluxo de geração em massa dos cards de notícias do **Rio Preto Diário** para Instagram (`1080×1350`). Foi projetada para funcionar tanto como **manual técnico de direção de arte** (Figma, Photoshop, Canva) quanto como **instrução executável para automação** via HTML/CSS + Chrome Headless (`scripts/render.mjs` e `scripts/server.mjs`).

---

## 1. Conceito Visual e Arquitetura do Layout

O sistema combina a leitura imediata de grandes portais digitais (inspiração na clareza do G1) com a identidade tipográfica e cromática do **Rio Preto Diário**, sem elementos que poluam rostos ou cenas jornalísticas:

1. **Formato universal `4:5` (`1080×1350 px`):** ocupa a altura máxima no feed do Instagram e mantém compatibilidade garantida com APIs de agendamento (Meta Graph API, n8n, Make).
2. **Margens seguras para a grade `3:4` do perfil:** a visualização em grade `3:4` recorta ~`34 px` de cada lateral em imagens `4:5`. Por isso, **logo, editoria e manchete respeitam `88 px` à esquerda e `108 px` à direita**.
3. **Topo limpo com a logo verdadeira:** usa a logo oficial recortada sem fundo ([logo-rio-preto-diario.png](./resources/logo-rio-preto-diario.png)) no canto superior esquerdo, sem linha circular cortando a foto.
4. **Mosaico diagonal vazado (*stroke*):** atrás da logo, repete a versão vazada da marca ([logo-rio-preto-diario-outline.png](./resources/logo-rio-preto-diario-outline.png) / [watermark-tile.png](./resources/watermark-tile.png)) inclinada a `-14°` com máscara radial suave que desaparece antes do centro da foto.
5. **Dupla proteção de contraste:** vinheta radial escura no canto superior esquerdo (segura a logo branca mesmo sobre céu claro ou tela branca) + degradê escuro inferior multi-parada (garante contraste AAA para a manchete sobre qualquer foto).

---

## 2. Especificação Rápida (Resumo Executivo)

| Elemento | Valor / Regra Oficial | Referência |
| :--- | :--- | :--- |
| **Canvas** | `1080 × 1350 px` (aspecto `4:5`, JPG `q=94` ou PNG) | [design-system.json](./resources/design-system.json) |
| **Margens Seguras** | Esquerda `88 px` · Direita `108 px` · Topo `78 px` · Base `70 px` | [design-spec.md](./references/design-spec.md) |
| **Vermelho Marca / Avatar** | `#DA0315` (`RGB 218, 3, 21`) | [avatar-rpd.svg](./resources/avatar-rpd.svg) |
| **Vermelho Acento (UI/Barras)** | `#FF1F34` (alta luminosidade sobre foto escura) | — |
| **Preto Editorial (Scrim)** | `#06070A` / `#07080C` (nunca `#000` chapado sem transição) | — |
| **Logo Superior Esquerda** | `left: 88 px`, `top: 78 px`, largura `242 px` + sombra suave | [logo-rio-preto-diario.png](./resources/logo-rio-preto-diario.png) |
| **Marca d'Água Stroke** | Tile `206 × 224 px`, rotação `-14°`, opacidade `0.18`, fade radial `520 px` | [watermark-tile.png](./resources/watermark-tile.png) |
| **Editoria (Kicker)** | `Plus Jakarta Sans Bold (700)`, `20 px`, caixa alta, tracking `0.15em` + barra `#FF1F34` (`6 × 22 px`) | — |
| **Manchete (`h1`)** | `Plus Jakarta Sans ExtraBold (800)`, `#FFFFFF`, tracking `-0.025em`, `text-wrap: balance` | [design-spec.md](./references/design-spec.md) |
| **Rodapé Sutil** | Filete `44 × 4 px` (`#FF1F34`) + `@RIOPRETODIARIO` (`15 px`, tracking `0.22em`) | — |

Para detalhes exatos de gradientes, ordem de camadas e tabela de redução automática de fonte por número de caracteres, consulte [design-spec.md](./references/design-spec.md).

---

## 3. Regras Editoriais e de Fotografia (Obrigatórias)

### Texto da Manchete
- **Faixa ideal:** entre **45 e 95 caracteres** (2 a 4 linhas).
- **Limite rígido:** **125 caracteres**. Nunca deixe passar de 5 linhas nem encostar na área superior do mosaico.
- **Escalonamento padrão da fonte:**
  - Até `50` caracteres → `60 px` (`line-height: 1.12`)
  - `51 a 75` caracteres → `54 px` (`line-height: 1.13`)
  - `76 a 100` caracteres → `48 px` (`line-height: 1.15`)
  - `101 a 130` caracteres → `42 px` (`line-height: 1.16`)
- **Variante `editorial`:** utiliza `Playfair Display ExtraBold (800)` para artigos, opinião ou reportagens especiais.
- **Variante `urgente`:** substitui a barra vertical da editoria pela pílula vermelha `• URGENTE` em `#DA0315`.

### Escolha e Enquadramento da Foto (`focus`)
1. **Nunca use foto com marca d'água ou selo de outro portal** (ex.: logos de TV/jornais no canto).
2. **Fotos verticais com bordas borradas (pillarbox):** recorte apenas o centro nítido antes de aplicar no card.
3. **Posição de assunto (`object-position`):**
   - **Retrato solo:** ajuste o foco horizontal para deslocar o rosto levemente à direita ou centro-direita (ex.: `"34% 16%"`), mantendo a região superior esquerda livre para a logo.
   - **Grupo de pessoas:** use foco superior (`"50% 0%"` a `"50% 15%"`) para não cortar cabeças na base nem sobrepor a logo nos rostos.
   - **Objeto ou tela clara à direita (ex.: celular):** mantenha `"70% 45%"` e confie na vinheta `.top-scrim` para segurar a leitura da logo branca.

---

## 4. Fluxos de Trabalho

### Fluxo A — Produção Manual (Figma / Photoshop / Canva)
1. Crie um frame `1080 × 1350 px` com guias de segurança em `x = 88`, `x = 972`, `y = 78` e `y = 1280`.
2. Siga rigorosamente a pilha de camadas descrita em [design-spec.md](./references/design-spec.md) usando os PNGs da pasta [resources](./resources/).
3. Exporte em JPEG (`qualidade >= 92`) ou PNG.

### Fluxo B — Produção em Massa Automatizada (Projeto Local / n8n / Make)
Quando estiver na raiz do projeto:
1. Edite ou gere um arquivo JSON seguindo o contrato em [automation-guide.md](./references/automation-guide.md) (e `schema/post.schema.json`).
2. **Modo Lote (CLI):**
   ```bash
   node scripts/render.mjs --input data/noticias-exemplo.json --out output --format jpeg
   ```
3. **Modo API HTTP (para n8n / Make):**
   ```bash
   node scripts/server.mjs
   ```
   Envie `POST http://127.0.0.1:3456/render` com `{ "headline", "category", "image", "focus", "variant" }` para receber o binário `image/jpeg` pronto.

---

## 5. Checklist de QA Antes de Aprovar um Lote

- [ ] A logo `RIO PRETO DIÁRIO` está legível mesmo se o canto superior esquerdo da foto for branco ou céu claro?
- [ ] Nenhum rosto principal está coberto pela logo no topo ou pela manchete na base?
- [ ] A manchete tem no máximo 4 linhas (ou 5 em casos extremos) sem palavras órfãs feias e com contraste alto?
- [ ] O arquivo gerado tem exatamente `1080 × 1350 px` e respeita a margem lateral de `88 px` (sem risco de corte na grade `3:4` do Instagram)?
- [ ] A foto de fundo está nítida e livre de logos concorrentes ou bordas borradas?
