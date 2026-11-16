# 2. Telegram: aprovação com um toque

## 2.1 Criar o bot
1. No Telegram, abra uma conversa com **@BotFather**.
2. Envie `/newbot`, dê um nome (ex.: *Redação Rio Preto Diário*) e um usuário terminado em `bot`
   (ex.: `riopretodiario_redacao_bot`).
3. O BotFather responde com um **token** no formato `123456789:AA...`. Guarde-o.

## 2.2 Descobrir o seu chat ID
1. Mande qualquer mensagem (ex.: "oi") para o seu bot.
2. Abra no navegador, trocando o token:
   `https://api.telegram.org/botSEU_TOKEN/getUpdates`
3. Procure `"chat":{"id":123456789` e guarde esse número.

**Quer aprovar em equipe?** Crie um grupo, adicione o bot e mande uma mensagem no grupo.
O ID do grupo é **negativo** (ex.: `-1001234567890`).

## 2.3 Secrets
| Secret do GitHub | Valor |
|---|---|
| `TELEGRAM_BOT_TOKEN` | token do BotFather (um só bot para todas as contas) |
| `TELEGRAM_CHAT_ID_RIO_PRETO_DIARIO` | seu chat ID ou o ID do grupo |

## Como fica no dia a dia
Para cada notícia local você recebe:
1. A **arte** com a fonte e o link da matéria original.
2. A **legenda completa** com os botões **✅ Publicar** e **❌ Descartar**.

O robô lê as respostas a cada 15 minutos. Depois disso o botão muda para
"✅ Aprovado — na fila", "📲 Publicado no Instagram" ou "⌛ Expirou".
Se algo falhar na publicação, você recebe um aviso ⚠️ no mesmo chat.

> Só cliques vindos do chat configurado são aceitos. Se outra pessoa achar o bot, ela não consegue aprovar nada.
