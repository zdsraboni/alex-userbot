from telethon import TelegramClient, events
import asyncio
import nest_asyncio
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

# ---------------------------------------------------------
# কনফিগারেশন এবং ক্রেডেনশিয়ালস
# ---------------------------------------------------------
api_id = 38622204
api_hash = 'd1da3bccca8184f39121e020c9b9dd44'

# ফিচার ১: মিডিয়া ফরোয়ার্ড এবং ডিলিট কনফিগারেশন
SOURCE_GROUP_ID = -1003771970765  
TARGET_BOT_ID = 8386204935        

# ফিচার ২: লিংক ফরোয়ার্ড কনফিগারেশন
LINK_SOURCE_GROUP_ID = -1003300886475 
LINK_SENDER_BOT_ID = 8399054856       

# পরিবর্তনযোগ্য কমান্ড ভেরিয়েবল (ডিফল্ট: !fn)
current_reply_command = "!fn"

# ফিচার ৩: সেভড মেসেজ কনফিগারেশন (আগের টার্গেট গ্রুপ)
target_groups = [-1001166146545, -1002786332618, -1003031306912, -1002547413437, -1002573082359]

# ⚠️ গুরত্বপূর্ণ: আপনার ফাইলের নাম 'Colab_session.session' তাই এখানে শুধু 'Colab_session' দেওয়া হলো
client = TelegramClient('Colab_session', api_id, api_hash)

# ---------------------------------------------------------
# সার্ভার সেটআপ (Railway এর জন্য ডায়নামিক পোর্ট)
# ---------------------------------------------------------
class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'Bot is Running on Railway')

def run_server():
    # Railway অটোমেটিক PORT এনভায়রনমেন্ট ভেরিয়েবল সেট করে, না পেলে 8080 ব্যবহার করবে
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), SimpleHTTPRequestHandler)
    server.serve_forever()

# ---------------------------------------------------------
# ফিচার ১: কমান্ড চেঞ্জ সিস্টেম (.setcmd / .getcmd)
# ---------------------------------------------------------
@client.on(events.NewMessage(outgoing=True, pattern=r'\.setcmd (.*)'))
async def set_command(event):
    global current_reply_command
    new_cmd = event.pattern_match.group(1)
    current_reply_command = new_cmd
    await event.edit(f"✅ Auto-reply command updated to: `{current_reply_command}`")

@client.on(events.NewMessage(outgoing=True, pattern=r'\.getcmd'))
async def get_command(event):
    global current_reply_command
    await event.edit(f"ℹ️ Current Auto-reply command is: `{current_reply_command}`")

# ---------------------------------------------------------
# ফিচার ২: সেভড মেসেজ (টার্গেট গ্রুপ থেকে)
# ---------------------------------------------------------
@client.on(events.NewMessage(chats=target_groups))
async def save_restricted_content(event):
    if event.media:
        try:
            chat = await event.get_chat()
            path = await event.download_media()
            caption_text = f"Group: {chat.title}\n\n{event.text if event.text else ''}"
            await client.send_file('me', path, caption=caption_text)
            if path and os.path.exists(path):
                os.remove(path)
        except Exception as e:
            print(f"Error saving content: {e}")

# ---------------------------------------------------------
# ফিচার ৩: মিডিয়া ফরোয়ার্ড এবং ডিলিট
# ---------------------------------------------------------
@client.on(events.NewMessage(chats=SOURCE_GROUP_ID))
async def forward_and_delete(event):
    if event.sender_id == TARGET_BOT_ID:
        return
    if event.media:
        try:
            await client.send_file(TARGET_BOT_ID, event.media, caption=event.text)
            print(f"Media forwarded to Bot ({TARGET_BOT_ID})")
            await event.delete()
            print("Original message deleted from source group.")
        except Exception as e:
            print(f"Error: {e}")

# ---------------------------------------------------------
# ফিচার ৪: লিংক ফরোয়ার্ড
# ---------------------------------------------------------
@client.on(events.NewMessage(chats=LINK_SOURCE_GROUP_ID))
async def forward_bot_link(event):
    if event.sender_id == LINK_SENDER_BOT_ID:
        if event.text and ("http://" in event.text or "https://" in event.text):
            try:
                await client.send_message(TARGET_BOT_ID, event.text)
                print(f"Link forwarded to {TARGET_BOT_ID}")
            except Exception as e:
                print(f"Error forwarding link: {e}")

# ---------------------------------------------------------
# ফিচার ৫: অটো রিপ্লাই (ডিফল্ট: !fn)
# ---------------------------------------------------------
@client.on(events.NewMessage(from_users=TARGET_BOT_ID))
async def reply_fn_to_bot(event):
    global current_reply_command
    if event.is_private and event.media:
        try:
            await event.reply(current_reply_command)
            print(f"Replied '{current_reply_command}' to bot.")
        except Exception as e:
            print(f"Error replying: {e}")

# ---------------------------------------------------------
# মেইন ফাংশন রান করা
# ---------------------------------------------------------
async def main():
    # সেশন ফাইল থাকায় এখানে ফোন নাম্বার বা লগিন কোড চাইবে না
    await client.start()
    print("Userbot started on Railway...")
    await client.run_until_disconnected()

# সার্ভার ব্যাকগ্রাউন্ডে চালু করা
threading.Thread(target=run_server, daemon=True).start()

nest_asyncio.apply()
client.loop.run_until_complete(main())
