# 📡 iPhone Price Radar

Radar automático que monitora preços de iPhone 15, 16 e 17 em todas as principais lojas brasileiras, rodando de hora em hora no GitHub — sem precisar de servidor próprio.

## 🔔 O que ele detecta?

| Sinal | Critério |
|-------|----------|
| 🚨 **Bug de Preço** | Mais de 25% abaixo da média dos últimos 6 meses |
| ⭐ **Menor Preço Histórico** | Novo mínimo nos últimos 6 meses |
| 🔥 **Boa Oferta** | Mais de 5% abaixo da média dos últimos 6 meses |

## 🛒 Lojas monitoradas
- Mercado Livre (via API oficial)
- Amazon BR
- Magazine Luiza
- KaBuM!

---

## ⚙️ Setup em 5 passos

### Passo 1 — Criar o Bot no Telegram

1. Abra o Telegram e busque por **@BotFather**
2. Envie o comando `/newbot`
3. Escolha um nome para o bot (ex: `iPhone Radar`)
4. Escolha um username (ex: `iphone_radar_bot`)
5. O BotFather vai te enviar um **token** assim:
   ```
   123456789:AAGxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   ```
   👉 **Guarde esse token** — você vai precisar dele.

### Passo 2 — Criar e configurar o grupo no Telegram

1. Crie um novo grupo no Telegram (ex: "iPhone Radar 📡")
2. Adicione seu bot ao grupo
3. Envie qualquer mensagem no grupo
4. Acesse este link no navegador (substitua `SEU_TOKEN`):
   ```
   https://api.telegram.org/botSEU_TOKEN/getUpdates
   ```
5. Procure o campo `"chat": {"id": -100XXXXXXXXX}` — esse número negativo é o **Chat ID**.
   👉 **Guarde o Chat ID** (inclua o sinal de `-`).

### Passo 3 — Criar o repositório no GitHub

1. Acesse [github.com](https://github.com) e crie uma conta (se não tiver)
2. Clique em **"New repository"**
3. Nome: `iphone-radar`
4. Visibilidade: **Public** (gratuito e ilimitado no Actions)
5. Clique em **"Create repository"**

### Passo 4 — Subir os arquivos

Com o [GitHub Desktop](https://desktop.github.com/) ou Git:

```bash
git clone https://github.com/SEU_USUARIO/iphone-radar.git
# Copie todos os arquivos desta pasta para dentro de iphone-radar/
git add .
git commit -m "🚀 Setup inicial do iPhone Radar"
git push
```

### Passo 5 — Configurar os Secrets do GitHub

1. No repositório, clique em **Settings** → **Secrets and variables** → **Actions**
2. Clique em **"New repository secret"** e adicione:

   | Nome | Valor |
   |------|-------|
   | `TELEGRAM_BOT_TOKEN` | Token do BotFather (ex: `123456789:AAGxxx...`) |
   | `TELEGRAM_CHAT_ID` | ID do grupo (ex: `-1001234567890`) |

3. Clique em **Settings** → **Actions** → **General** → marque **"Allow all actions"** → Salve.

### ✅ Ativar e testar

1. Vá em **Actions** no seu repositório
2. Clique em **"iPhone Price Radar"**
3. Clique em **"Run workflow"** para um teste manual
4. Verifique se a mensagem chegou no seu grupo do Telegram!

O radar vai rodar automaticamente **a cada hora** a partir daí.

---

## 📁 Estrutura do projeto

```
iphone-radar/
├── .github/workflows/radar.yml   # Agendamento (GitHub Actions)
├── src/
│   ├── main.py                   # Orquestrador principal
│   ├── price_db.py               # Banco de dados de preços (JSON)
│   ├── analyzer.py               # Lógica de análise (mínimo, média, bug)
│   ├── notifier.py               # Envio de alertas pro Telegram
│   └── scrapers/
│       ├── mercadolivre.py       # API oficial MercadoLivre
│       ├── amazon.py             # Scraper Amazon BR
│       ├── magalu.py             # Scraper Magazine Luiza
│       └── kabum.py              # Scraper KaBuM!
├── data/
│   └── prices.json               # Histórico de preços (auto-atualizado)
└── requirements.txt
```

## 📊 Histórico de preços

O arquivo `data/prices.json` é atualizado automaticamente a cada hora e commitado no repositório. Com isso, você tem um histórico completo de todos os preços coletados, visível diretamente pelo GitHub.

---

## ❓ Dúvidas comuns

**O radar não está enviando alertas.**
→ Verifique se os Secrets estão corretos. Acesse `Actions` → último run → veja os logs.

**Aparece erro 403 em algumas lojas.**
→ Sites como Amazon têm anti-bot. O radar tenta mas não trava se falhar — o MercadoLivre (API oficial) sempre funciona.

**Posso adicionar mais modelos?**
→ Sim! Edite a lista `IPHONE_MODELS` em `src/scrapers/mercadolivre.py`.

**Quero mudar o horário de execução.**
→ Edite o `cron` em `.github/workflows/radar.yml`. Use [crontab.guru](https://crontab.guru) para gerar a expressão.
