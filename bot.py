import os
import random
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask
from threading import Thread
import sqlite3 # Starting with SQLite for ease, can move to Postgres later

# --- CONFIGURATION ---
TOKEN = "8765318231:AAG6_xW4VA0u-xH7u4O3kgk2m4dbIO90LYo"
ADMIN_ID = 1803236517
BACKUP_CH_ID = -1003714147743
BACKUP_LINK = "https://t.me/+1zGwJZU7Tgg3ZTE1"
GODOWN_CH_ID = -1003556779081

bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- DATABASE SETUP ---
db = sqlite3.connect("bot_data.db")
cur = db.cursor()
cur.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, pts INTEGER DEFAULT 20, last_daily TEXT, referred_by INTEGER)")
cur.execute("CREATE TABLE IF NOT EXISTS videos (msg_id INTEGER PRIMARY KEY)")
db.commit()

# --- UTILS ---
async def is_subscribed(user_id):
    try:
        member = await bot.get_chat_member(BACKUP_CH_ID, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

# --- KEYBOARDS ---
main_kb = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="📺 Get Video"), KeyboardButton(text="💰 My Points")],
    [KeyboardButton(text="🎁 Daily Bonus"), KeyboardButton(text="🔗 Invite Friends")]
], resize_keyboard=True)

# --- HANDLERS ---
@dp.message(Command("start"))
async def start_cmd(msg: types.Message):
    user_id = msg.from_user.id
    ref_id = msg.text.split()[1] if len(msg.text.split()) > 1 else None
    
    cur.execute("SELECT id FROM users WHERE id=?", (user_id,))
    if not cur.fetchone():
        # New User Logic
        cur.execute("INSERT INTO users (id, pts, referred_by) VALUES (?, ?, ?)", (user_id, 20, ref_id))
        if ref_id and ref_id.isdigit():
            cur.execute("UPDATE users SET pts = pts + 10 WHERE id=?", (int(ref_id),))
            try: await bot.send_message(ref_id, "🎊 Someone joined using your link! +10 Points added.")
            except: pass
        db.commit()

    if not await is_subscribed(user_id):
        btn = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Join Backup Channel", url=BACKUP_LINK)]])
        await msg.answer("❌ Access Denied!\n\nYou must join our backup channel first to use this bot.", reply_markup=btn)
        return

    await msg.answer("Welcome! You've received 20 bonus points. Use the menu below.", reply_markup=main_kb)

@dp.message(F.text == "📺 Get Video")
async def get_video(msg: types.Message):
    if not await is_subscribed(msg.from_user.id):
        await msg.answer("Join the backup channel first!")
        return

    cur.execute("SELECT pts FROM users WHERE id=?", (msg.from_user.id,))
    pts = cur.fetchone()[0]
    
    if pts <= 0:
        await msg.answer("Insufficient points! Invite friends to earn more.")
        return

    cur.execute("SELECT msg_id FROM videos")
    all_vids = cur.fetchall()
    if not all_vids:
        await msg.answer("Godown is empty! Admin needs to /index first.")
        return

    vid_id = random.choice(all_vids)[0]
    try:
        # protect_content=True blocks saving/forwarding
        await bot.copy_message(chat_id=msg.from_user.id, from_chat_id=GODOWN_CH_ID, message_id=vid_id, protect_content=True)
        cur.execute("UPDATE users SET pts = pts - 1 WHERE id=?", (msg.from_user.id,))
        db.commit()
    except:
        await msg.answer("Error fetching video. Try again.")

@dp.message(F.text == "💰 My Points")
async def check_pts(msg: types.Message):
    cur.execute("SELECT pts FROM users WHERE id=?", (msg.from_user.id,))
    await msg.answer(f"Your Current Balance: {cur.fetchone()[0]} Points")

@dp.message(F.text == "🔗 Invite Friends")
async def invite(msg: types.Message):
    link = f"https://t.me/{(await bot.get_me()).username}?start={msg.from_user.id}"
    await msg.answer(f"Share this link with friends!\n\nYou get 10 points per referral.\n\n`{link}`", parse_mode="Markdown")

# --- ADMIN COMMANDS ---
@dp.message(Command("index"))
async def index_videos(msg: types.Message):
    if msg.from_user.id != ADMIN_ID: return
    await msg.answer("Indexing started... This might take time.")
    # This logic assumes you manually forward videos or bot scans history
    # For now, let's say it scans last 3000 messages
    count = 0
    for i in range(1, 5000): # Scanning message IDs
        try:
            # We check if a message exists in godown
            await bot.forward_message(chat_id=ADMIN_ID, from_chat_id=GODOWN_CH_ID, message_id=i)
            cur.execute("INSERT OR IGNORE INTO videos VALUES (?)", (i,))
            count += 1
        except: continue
    db.commit()
    await msg.answer(f"Indexing complete. {count} videos found.")

# --- WEB SERVER FOR RENDER ---
app = Flask('')
@app.route('/')
def home(): return "Bot is Running"
def run(): app.run(host='0.0.0.0', port=8080)
Thread(target=run).start()

if __name__ == "__main__":
    dp.run_polling(bot)
