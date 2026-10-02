import os, hmac, hashlib, sqlite3, time, urllib.parse, json, threading
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler

BASE = Path(__file__).resolve().parent.parent
load_dotenv(BASE / ".env")

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
WEBAPP_URL = os.getenv("WEBAPP_URL", "").rstrip("/")
DB = BASE / "profit_ai.db"

app = FastAPI(title="Profit AI")

def connect():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c

def init_db():
    c = connect()
    c.execute("""CREATE TABLE IF NOT EXISTS users(
        telegram_id INTEGER PRIMARY KEY,
        username TEXT DEFAULT '',
        first_name TEXT DEFAULT '',
        balance INTEGER NOT NULL DEFAULT 0,
        referred_by INTEGER,
        created_at INTEGER NOT NULL,
        last_daily INTEGER NOT NULL DEFAULT 0
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS referrals(
        invited_id INTEGER PRIMARY KEY,
        inviter_id INTEGER NOT NULL,
        created_at INTEGER NOT NULL
    )""")
    c.commit()
    c.close()

init_db()

def validate(init_data):
    if not BOT_TOKEN or not init_data:
        raise HTTPException(401, "Telegram authentication is not configured")

    data = dict(urllib.parse.parse_qsl(init_data, keep_blank_values=True))
    received = data.pop("hash", None)
    if not received:
        raise HTTPException(401, "Missing Telegram hash")

    try:
        auth_date = int(data.get("auth_date", "0"))
    except ValueError:
        raise HTTPException(401, "Invalid auth_date")

    if time.time() - auth_date > 86400:
        raise HTTPException(401, "Telegram authentication expired")

    check = "\n".join(f"{k}={data[k]}" for k in sorted(data))
    secret = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
    expected = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(expected, received):
        raise HTTPException(401, "Invalid Telegram signature")

    user = json.loads(data.get("user", "{}"))
    if not user.get("id"):
        raise HTTPException(401, "Telegram user not found")
    return data, user

class AuthBody(BaseModel):
    init_data: str

@app.post("/api/me")
def me(body: AuthBody):
    data, user = validate(body.init_data)
    uid = int(user["id"])
    now = int(time.time())
    start = data.get("start_param", "")

    c = connect()
    row = c.execute("SELECT * FROM users WHERE telegram_id=?", (uid,)).fetchone()

    if not row:
        inviter = None
        if start.isdigit() and int(start) != uid:
            exists = c.execute("SELECT telegram_id FROM users WHERE telegram_id=?", (int(start),)).fetchone()
            if exists:
                inviter = int(start)

        c.execute("""INSERT INTO users
            (telegram_id,username,first_name,referred_by,created_at)
            VALUES(?,?,?,?,?)""",
            (uid, user.get("username",""), user.get("first_name",""), inviter, now))

        if inviter:
            c.execute("INSERT OR IGNORE INTO referrals(invited_id,inviter_id,created_at) VALUES(?,?,?)",
                      (uid, inviter, now))
            c.execute("UPDATE users SET balance=balance+500 WHERE telegram_id=?", (inviter,))
        c.commit()

    row = c.execute("SELECT * FROM users WHERE telegram_id=?", (uid,)).fetchone()
    refs = c.execute("SELECT COUNT(*) n FROM referrals WHERE inviter_id=?", (uid,)).fetchone()["n"]
    c.close()

    return {"id": row["telegram_id"], "first_name": row["first_name"],
            "username": row["username"], "balance": row["balance"], "referrals": refs}

@app.post("/api/daily")
def daily(body: AuthBody):
    _, user = validate(body.init_data)
    uid = int(user["id"])
    now = int(time.time())
    c = connect()
    row = c.execute("SELECT last_daily FROM users WHERE telegram_id=?", (uid,)).fetchone()
    if not row:
        c.close()
        raise HTTPException(404, "User not registered")
    if now - row["last_daily"] < 86400:
        left = 86400 - (now-row["last_daily"])
        c.close()
        raise HTTPException(400, f"Already claimed. Try again in {left//3600}h {(left%3600)//60}m")
    c.execute("UPDATE users SET balance=balance+100,last_daily=? WHERE telegram_id=?", (now,uid))
    c.commit()
    balance = c.execute("SELECT balance FROM users WHERE telegram_id=?", (uid,)).fetchone()["balance"]
    c.close()
    return {"balance": balance, "amount": 100}

@app.get("/api/leaderboard")
def leaderboard():
    c = connect()
    rows = c.execute("SELECT first_name,username,balance FROM users ORDER BY balance DESC LIMIT 20").fetchall()
    c.close()
    return [dict(r) for r in rows]

async def start(update: Update, context):
    if not WEBAPP_URL:
        await update.message.reply_text("WEBAPP_URL is not configured on the server.")
        return
    keyboard = [[InlineKeyboardButton("🚀 Open Profit AI", web_app=WebAppInfo(url=WEBAPP_URL))]]
    await update.message.reply_text(
        "🤖 Welcome to Profit AI!\n\n🎁 Daily Bonus: 100 points\n👥 Referral: 500 points\n🏆 Leaderboard",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

def run_bot():
    if not BOT_TOKEN:
        print("BOT_TOKEN is missing; bot disabled.")
        return
    import asyncio
    async def runner():
        bot_app = Application.builder().token(BOT_TOKEN).build()
        bot_app.add_handler(CommandHandler("start", start))
        await bot_app.initialize()
        await bot_app.start()
        await bot_app.updater.start_polling()
        print("Telegram bot started.")
        await asyncio.Event().wait()
    asyncio.run(runner())

@app.get("/health")
def health():
    return {"status":"ok","service":"Profit AI"}

app.mount("/", StaticFiles(directory=BASE / "web", html=True), name="web")

if __name__ == "__main__":
    import uvicorn
    threading.Thread(target=run_bot, daemon=True).start()
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
