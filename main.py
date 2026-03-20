import os
import time
import asyncio
import random
import requests
from flask import Flask
from threading import Thread
from telethon import TelegramClient, events, Button
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.errors import FloodWaitError, SessionPasswordNeededError

# ================================================================
# --- CẤU HÌNH HỆ THỐNG (THAY ĐỔI TẠI ĐÂY) ---
# ================================================================
API_ID = 36437338 
API_HASH = '18d34c7efc396d277f3db62baa078efc'
BOT_TOKEN = '8499499024:AAFSifEjBAKL2BSmanDDlXuRGh93zvZjM78'
ADMIN_ID = 7816353760 

# Lưu ý quan trọng: Thay URL này bằng link App Render của bạn để chạy 24/7
RENDER_URL = "https://bot-clone-v89.onrender.com" 

SESSION_DIR = 'sessions'
GROUP_FILE = 'groups.txt'
MSG_FILE = 'ad_msg.txt'

# Tự động tạo file nếu chưa có
if not os.path.exists(SESSION_DIR): os.makedirs(SESSION_DIR)
if not os.path.exists(GROUP_FILE): open(GROUP_FILE, 'w').close()
if not os.path.exists(MSG_FILE): 
    with open(MSG_FILE, 'w', encoding='utf-8') as f: 
        f.write("Nhóm chéo chất lượng ae vào chéo đi : Tham gia ngay (Link nhóm)")

ICONS = ["🔥", "🚀", "💎", "🧧", "🍀", "✨", "🎯", "⚡", "🌈", "💰"]
KEYWORDS_REPLY = ["bot", "link", "chéo", "admin", "đâu", "nào", "sao", "giúp", "rep", "alo"]
is_spamming = False
last_messages = {} # Lưu ID tin nhắn cũ để xóa
clones = {} # Lưu các client đang hoạt động
replied_users_cooldown = {} # Chống spam loop với 1 user

# ================================================================
# --- HỆ THỐNG KEEP-ALIVE (GIÚP RENDER CHẠY 24/7) ---
# ================================================================
app = Flask('')

@app.route('/')
def home():
    return "🤖 Bot Clone V8.9 PRO is Online 24/7 (Status: Running)"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port, use_reloader=False)

def keep_alive_ping():
    """Tự gửi yêu cầu đến chính nó để Render không tắt server"""
    while True:
        try:
            if "onrender.com" in RENDER_URL:
                requests.get(RENDER_URL, timeout=10)
                print("📡 System: Ping sent to keep bot alive 24/7.")
        except Exception as e:
            print(f"📡 System: Ping error {e}")
        time.sleep(300) # Ping mỗi 5 phút

# ================================================================
# --- QUẢN LÝ DỮ LIỆU ---
# ================================================================
def get_ad_msg():
    with open(MSG_FILE, 'r', encoding='utf-8') as f: return f.read()

def load_groups():
    if not os.path.exists(GROUP_FILE): return []
    with open(GROUP_FILE, 'r') as f: return [line.strip() for line in f.readlines() if line.strip()]

def save_group(group):
    groups = load_groups()
    if group not in groups:
        with open(GROUP_FILE, 'a') as f: f.write(group + '\n')

def get_safe_text():
    """Tạo tin nhắn biến thiên để né bộ lọc Telegram"""
    inv = "".join(random.choices(['\u200b', '\u200c', '\u200d'], k=random.randint(4, 10)))
    return f"{random.choice(ICONS)} {get_ad_msg()} {random.choice(ICONS)}\n{inv}"

# ================================================================
# --- MASTER BOT (ADMIN INTERFACE) ---
# ================================================================
master_bot = TelegramClient('master_bot', API_ID, API_HASH)

@master_bot.on(events.NewMessage(pattern='/start'))
async def start_menu(event):
    if event.sender_id != ADMIN_ID: return
    text = (
        "🛡️ **HỆ THỐNG QUẢN LÝ CLONE V8.9 PRO (LIVE 24/7)**\n\n"
        "Chào Admin, dàn clone đã sẵn sàng. Hãy chọn lệnh bên dưới:"
    )
    buttons = [
        [Button.inline("➕ Thêm Acc", data="menu_add"), Button.inline("📊 Trạng Thái", data="menu_status")],
        [Button.inline("🚀 Chạy Spam", data="menu_spam"), Button.inline("🛑 Dừng Spam", data="menu_stop")],
        [Button.inline("🔄 Cho Acc Join Nhóm", data="menu_join")],
        [Button.inline("📝 Đổi Tin Nhắn", data="menu_setmsg"), Button.inline("📂 Xem Nhóm", data="menu_list")]
    ]
    await event.reply(text, buttons=buttons)

