import os
import time
import asyncio
import random
from flask import Flask
from threading import Thread
from telethon import TelegramClient, events, Button
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.errors import FloodWaitError, SessionPasswordNeededError

# --- CẤU HÌNH ---
API_ID = 36437338 
API_HASH = '18d34c7efc396d277f3db62baa078efc'
BOT_TOKEN = '8499499024:AAFSifEjBAKL2BSmanDDlXuRGh93zvZjM78'
ADMIN_ID = 7816353760 

SESSION_DIR = 'sessions'
GROUP_FILE = 'groups.txt'
MSG_FILE = 'ad_msg.txt'

if not os.path.exists(SESSION_DIR): os.makedirs(SESSION_DIR)
if not os.path.exists(GROUP_FILE): open(GROUP_FILE, 'w').close()
if not os.path.exists(MSG_FILE): 
    with open(MSG_FILE, 'w', encoding='utf-8') as f: 
        f.write("Nhóm chéo chất lượng ae vào chéo đi : Tham gia ngay (Link nhóm)")

ICONS = ["🔥", "🚀", "💎", "🧧", "🍀", "✨", "🎯", "⚡", "🌈", "💰"]
KEYWORDS_REPLY = ["bot", "link", "chéo", "admin", "đâu"]
is_spamming = False
last_messages = {} 
clones = {} 

# --- WEB SERVER (RENDER) ---
app = Flask('')
@app.route('/')
def home(): return "🤖 Bot Clone V8.9 PRO is Active!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port, use_reloader=False)

# --- QUẢN LÝ DỮ LIỆU ---
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
    inv = "".join(random.choices(['\u200b', '\u200c', '\u200d'], k=random.randint(4, 10)))
    return f"{random.choice(ICONS)} {get_ad_msg()} {random.choice(ICONS)}\n{inv}"

# --- MASTER BOT ---
master_bot = TelegramClient('master_bot', API_ID, API_HASH)

# --- MENU CHÍNH ---
@master_bot.on(events.NewMessage(pattern='/start'))
async def start_menu(event):
    if event.sender_id != ADMIN_ID: return
    text = (
        "🛡️ **HỆ THỐNG QUẢN LÝ CLONE V8.9**\n\n"
        "Chào Admin, hãy sử dụng các nút bấm bên dưới để điều khiển:"
    )
    buttons = [
        [Button.inline("➕ Thêm Acc", data="menu_add"), Button.inline("📊 Trạng Thái", data="menu_status")],
        [Button.inline("🚀 Chạy Spam", data="menu_spam"), Button.inline("🛑 Dừng Spam", data="menu_stop")],
        [Button.inline("🔄 Cho Acc Join Nhóm", data="menu_join")],
        [Button.inline("📝 Đổi Tin Nhắn", data="menu_setmsg"), Button.inline("📂 Xem Nhóm", data="menu_list")]
    ]
    await event.reply(text, buttons=buttons)

# --- XỬ LÝ NÚT BẤM (CALLBACK) ---
@master_bot.on(events.CallbackQuery)
async def callback_handler(event):
    global is_spamming
    if event.sender_id != ADMIN_ID: return
    data = event.data.decode('utf-8')

    if data == "menu_status":
        sessions = [f for f in os.listdir(SESSION_DIR) if f.endswith('.session')]
        groups = load_groups()
        st = "🟢 Đang chạy" if is_spamming else "🔴 Đang dừng"
        msg = f"📊 STATUS:\n- Trạng thái: {st}\n- Acc Clone: {len(sessions)}\n- Nhóm mục tiêu: {len(groups)}"
        await event.answer(msg, cache_time=0, alert=True)

    elif data == "menu_spam":
        if is_spamming: return await event.answer("⚠️ Bot đang chạy rồi!", alert=True)
        is_spamming = True
        asyncio.create_task(run_spam_loop())
        await event.edit("🚀 **Hệ thống đã bắt đầu chiến dịch Spam!**", buttons=[Button.inline("🔙 Quay lại", data="menu_back")])

    elif data == "menu_stop":
        is_spamming = False
        await event.edit("🛑 **Đã dừng toàn bộ hoạt động.**", buttons=[Button.inline("🔙 Quay lại", data="menu_back")])

    elif data == "menu_add":
        await event.answer("Vui lòng gõ lệnh /add để bắt đầu nạp acc.", alert=True)

    elif data == "menu_setmsg":
        await event.answer("Vui lòng gõ: /setmsg [nội dung] để đổi tin nhắn.", alert=True)

    elif data == "menu_list":
        gps = load_groups()
        msg = "📂 DANH SÁCH NHÓM:\n" + ("\n".join(gps) if gps else "Chưa có nhóm nào.")
        await event.answer(msg, cache_time=0, alert=True)

    elif data == "menu_join":
        await event.answer("Đang ra lệnh cho dàn clone join nhóm...", alert=False)
        asyncio.create_task(join_all_groups_logic(event))

    elif data == "menu_back":
        await start_menu(event)

# --- LOGIC JOIN NHÓM CHO TOÀN BỘ ACC ---
async def join_all_groups_logic(event):
    targets = load_groups()
    session_files = [f for f in os.listdir(SESSION_DIR) if f.endswith('.session')]
    if not targets or not session_files:
        await master_bot.send_message(ADMIN_ID, "❌ Không có nhóm hoặc không có acc để join.")
        return
    
    await master_bot.send_message(ADMIN_ID, f"🔄 Đang cho {len(session_files)} acc join {len(targets)} nhóm...")
    for s in session_files:
        c = TelegramClient(os.path.join(SESSION_DIR, s), API_ID, API_HASH)
        try:
            await c.connect()
            for t in targets:
                try:
                    await c(JoinChannelRequest(t))
                    await asyncio.sleep(1) # Tránh lụt
                except: pass
            await c.disconnect()
        except: pass
    await master_bot.send_message(ADMIN_ID, "✅ Đã hoàn thành lệnh Join nhóm cho tất cả acc!")

