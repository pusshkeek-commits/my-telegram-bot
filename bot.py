import os, random, sqlite3, logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask
from threading import Thread

# --- CONFIGURATION (Render Environment Variables se aayega) ---
TOKEN = os.getenv("8765318231:AAEp_5sOvg_wc50sTh8NiOMdrT-393es3DQ")
ADMIN_ID = 1803236517
BACKUP_CH_ID = -1003714147743
BACKUP_LINK = "https://t.me/+1zGwJZU7Tgg3ZTE1"
GODOWN_CH_ID = -1003556779081

bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- DATABASE SETUP ---
db = sqlite3.connect("bot_data.db")
cur = db.cursor()
cur.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, pts INTEGER DEFAULT 20, referred_by INTEGER)")
cur.execute("CREATE TABLE IF NOT EXISTS videos (msg_id INTEGER PRIMARY KEY)")
db.commit()

# --- MIDDLEWARE: CHECK BACKUP JOIN ---
async def check_join(user_id):
    try:
        member = await bot.get_chat_member(BACKUP_CH_ID, user_id)
        return member.status in ["member", "administrator", "creator"]
    except: return False

# --- KEYBOARDS ---
main_kb = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="📺 Get Video"), KeyboardButton(text="💰 My Points")],
    [KeyboardButton(text="🎁 Daily Bonus"), KeyboardButton(text="🔗 Invite Friends")]
], resize_keyboard=True)

# --- USER HANDLERS ---
@dp.message(Command("start"))
async def start_cmd(msg: types.Message):
    user_id = msg.from_user.id
    args = msg.text.split()
    ref_id = args[1] if len(args) > 1 else None
    
    cur.execute("SELECT id FROM users WHERE id=?", (user_id,))
    if not cur.fetchone():
        # New User logic
        cur.execute("INSERT INTO users (id, pts, referred_by) VALUES (?, 20, ?)", (user_id, 20, ref_id))
        if ref_id and ref_id.isdigit() and int(ref_id) != user_id:
            cur.execute("UPDATE users SET pts = pts + 10 WHERE id=?", (int(ref_id),))
            try: await bot.send_message(ref_id, "🎊 Someone joined using your link! +10 Points added.")
            except: pass
        db.commit()

    if not await check_join(user_id):
        btn = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Join Backup Channel", url=BACKUP_LINK)]])
        await msg.answer("❌ Access Denied!\n\nYou must join our backup channel to use this bot.", reply_markup=btn)
        return
    await msg.answer("Welcome! You have 20 bonus points. Choose an option:", reply_markup=main_kb)

@dp.message(F.text == "📺 Get Video")
async def get_video(msg: types.Message):
    if not await check_join(msg.from_user.id):
        await msg.answer("Join the backup channel first!")
        return

    cur.execute("SELECT pts FROM users WHERE id=?", (msg.from_user.id,))
    pts = cur.fetchone()[0]
    
    if pts > 0:
        cur.execute("SELECT msg_id FROM videos ORDER BY RANDOM() LIMIT 1")
        res = cur.fetchone()
        if not res:
            await msg.answer("Godown is empty! Admin needs to /index first.")
            return

        try:
            # Copy message with protection (No Save/Forward)
            await bot.copy_message(chat_id=msg.from_user.id, from_chat_id=GODOWN_CH_ID, message_id=res[0], protect_content=True)
            cur.execute("UPDATE users SET pts = pts - 1 WHERE id=?", (msg.from_user.id,))
            db.commit()
        except: await msg.answer("Error fetching video. Please try again.")
    else:
        await msg.answer("Insufficient points! Invite friends to earn more.")

@dp.message(F.text == "💰 My Points")
async def my_pts(msg: types.Message):
    cur.execute("SELECT pts FROM users WHERE id=?", (msg.from_user.id,))
    await msg.answer(f"Your Balance: {cur.fetchone()[0]} Points")

@dp.message(F.text == "🎁 Daily Bonus")
async def daily_bonus(msg: types.Message):
    # Basic daily bonus logic (Add 10 pts)
    cur.execute("UPDATE users SET pts = pts + 10 WHERE id=?", (msg.from_user.id,))
    db.commit()
    await msg.answer("🎁 You claimed 10 Daily Points!")

@dp.message(F.text == "🔗 Invite Friends")
async def invite(msg: types.Message):
    bot_info = await bot.get_me()
    link = f"https://t.me/{bot_info.username}?start={msg.from_user.id}"
    await msg.answer(f"Share your link and get 10 points per referral!\n\n`{link}`", parse_mode="Markdown")

# --- ADMIN PANEL (Only for You) ---
@dp.message(Command("addpoints"))
async def admin_add_pts(msg: types.Message):
    if msg.from_user.id != ADMIN_ID: return
    try:
        _, target_id, amount = msg.text.split()
        cur.execute("UPDATE users SET pts = pts + ? WHERE id=?", (int(amount), int(target_id)))
        db.commit()
        await msg.answer(f"✅ Successfully added {amount} points to {target_id}")
    except: await msg.answer("Usage: /addpoints [UserID] [Amount]")

@dp.message(Command("broadcast"))
async def broadcast(msg: types.Message):
    if msg.from_user.id != ADMIN_ID: return
    if not msg.reply_to_message:
        await msg.answer("Reply to a message/photo/video with /broadcast to send it to everyone.")
        return
    
    cur.execute("SELECT id FROM users")
    users = cur.fetchall()
    count = 0
    for user in users:
        try:
            await bot.copy_message(chat_id=user[0], from_chat_id=msg.chat.id, message_id=msg.reply_to_message.message_id)
            count += 1
        except: pass
    await msg.answer(f"✅ Broadcast sent to {count} users.")

@dp.message(Command("index"))
async def silent_index(msg: types.Message):
    if msg.from_user.id != ADMIN_ID: return
    await msg.answer("Starting SILENT indexing (1 to 4000)... No spam this time.")
    ids = [(i,) for i in range(1, 4001)]
    cur.executemany("INSERT OR IGNORE INTO videos VALUES (?)", ids)
    db.commit()
    await msg.answer("✅ Indexing Complete! IDs added to database.")

# --- KEEP ALIVE ---
app = Flask('')
@app.route('/')
def home(): return "Bot is Online"
Thread(target=lambda: app.run(host='0.0.0.0', port=8080)).start()

if __name__ == "__main__":
    dp.run_polling(bot)
