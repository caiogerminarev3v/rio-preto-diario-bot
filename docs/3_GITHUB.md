# 3. GitHub: onde o robô roda (grátis)

## 3.1 Criar o repositório
1. Crie uma conta em **github.com**, se ainda não tiver.
2. **New repository** → nome `rio-preto-diario-bot` → marque **Public**.
   - *Por que público?* Assim os minutos do GitHub Actions são ilimitados e as artes ganham link público
     para o Instagram buscar. **Tokens e senhas ficam nos Secrets, que são criptografados e invisíveis
     mesmo em repositório público.**
   - Prefere privado? Funciona, mas crie uma conta grátis em **imgbb.com**, gere uma API key e siga a seção 3.3.
     O plano grátis do GitHub para repositório privado tem 2.000 min/mês, e o robô a cada 15 min gasta perto disso.
     Nesse caso, mude o `cron` para `*/30`.
3. Envie todos os arquivos desta pasta para o repositório. Pode ser pelo botão
   **"uploading an existing file"**, arrastando a pasta inteira, inclusive `.github`.

## 3.2 Chave da IA (Anthropic)
1. Entre em **console.anthropic.com → API Keys → Create Key**.
2. Coloque créditos em **Billing**. US$ 20 duram mais de um mês.

## 3.3 Cadastrar os Secrets
No repositório: **Settings → Secrets and variables → Actions → New repository secret**.

| Nome | De onde vem |
|---|---|
| `ANTHROPIC_API_KEY` | passo 3.2 |
| `IG_TOKEN_RIO_PRETO_DIARIO` | doc 1 |
| `IG_USER_ID_RIO_PRETO_DIARIO` | doc 1 |
| `TELEGRAM_BOT_TOKEN` | doc 2 |
| `TELEGRAM_CHAT_ID_RIO_PRETO_DIARIO` | doc 2 |
| `GH_PAT` | *opcional*: só para contas com token que expira (passo 3.4) |
| `IMGBB_API_KEY` | *só se o repositório for privado* |

Se for usar imgbb: na aba **Variables**, crie `RPD_HOSPEDAGEM` = `imgbb`.

## 3.4 Renovação automática do token (opcional)
**O Rio Preto Diário não precisa disto**, porque o token dele não expira. Só vale para contas com token de login do Instagram, que vence em 60 dias. O workflow `renovar-token.yml` renova no dia 1 e no dia 15 de cada mês.
Para ele poder regravar o secret, crie um token do GitHub:
1. **github.com → Settings (do seu perfil) → Developer settings → Personal access tokens → Fine-grained tokens → Generate**.
2. Em *Repository access*, escolha **só este repositório**.
3. Em *Permissions → Repository → Secrets*, marque **Read and write**.
4. Salve o valor como secret `GH_PAT`.

## 3.5 Ligar e testar
1. Aba **Actions** → aceite ativar os workflows.
2. Abra **Redação automática → Run workflow**.
3. Abra a execução e veja o log, que mostra cada agente trabalhando.
4. Em poucos minutos chegam os primeiros pedidos de aprovação no Telegram.

Depois disso ele roda sozinho **a cada 15 minutos, das 6h às 23h45**.

### Se algo der errado
| Sintoma no log | Solução |
|---|---|
| `Fonte falhou: ...` | Uma fonte saiu do ar ou mudou de endereço. As outras continuam. Ajuste em `contas/*.yaml` |
| `Variável ... não definida` | Falta um Secret ou ele está com o nome errado |
| `Invalid OAuth access token` | Token do Instagram vencido. Gere outro (doc 1, passo 1.3) |
| `Imagem não ficou pública` | O repositório não é público. Use imgbb |
| Nada chega no Telegram | Confira o chat ID e se você mandou "oi" para o bot |
