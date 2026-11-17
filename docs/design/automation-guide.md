# Guia de Automação e Integração em Massa

Este guia detalha como plugar o template do **Rio Preto Diário** em pipelines diários de raspagem e publicação automática (n8n, Make, Python ou Node.js).

---

## 1. Contrato JSON de Entrada (`post.schema.json`)

Cada notícia enviada ao gerador aceita os campos abaixo:

```json
{
  "id": "2026-11-17-saude-rio-preto",
  "category": "RIO PRETO • SAÚDE",
  "headline": "Coronel apresenta projeto de R$ 50 milhões para reforçar a Saúde",
  "image": "https://portal.exemplo.com.br/fotos/materia.jpg",
  "focus": "34% 16%",
  "variant": "padrao",
  "accentColor": "#FF1F34",
  "showFooter": true,
  "footerText": "@RIOPRETODIARIO"
}
```

### Detalhamento dos Campos
- **`id`** *(obrigatório no CLI)*: nome do arquivo de saída (sem extensão).
- **`headline`** *(obrigatório)*: título limpo da matéria. Recomenda-se truncar/reescrever via LLM na automação para **55–90 caracteres** (evitar prefixos como `"VÍDEO:"`, `"VEJA:"`, `"SAIBA MAIS"`).
- **`image`** *(obrigatório)*: URL `https://` direta da foto ou caminho local relativo/absoluto. Prefira imagens com largura `>= 900 px` sem marcas d'água.
- **`category`** *(opcional)*: editoria ou cidade em caixa alta (máx. 36 caracteres). Se vazio, oculta a linha de editoria automaticamente.
- **`focus`** *(opcional, padrão `"center 25%"`)*: ponto focal CSS `object-position`.
  - Dica para automação com visão computacional/IA: se houver pessoa única centralizada, enviar `"36% 18%"`; se houver grupo de pessoas, enviar `"50% 8%"`; para arquitetura/paisagem, `"center 40%"`.
- **`variant`** *(opcional, padrão `"padrao"`)*: `"padrao"` | `"urgente"` | `"editorial"`.
- **`accentColor`** *(opcional, padrão `"#FF1F34"`)*: hex de 6 dígitos para campanhas especiais ou editorias temáticas.
- **`showFooter`** *(opcional, padrão `true`)* e **`footerText`** *(opcional, padrão `"@RIOPRETODIARIO"`)*: controla a assinatura na base.

---

## 2. Integração via API HTTP (n8n / Make)

1. Inicie o servidor local de renderização na máquina/container:
   ```bash
   PORT=3456 node scripts/server.mjs
   ```
   *(Em containers Linux sem Chrome no caminho do macOS, defina `CHROME_PATH=/usr/bin/chromium`.)*

2. No **n8n** (nó *HTTP Request*):
   - **Method:** `POST`
   - **URL:** `http://127.0.0.1:3456/render` (ou URL do container na mesma rede Docker)
   - **Body Content Type:** `JSON`
   - **Response Format:** `File` (binário `image/jpeg`)

3. **Pipeline recomendado de publicação diária:**
   - **Gatilho:** RSS / Web Scraper → Filtro anti-duplicidade (banco/Planilha).
   - **LLM (Curadoria):** Reescreve a manchete para até 90 caracteres no tom jornalístico do Rio Preto Diário, define `category`, escolhe `variant` (`padrao` vs `urgente`) e sugere `focus`.
   - **Renderização:** `POST /render` devolve o JPG `1080×1350`.
   - **Storage Público:** Upload para S3 / Cloudinary / Supabase Storage (a Meta Graph API exige URL pública HTTPS para publicar no feed).
   - **Aprovação (opcional) + Publicação:** Envia prévia no Telegram/WhatsApp ou publica direto via Instagram Graph API com legenda completa e créditos da fonte.

---

## 3. Integração via CLI em Lote

Para gerar dezenas ou centenas de artes de uma só vez a partir de um JSON gerado pelo seu scraper:

```bash
node scripts/render.mjs \
  --input data/noticias-do-dia.json \
  --out output/lote-hoje \
  --format jpeg \
  --quality 94
```
O processo abre uma única instância do Chrome Headless e captura cada card em ~`120–180 ms`.
