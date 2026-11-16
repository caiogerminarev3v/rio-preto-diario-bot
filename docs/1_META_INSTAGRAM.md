# 1. Instagram + API da Meta (feito em 16/11/2026)

## Situação atual do Rio Preto Diário
| Item | Valor |
|---|---|
| App na Meta | **Rio Preto Diario Bot**, ID `1782362089538715` |
| Portfólio empresarial | **V3V Agencia Criativa 2** |
| Tipo de acesso | API do Instagram com **login unificado**: token de usuário do sistema, **que não expira** |
| Conta | **@riopretodiario**, ID `17841449511512909` |
| Endereço da API | `graph.facebook.com` |

> A Meta não oferece mais o "login do Instagram" para apps novos. Apps criados agora usam o
> **login unificado**, que exige um portfólio empresarial. Em troca, o token não vence.

## Passo a passo (para refazer ou para as secretarias)
1. **developers.facebook.com → Meus apps → Criar aplicativo.**
   Escolha o caso de uso **"Gerenciar mensagens e conteúdo no Instagram"**. Se for a mesma estrutura,
   reaproveite o app Rio Preto Diario Bot.
2. **Casos de uso → Personalizar → Permissões e recursos.**
   Adicione `instagram_business_basic` e `instagram_business_content_publish`.
3. **API setup with Unified login.** Conecte um **portfólio empresarial** e clique em
   **Criar nova configuração**. O modelo padrão já gera um token de usuário do sistema que não expira.
4. **Funções do app → Adicionar pessoas → Testador do Instagram.** Digite o @ da conta.
5. **No Instagram** (logado na conta): **Configurações → Apps e sites → Convites do testador → Aceitar**.
6. **De volta ao passo 2 da página de configuração ("Gerar tokens de acesso"):**
   a conta aparece com o ID. Clique em **Gerar token** e autorize na janela que abrir.
   **Copie o token na hora** e cole direto no secret do GitHub. Nunca coloque o token em chat, e-mail ou arquivo do repositório.

## Secrets do GitHub
| Secret | Valor |
|---|---|
| `IG_TOKEN_RIO_PRETO_DIARIO` | o token gerado no passo 6 |
| `IG_USER_ID_RIO_PRETO_DIARIO` | `17841449511512909` |

## Testar o token (opcional, no seu computador)
```bash
export IG_TOKEN_RIO_PRETO_DIARIO="cole-o-token"
export IG_USER_ID_RIO_PRETO_DIARIO=17841449511512909
python -m rpd testar-instagram --conta rio_preto_diario
```
Se estiver tudo certo, o comando mostra `✅ Conectado como @riopretodiario` e quantos posts ainda podem ser feitos nas próximas 24h.
Esse teste não publica nada.

## Limites da Meta
- No máximo **100 posts a cada 24h** via API. O robô vem limitado a 10 por dia.
- Imagens JPEG de até 8 MB. O robô gera cerca de 300 KB.