@master_bot.on(events.CallbackQuery)
async def callback_handler(event):
    global is_spamming
    if event.sender_id != ADMIN_ID: return
    data = event.data.decode('utf-8')

    if data == "menu_status":
        sessions = [f for f in os.listdir(SESSION_DIR) if f.endswith('.session')]
        groups = load_groups()
        st = "🟢 LIVE 24/7" if is_spamming else "🔴 Đang dừng"
        msg = f"📊 STATUS:\n- Trạng thái: {st}\n- Acc Clone: {len(sessions)}\n- Nhóm mục tiêu: {len(groups)}"
        await event.answer(msg, cache_time=0, alert=True)

    elif data == "menu_spam":
        if is_spamming: return await event.answer("⚠️ Bot đang chạy rồi!", alert=True)
        is_spamming = True
        asyncio.create_task(run_spam_loop())
        await event.edit("🚀 **Bắt đầu chiến dịch Spam & Rep (2 phút/vòng)!**", buttons=[Button.inline("🔙 Quay lại", data="menu_back")])

    elif data == "menu_stop":
        is_spamming = False
        await event.edit("🛑 **Đã dừng toàn bộ hoạt động.**", buttons=[Button.inline("🔙 Quay lại", data="menu_back")])

    elif data == "menu_add":
        await event.answer("Gõ lệnh /add để thêm tài khoản mới.", alert=True)

    elif data == "menu_setmsg":
        await event.answer("Gõ: /setmsg [nội dung] để đổi tin nhắn quảng cáo.", alert=True)

    elif data == "menu_list":
        gps = load_groups()
        msg = "📂 DANH SÁCH NHÓM:\n" + ("\n".join(gps) if gps else "Chưa có nhóm nào.")
        await event.answer(msg, cache_time=0, alert=True)

    elif data == "menu_join":
        await event.answer("Đang ra lệnh cho dàn clone join nhóm mục tiêu...", alert=False)
        asyncio.create_task(join_all_groups_logic(event))

    elif data == "menu_back":
        await start_menu(event)

# ================================================================
# --- LOGIC TÀI KHOẢN CLONE ---
# ================================================================
async def join_all_groups_logic(event):
    targets = load_groups()
    session_files = [f for f in os.listdir(SESSION_DIR) if f.endswith('.session')]
    if not targets or not session_files:
        await master_bot.send_message(ADMIN_ID, "❌ Thiếu dữ liệu nhóm hoặc tài khoản.")
        return
    
    await master_bot.send_message(ADMIN_ID, f"🔄 Đang bắt đầu cho {len(session_files)} acc join nhóm...")
    for s in session_files:
        c = TelegramClient(os.path.join(SESSION_DIR, s), API_ID, API_HASH)
        try:
            await c.connect()
            for t in targets:
                try:
                    await c(JoinChannelRequest(t))
                    await asyncio.sleep(2) # Giãn cách join tránh ban
                except: pass
            await c.disconnect()
        except: pass
    await master_bot.send_message(ADMIN_ID, "✅ Đã hoàn thành lệnh Join nhóm!")

@master_bot.on(events.NewMessage(pattern='/add'))
async def add_account(event):
    if event.sender_id != ADMIN_ID: return
    async with master_bot.conversation(event.chat_id) as conv:
        try:
            await conv.send_message("📞 **Số điện thoại (+84...):**")
            phone = (await conv.get_response()).text.strip()
            client = TelegramClient(os.path.join(SESSION_DIR, f"{phone}.session"), API_ID, API_HASH)
            await client.connect()
            if not await client.is_user_authorized():
                await client.send_code_request(phone)
                await conv.send_message("📩 **Nhập mã OTP:**")
                otp = (await conv.get_response()).text.strip()
                try:
                    await client.sign_in(phone, otp)
                except SessionPasswordNeededError:
                    await conv.send_message("🔒 **Nhập mật khẩu 2FA:**")
                    pwd = (await conv.get_response()).text.strip()
                    await client.sign_in(password=pwd)
            await conv.send_message(f"✅ Nạp thành công: `{phone}`")
            await client.disconnect()
        except Exception as e: await conv.send_message(f"❌ Lỗi: {str(e)}")

