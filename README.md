# 🗞 Rio Preto Diário — Redação automática

Robô de notícias para Instagram: uma "redação" de agentes de IA que procura
notícias de São José do Rio Preto e do Brasil, escreve a legenda, cria a arte
e publica sozinho. Ou pede a sua aprovação no Telegram antes de publicar.

Ele foi feito para várias contas. Comece pelo **Rio Preto Diário** e depois adicione
as **secretarias** (veja `docs/4_SECRETARIAS.md`).

---

## Como a redação funciona

```
 ┌─────────────┐   ┌──────────────┐   ┌───────────┐   ┌────────────┐   ┌────────────┐
 │  PAUTEIRO   │ → │ EDITOR-CHEFE │ → │  REDATOR  │ → │  CHECADOR  │ → │  DESIGNER  │
 │ lê g1, Pref.│   │ escolhe as   │   │ escreve   │   │ confere    │   │ monta arte │
 │ Ag. Brasil, │   │ melhores,    │   │ manchete e│   │ cada fato  │   │ 1080x1350  │
 │ Google Not. │   │ tira repetida│   │ legenda   │   │ com a fonte│   │ com a marca│
 └─────────────┘   └──────────────┘   └───────────┘   └────────────┘   └─────┬──────┘
                                                                             │
                     ┌───────────────────────────────────────────────────────┤
                     ▼                                                       ▼
          LOCAL ou SENSÍVEL                                           BRASIL (comum)
   📱 Telegram: [✅ Publicar] [❌ Descartar]                          vai direto para a fila
                     │                                                       │
                     └───────────────►  FILA  ◄──────────────────────────────┘
                                         │  respeita horário (7h–22h),
                                         │  intervalo entre posts e limite diário
                                         ▼
                                  📲 PUBLICADOR (API oficial do Instagram)
```

| Agente | O que faz | Usa IA? |
|---|---|---|
| Pauteiro | Lê as fontes a cada hora e ignora o que já viu ou o que tem mais de 18h | Não |
| Editor-chefe | Escolhe até 4 pautas por rodada, classifica a editoria e marca as **sensíveis** e **urgentes** | Sim |
| Redator | Escreve manchete, linha fina, legenda e hashtags, só com fatos da fonte e sempre creditando o veículo | Sim |
| Checador | Revisa o texto contra a fonte. Se algo não bate, manda o post para aprovação humana | Sim |
| Designer | Gera a arte com logo, cores, chapéu da editoria e selo URGENTE | Não |
| Aprovação | Envia arte e legenda para o seu Telegram com botões | Não |
| Publicador | Publica via Instagram Graph API | Não |

### Regras de segurança jornalística já embutidas
- **Notícia local sempre passa pela sua aprovação** (como você escolheu). Notícia nacional sai sozinha,
  **exceto** se o editor ou o checador marcar como sensível: crime com pessoa identificada, morte,
  menores, acusações ou política eleitoral.
- O texto é **reescrito**, nunca copiado, e sempre traz `Fonte: <veículo>`.
- **Fotos só de fontes que permitem**: Agência Brasil (licença Creative Commons) e Prefeitura,
  sempre com crédito. Matérias de jornais comerciais (g1, Diário da Região etc.) ganham **arte tipográfica**
  com as cores da marca, para não usar a foto deles.
- Pedidos de aprovação sem resposta expiram em 12h (a notícia fica velha).

---

## Instalação (uma vez, cerca de 1 hora)

1. **Instagram + Meta** → `docs/1_META_INSTAGRAM.md` (conta profissional e token da API)
2. **Telegram** → `docs/2_TELEGRAM.md` (bot de aprovação, 5 minutos)
3. **GitHub** → `docs/3_GITHUB.md` (subir o projeto, cadastrar os segredos e ligar)
4. **Sua marca**: troque `assets/rio_preto_diario/logo.png` (PNG transparente e claro) e as cores em
   `contas/rio_preto_diario.yaml` → `visual.cores`.

### Custos estimados
| Item | Custo |
|---|---|
| GitHub Actions (repositório público) | grátis |
| API do Instagram e Telegram | grátis |
| API do Claude (Anthropic) | cerca de US$ 0,02 a 0,05 por post (4 agentes de IA) → **~US$ 10–15/mês** com 10 posts/dia |

---

## Comandos úteis (no seu computador, opcional)

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=...

python -m rpd fontes  --conta rio_preto_diario   # testa se as fontes estão respondendo
python -m rpd simular --conta rio_preto_diario   # gera artes e legendas em saida/ SEM publicar
python -m rpd ciclo   --conta rio_preto_diario   # um ciclo real (precisa de todos os segredos)
```

## Onde mexer

| Quero… | Arquivo |
|---|---|
| Trocar cores, logo, @ | `contas/rio_preto_diario.yaml` → `visual`, `arroba` |
| Mudar horários, intervalo, posts/dia | `contas/rio_preto_diario.yaml` → `publicacao` |
| Publicar local sem aprovação (não recomendado) | `publicacao.local: automatico` |
| Adicionar ou remover fontes | `contas/rio_preto_diario.yaml` → `fontes` |
| Mudar o estilo de texto | `editorial.tom` e `rpd/agentes/redator.py` |
| Mudar o layout da arte | `rpd/agentes/designer.py` |
| Frequência do robô | `.github/workflows/redacao.yml` → `cron` |

## Estrutura

```
contas/                 uma configuração por perfil (jornal, secretarias…)
rpd/agentes/            pauteiro, editor, redator, checador, designer, aprovacao, publicador
rpd/__main__.py         orquestrador do ciclo
dados/<conta>/          memória da redação (o que já viu, fila, publicados)
publicacoes/<conta>/    artes geradas (servem de link público para o Instagram)
.github/workflows/      agendamentos (ciclo a cada 15 min + renovação do token)
```
