# Profit AI — Render 24/7

## Deploy
1. Create a GitHub repository and upload this project.
2. Create a Render Web Service from the repository.
3. Render can use `render.yaml`, or set:
   Build: `pip install -r requirements.txt`
   Start: `python app/main.py`
4. Add environment variables:
   BOT_TOKEN = BotFather token
   WEBAPP_URL = your Render HTTPS URL
5. Deploy.

## Telegram
In @BotFather configure the bot's Menu Button / Web App using your Render HTTPS URL.
Then send `/start` to your bot.

## Important
Change `YOUR_BOT_USERNAME` in `app/web/app.js` to your bot username (without @).

This project uses points only. Real-money deposits, withdrawals, guaranteed returns, or investment claims require appropriate legal/compliance, payment, security and fraud controls.