@master_bot.on(events.NewMessage(pattern='/setmsg'))
async def set_msg(event):
    if event.sender_id != ADMIN_ID: return
    try:
        new_msg = event.text.split(' ', 1)[1]
        with open(MSG_FILE, 'w', encoding='utf-8') as f: f.write(new_msg)
        await event.reply(f"✅ Đã cập nhật tin nhắn quảng cáo!")
    except: await event.reply("⚠️ HD: `/setmsg [Nội dung]`")

@master_bot.on(events.NewMessage(pattern='/addgroup'))
async def add_g(event):
    if event.sender_id != ADMIN_ID: return
    try:
        group = event.text.split(' ', 1)[1].strip().replace('@', '')
        save_group(group); await event.reply(f"✅ Đã thêm nhóm: {group}")
    except: await event.reply("⚠️ HD: `/addgroup [username]`")

# ================================================================
# --- LOGIC SPAM & AUTO-REPLY (TỐI ƯU TỐC ĐỘ) ---
# ================================================================
async def start_reply_handler(client):
    """Xử lý trả lời tin nhắn ngay lập tức"""
    @client.on(events.NewMessage(incoming=True))
    async def handler(event):
        if event.is_private or not is_spamming: return
        try:
            sender = await event.get_sender()
            # NÉ BOT VÀ CHÍNH MÌNH:
            if sender is None or getattr(sender, 'bot', False) or event.out: return
            
            # Cooldown 5s mỗi user để tránh spam loop
            user_id = event.sender_id
            if user_id in replied_users_cooldown:
                if time.time() - replied_users_cooldown[user_id] < 5: return

            text_lower = (event.text or "").lower()
            if any(word in text_lower for word in KEYWORDS_REPLY):
                replied_users_cooldown[user_id] = time.time()
                await asyncio.sleep(1) # Delay 1s trả lời cực nhanh
                try: await event.reply(f"🤖 {get_ad_msg()}")
                except: pass
        except: pass

async def run_spam_loop():
    """Vòng lặp spam mỗi 2 phút"""
    global is_spamming
    while is_spamming:
        targets = load_groups()
        sessions = [f for f in os.listdir(SESSION_DIR) if f.endswith('.session')]
        if not targets or not sessions: 
            is_spamming = False
            break
        
        for target in targets:
            if not is_spamming: break
            s_name = random.choice(sessions)
            if s_name not in clones:
                c = TelegramClient(os.path.join(SESSION_DIR, s_name), API_ID, API_HASH)
                try:
                    await c.connect()
                    if await c.is_user_authorized():
                        await start_reply_handler(c)
                        clones[s_name] = c
                    else: continue
                except: continue
            
            client = clones.get(s_name)
            if client:
                try:
                    m_key = (s_name, target)
                    # Xóa tin nhắn cũ trước khi gửi mới để sạch nhóm
                    if m_key in last_messages:
                        try: await client.delete_messages(target, [last_messages[m_key]])
                        except: pass
                    
                    sent = await client.send_message(target, get_safe_text())
                    last_messages[m_key] = sent.id
                except FloodWaitError as e: await asyncio.sleep(e.seconds)
                except: pass
            
            # Giãn cách 5s giữa các nhóm để tránh bị Telegram quét nhanh quá
            await asyncio.sleep(5)
        
        # Chờ đúng 2 phút (120 giây) trước khi bắt đầu vòng mới
        await asyncio.sleep(120)

# ================================================================
# --- KHỞI CHẠY ---
# ================================================================
async def main():
    await master_bot.start(bot_token=BOT_TOKEN)
    print("✅ Bot Master Online!")
    await master_bot.run_until_disconnected()

if __name__ == "__main__":
    # Khởi chạy các Thread bổ trợ
    Thread(target=run_web, daemon=True).start()
    Thread(target=keep_alive_ping, daemon=True).start()
    
    try:
        asyncio.run(main())
    except:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())
        
