# 4. Adicionando as secretarias

Cada secretaria é **mais uma conta** no mesmo robô. O código é o mesmo e só muda a configuração.

## Passo a passo (por secretaria)
1. Copie `contas/_modelo_secretaria.yaml` para `contas/sec_saude.yaml`, `contas/sec_educacao.yaml` etc.
2. No arquivo, troque `id`, `nome`, `arroba`, as cores e as `filtro_palavras`, que são as palavras
   que identificam as notícias daquela secretaria no site da Prefeitura.
3. Coloque o logo em `assets/sec_saude/logo.png`.
4. Repita o **doc 1** para o Instagram da secretaria. O mesmo app da Meta serve: é só **Adicionar conta**
   e gerar outro token.
5. Crie os secrets `IG_TOKEN_SEC_SAUDE`, `IG_USER_ID_SEC_SAUDE` e `TELEGRAM_CHAT_ID_SEC_SAUDE`.
   Use um grupo de Telegram com a equipe de comunicação da secretaria.
6. Em `.github/workflows/redacao.yml`, descomente e ajuste as 3 linhas da secretaria.
   Em `renovar-token.yml`, adicione a conta na `matrix`.
7. Mude `ativo: true` no arquivo da conta.

## Cuidados específicos de perfis oficiais
- O modelo já vem com **aprovação humana em 100% dos posts**. Para conta de governo, mantenha assim.
- **Sem promoção pessoal**: o tom editorial instrui a IA a destacar o serviço e não a autoridade,
  conforme o art. 37, §1º da Constituição.
- **Período eleitoral**: a lei eleitoral restringe a publicidade institucional nos 3 meses antes das eleições.
  Nas próximas municipais (2028), confirme com a Procuradoria/Secom do município e,
  se for o caso, mude `ativo: false` durante o período.
- Prefira como fonte o **próprio site da Prefeitura** e os comunicados da secretaria.
  Também é possível adicionar uma pasta ou planilha de pautas internas como fonte.