# --- CÁC LỆNH ĐIỀU KHIỂN ---
@master_bot.on(events.NewMessage(pattern='/add'))
async def add_account(event):
    if event.sender_id != ADMIN_ID: return
    async with master_bot.conversation(event.chat_id) as conv:
        try:
            await conv.send_message("📞 **Nhập số điện thoại (+84...):**\n(Hoặc gõ /cancel để hủy)")
            phone_res = await conv.get_response()
            if phone_res.text == '/cancel': return await conv.send_message("❌ Đã hủy.")
            phone = phone_res.text.strip()
            
            client = TelegramClient(os.path.join(SESSION_DIR, f"{phone}.session"), API_ID, API_HASH)
            await client.connect()
            
            if not await client.is_user_authorized():
                await client.send_code_request(phone)
                await conv.send_message("📩 **Nhập OTP:**")
                otp_res = await conv.get_response()
                try:
                    await client.sign_in(phone, otp_res.text.strip())
                except SessionPasswordNeededError:
                    await conv.send_message("🔒 **Nhập 2FA:**")
                    pwd_res = await conv.get_response()
                    await client.sign_in(password=pwd_res.text.strip())
            
            await conv.send_message(f"✅ Đã nạp thành công: `{phone}`")
            await client.disconnect()
        except Exception as e: await conv.send_message(f"❌ Lỗi: {str(e)}")

@master_bot.on(events.NewMessage(pattern='/setmsg'))
async def set_msg(event):
    if event.sender_id != ADMIN_ID: return
    try:
        new_msg = event.text.split(' ', 1)[1]
        with open(MSG_FILE, 'w', encoding='utf-8') as f: f.write(new_msg)
        await event.reply(f"✅ Đã cập nhật tin nhắn quảng cáo mới!")
    except: await event.reply("⚠️ HD: `/setmsg [Nội dung]`")

@master_bot.on(events.NewMessage(pattern='/addgroup'))
async def add_g(event):
    if event.sender_id != ADMIN_ID: return
    try:
        group = event.text.split(' ', 1)[1].strip().replace('@', '')
        save_group(group); await event.reply(f"✅ Đã thêm nhóm: {group}")
    except: await event.reply("⚠️ HD: `/addgroup [username]`")

# --- LOGIC SPAM ---
# Thêm Dictionary lưu trữ thời gian trả lời để chống spam loop
replied_users_cooldown = {}

async def start_reply_handler(client):
    @client.on(events.NewMessage(incoming=True))
    async def handler(event):
        if event.is_private or not is_spamming: return
        
        # === BẮT ĐẦU PHẦN LOGIC THÊM MỚI (CHỐNG BAN & TRÁNH BOT KHÁC) ===
        try:
            sender = await event.get_sender()
            if sender is None: return
            
            # 1. Bỏ qua nếu người gửi là một bot chính thức
            if getattr(sender, 'bot', False): return
            
            # 2. Bỏ qua tin nhắn do chính dàn clone của mình gửi (tránh tự rep nhau)
            if event.out: return
            
            # 3. Kiểm tra Cooldown: Chỉ rep 1 người 1 lần mỗi 5 phút (300 giây)
            current_time = time.time()
            user_id = event.sender_id
            if user_id in replied_users_cooldown:
                if current_time - replied_users_cooldown[user_id] < 300:
                    return # Chưa đủ 5 phút, bỏ qua không rep
            
            # 4. Bỏ qua nếu tin nhắn của họ có chứa Link/URL (100% là bot spam khác)
            if event.message.entities:
                for entity in event.message.entities:
                    if type(entity).__name__ in ['MessageEntityUrl', 'MessageEntityTextUrl']:
                        return
            
            # 5. Bỏ qua nếu tin nhắn chứa t.me hoặc http (chống lọt lưới)
            text_lower = (event.text or "").lower()
            if "t.me" in text_lower or "http" in text_lower:
                return
        except Exception:
            pass # Bỏ qua lỗi nhẹ nếu không lấy được thông tin người gửi
        # === KẾT THÚC PHẦN LOGIC THÊM MỚI ===

        targets = load_groups()
        chat = await event.get_chat()
        username = getattr(chat, 'username', '')
        if username and any(username in g for g in targets):
            if any(word in (event.text or "").lower() for word in KEYWORDS_REPLY):
                
                # Cập nhật thời gian đã rep user này vào từ điển
                replied_users_cooldown[user_id] = time.time()
                
                await asyncio.sleep(random.randint(3, 8))
                try: await event.reply(f"🤖 {get_ad_msg()}")
                except: pass

async def run_spam_loop():
    global is_spamming
    while is_spamming:
        targets = load_groups()
        sessions = [f for f in os.listdir(SESSION_DIR) if f.endswith('.session')]
        if not targets or not sessions: break
        
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
                    if m_key in last_messages:
                        try: await client.delete_messages(target, [last_messages[m_key]])
                        except: pass
                    sent = await client.send_message(target, get_safe_text())
                    last_messages[m_key] = sent.id
                except FloodWaitError as e: await asyncio.sleep(e.seconds)
                except: pass
            await asyncio.sleep(random.randint(100, 180)) # Giãn cách để tránh ban
        await asyncio.sleep(300)

# --- KHỞI CHẠY ---
async def main():
    await master_bot.start(bot_token=BOT_TOKEN)
    print("✅ Bot Online!")
    await master_bot.run_until_disconnected()

if __name__ == "__main__":
    Thread(target=run_web, daemon=True).start()
    try:
        asyncio.run(main())
    except:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())
      
