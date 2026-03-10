import os
import random
import sqlite3
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from flask import Flask
from threading import Thread

# --- KEEP ALIVE LOGIC (Render ko jagane ke liye) ---
app = Flask('')
@app.route('/')
def home(): return "I am alive!"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive():
    t = Thread(target=run)
    t.start()

# --- BOT SETTINGS ---
TOKEN = "TERA_BOT_TOKEN_YAHAN_DAAL"
GODOWN_ID = -100123456789  # Apne channel ki ID yahan daal
VIDEO_IDS = [10, 11, 12, 13] # Apne videos ke message IDs

bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- DATABASE ---
db = sqlite3.connect("users.db")
cur = db.cursor()
cur.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, pts INTEGER DEFAULT 10)")
db.commit()

@dp.message(Command("start"))
async def welcome(msg: types.Message):
    await msg.answer("Bhai welcome! 10 points free mile hain. /get likho video ke liye.")

@dp.message(Command("get"))
async def send_vid(msg: types.Message):
    uid = msg.from_user.id
    cur.execute("SELECT pts FROM users WHERE id=?", (uid,))
    res = cur.fetchone()
    pts = res[0] if res else 10 # Naye user ko 10 points

    if pts > 0:
        vid = random.choice(VIDEO_IDS)
        await bot.copy_message(chat_id=uid, from_chat_id=GODOWN_ID, message_id=vid)
        cur.execute("INSERT OR REPLACE INTO users VALUES (?, ?)", (uid, pts-1))
        db.commit()
        await msg.answer(f"Video bhej di! Points bache: {pts-1}")
    else:
        await msg.answer("Points khatam ho gaye bhai!")

if __name__ == "__main__":
    keep_alive()
    dp.run_polling(bot)
