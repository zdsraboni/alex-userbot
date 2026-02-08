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
SOURCE_GROUP_ID = -1003771970765  # যে গ্রুপ থেকে মিডিয়া আসবে এবং ডিলিট হবে
TARGET_BOT_ID = 8386204935        # যে বটে ফরোয়ার্ড হবে এবং রিপ্লাই দেওয়া হবে

# ফিচার ২ (নতুন): লিংক ফরোয়ার্ড কনফিগারেশন
LINK_SOURCE_GROUP_ID = -1003300886475 # যে গ্রুপে লিংক আসবে
LINK_SENDER_BOT_ID = 8399054856       # যে বট লিংক পাঠাবে

# পরিবর্তনযোগ্য কমান্ড ভেরিয়েবল (ডিফল্ট: !fn)
current_reply_command = "!fn"

# ফিচার ৩: সেভড মেসেজ কনফিগারেশন (আগের টার্গেট গ্রুপ)
target_groups = [-1001166146545, -1002786332618, -1003031306912, -1002547413437, -1002573082359]

client = TelegramClient('colab_session', api_id, api_hash)

# ---------------------------------------------------------
# সার্ভার সেটআপ (Keep Alive)
# ---------------------------------------------------------
class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'Bot is Running 24/7')

def run_server():
    server = HTTPServer(('0.0.0.0', 7860), SimpleHTTPRequestHandler)
    server.serve_forever()

# ---------------------------------------------------------
# ফিচার ১: টেলিগ্রাম থেকেই কমান্ড চেঞ্জ করার সিস্টেম
# ---------------------------------------------------------
# কমান্ড সেট করতে: .setcmd <নতুন কমান্ড> (যেমন: .setcmd !gf)
@client.on(events.NewMessage(outgoing=True, pattern=r'\.setcmd (.*)'))
async def set_command(event):
    global current_reply_command
    new_cmd = event.pattern_match.group(1)
    current_reply_command = new_cmd
    await event.edit(f"✅ Auto-reply command updated to: `{current_reply_command}`")

# বর্তমান কমান্ড দেখতে: .getcmd
@client.on(events.NewMessage(outgoing=True, pattern=r'\.getcmd'))
async def get_command(event):
    global current_reply_command
    await event.edit(f"ℹ️ Current Auto-reply command is: `{current_reply_command}`")

# ---------------------------------------------------------
# ফিচার ২: টার্গেট গ্রুপ থেকে সেভড মেসেজে সেভ করা (রেস্ট্রিকটেড কন্টেন্ট)
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
# ফিচার ৩: গ্রুপ থেকে মিডিয়া বটের কাছে পাঠানো এবং গ্রুপ থেকে ডিলিট করা
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
            print(f"Error in forwarding/deleting: {e}")

# ---------------------------------------------------------
# ফিচার ৪ (নতুন): নির্দিষ্ট গ্রুপে নির্দিষ্ট বট লিংক দিলে তা টার্গেট বটে ফরোয়ার্ড করা
# ---------------------------------------------------------
@client.on(events.NewMessage(chats=LINK_SOURCE_GROUP_ID))
async def forward_bot_link(event):
    # ১. চেক করা মেসেজটি কি কাঙ্ক্ষিত বট (8399054856) পাঠিয়েছে?
    if event.sender_id == LINK_SENDER_BOT_ID:
        # ২. চেক করা মেসেজে টেক্সট আছে কিনা এবং তাতে লিংক আছে কিনা
        if event.text and ("http://" in event.text or "https://" in event.text):
            try:
                # লিংকসহ মেসেজটি টার্গেট বটে (8386204935) পাঠিয়ে দেওয়া
                await client.send_message(TARGET_BOT_ID, event.text)
                print(f"Link detected from Bot {LINK_SENDER_BOT_ID}, Forwarded to {TARGET_BOT_ID}")
            except Exception as e:
                print(f"Error forwarding link: {e}")

# ---------------------------------------------------------
# ফিচার ৫: টার্গেট বট যখন মিডিয়া রিপ্লাই দিবে, তখন সেট করা কমান্ড রিপ্লাই দেওয়া
# ---------------------------------------------------------
@client.on(events.NewMessage(from_users=TARGET_BOT_ID))
async def reply_fn_to_bot(event):
    global current_reply_command
    if event.is_private and event.media:
        try:
            # এখানে ভেরিয়েবল ব্যবহার করা হচ্ছে
            await event.reply(current_reply_command)
            print(f"Replied '{current_reply_command}' to media from bot.")
        except Exception as e:
            print(f"Error replying to bot: {e}")

# ---------------------------------------------------------
# মেইন ফাংশন রান করা
# ---------------------------------------------------------
async def main():
    await client.start()
    print("Userbot started with Link Forwarding + All Features...")
    await client.run_until_disconnected()

# সার্ভার ব্যাকগ্রাউন্ডে চালু করা
threading.Thread(target=run_server, daemon=True).start()

nest_asyncio.apply()
client.loop.run_until_complete(main())
