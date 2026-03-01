# 🚀 BookBot — Deploy no Railway

## O que você vai precisar
- Conta no GitHub (gratuito)
- Conta no Railway (gratuito) → railway.app
- Suas credenciais já existentes:
  - Token do Telegram Bot
  - OpenAI API Key
  - Supabase URL e Key

---

## ETAPA 1 — Criar repositório no GitHub

1. Acesse **github.com** e faça login
2. Clique em **"New repository"**
3. Nome: `bookbot`
4. Deixe **Private** selecionado
5. Clique em **"Create repository"**
6. Na próxima tela clique em **"uploading an existing file"**
7. Faça upload dos 3 arquivos:
   - `bot.py`
   - `requirements.txt`
   - `Procfile`
8. Clique em **"Commit changes"**

---

## ETAPA 2 — Deploy no Railway

1. Acesse **railway.app** e clique em **"Login with GitHub"**
2. Clique em **"New Project"**
3. Clique em **"Deploy from GitHub repo"**
4. Selecione o repositório `bookbot`
5. Clique em **"Deploy Now"**

---

## ETAPA 3 — Configurar variáveis de ambiente

No Railway, após o deploy:

1. Clique no seu projeto
2. Clique em **"Variables"**
3. Adicione cada variável clicando em **"New Variable"**:

| Nome | Valor |
|------|-------|
| `TELEGRAM_TOKEN` | Token do seu BotFather |
| `OPENAI_API_KEY` | Sua chave da OpenAI (sk-...) |
| `SUPABASE_URL` | `https://llewcpyjgpwsejaqhbqk.supabase.co` |
| `SUPABASE_KEY` | `sb_secret_ferp0ySSKeyaXRSVKvsKww_TbVo2zGm` |

4. Após adicionar todas, o Railway vai reiniciar automaticamente

---

## ETAPA 4 — Verificar se está funcionando

1. No Railway clique em **"Deployments"**
2. Clique no último deploy
3. Clique em **"View Logs"**
4. Deve aparecer: `Bot iniciado!`

---

## ETAPA 5 — Testar no Telegram

Abra seu bot e envie:
```
oi
```

Deve responder com o menu! 🎉

---

## Solução de problemas

| Problema | Solução |
|---------|---------|
| Bot não responde | Verificar logs no Railway |
| "TELEGRAM_TOKEN not found" | Verificar variáveis de ambiente |
| Erro no Supabase | Verificar SUPABASE_URL e SUPABASE_KEY |
| Erro na OpenAI | Verificar OPENAI_API_KEY e créditos |
