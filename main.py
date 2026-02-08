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

# সেশন নাম (আপনার ফাইল অনুযায়ী)
session_name = 'Colab_session'

# ------------------- ফিচার ১ কনফিগারেশন (মিডিয়া ফরোয়ার্ড ও ডিলিট) -------------------
SOURCE_GROUP_ID = -1003771970765  # যে গ্রুপ থেকে মিডিয়া আসবে এবং ডিলিট হবে
TARGET_BOT_ID = 8386204935        # যে বটে ফরোয়ার্ড হবে

# ------------------- ফিচার ২ কনফিগারেশন (লিংক ফরোয়ার্ড) -------------------
LINK_SOURCE_GROUP_ID = -1003300886475 
LINK_SENDER_BOT_ID = 8399054856       

# ------------------- ফিচার ৩ কনফিগারেশন (সেভ ও টপিক রাউটিং) -------------------
# সব টার্গেট গ্রুপের লিস্ট
target_groups = [-1001166146545, -1002786332618, -1003031306912, -1002547413437, -1002573082359]

# স্পেশাল টপিক ম্যাপিং (কোন গ্রুপ থেকে কোথায় যাবে)
# ফরম্যাট: গ্রুপ_আইডি : { 'entity': 'ইউজারনেম_বা_আইডি', 'topic': টপিক_আইডি }
TOPIC_MAPPING = {
    -1002786332618: {'dest': 'zdcall', 'topic': 4808},
    -1002547413437: {'dest': 'zdcall', 'topic': 4810}
}

# অটো রিপ্লাই কমান্ড ভেরিয়েবল (ডিফল্ট)
current_reply_command = "!fn"

client = TelegramClient(session_name, api_id, api_hash)

# ---------------------------------------------------------
# সার্ভার সেটআপ (Railway Keep Alive)
# ---------------------------------------------------------
class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'Bot is Running on Railway with Topic Routing')

def run_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), SimpleHTTPRequestHandler)
    server.serve_forever()

# ---------------------------------------------------------
# ফিচার: কমান্ড চেঞ্জ সিস্টেম (.setcmd / .getcmd)
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
# ফিচার: সেভড মেসেজ + টপিক রাউটিং (আপনার নতুন রিকোয়ারমেন্ট)
# ---------------------------------------------------------
@client.on(events.NewMessage(chats=target_groups))
async def save_or_route_content(event):
    if event.media:
        try:
            chat = await event.get_chat()
            chat_id = event.chat_id
            
            # মিডিয়া ডাউনলোড করা
            path = await event.download_media()
            caption_text = f"Source: {chat.title}\n\n{event.text if event.text else ''}"

            # লজিক চেক: এটি কি স্পেশাল গ্রুপ?
            if chat_id in TOPIC_MAPPING:
                # যদি স্পেশাল গ্রুপ হয়, তবে নির্দিষ্ট টপিকে পাঠানো হবে
                dest_info = TOPIC_MAPPING[chat_id]
                destination = dest_info['dest'] # 'zdcall'
                topic_id = dest_info['topic']   # 4808 or 4810
                
                await client.send_file(destination, path, caption=caption_text, reply_to=topic_id)
                print(f"Routed media from {chat_id} to {destination}/{topic_id}")
            else:
                # অন্য সব গ্রুপ হলে Saved Messages-এ যাবে
                await client.send_file('me', path, caption=caption_text)
                print(f"Saved media from {chat.title} to Saved Messages")

            # ফাইল ডিলিট করা (স্টোরেজ সেভ করতে)
            if path and os.path.exists(path):
                os.remove(path)

        except Exception as e:
            print(f"Error in save/route: {e}")

# ---------------------------------------------------------
# ফিচার: মিডিয়া ফরোয়ার্ড এবং ডিলিট (বট ফরোয়ার্ডিং)
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
# ফিচার: লিংক ফরোয়ার্ড
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
# ফিচার: অটো রিপ্লাই (Bot Reply)
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
# মেইন ফাংশন
# ---------------------------------------------------------
async def main():
    await client.start()
    print("Userbot started with Topic Routing feature...")
    await client.run_until_disconnected()

# সার্ভার ব্যাকগ্রাউন্ডে চালু করা
threading.Thread(target=run_server, daemon=True).start()

nest_asyncio.apply()
client.loop.run_until_complete(main())
