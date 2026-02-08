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

# ------------------- কনফিগারেশন ভেরিয়েবল -------------------
SOURCE_GROUP_ID = -1003771970765  # মিডিয়া আসবে এবং ডিলিট হবে
TARGET_BOT_ID = 8386204935        # ফরোয়ার্ড হবে (এবং /zb কমান্ডের গন্তব্য)
LINK_SOURCE_GROUP_ID = -1003300886475 
LINK_SENDER_BOT_ID = 8399054856       

# টার্গেট গ্রুপ লিস্ট (অটো সেভ এর জন্য)
target_groups = [-1001166146545, -1002786332618, -1003031306912, -1002547413437, -1002573082359]

# অটো টপিক ম্যাপিং (অটো সেভ এর জন্য)
TOPIC_MAPPING = {
    -1002786332618: {'dest': 'zdcall', 'topic': 4808},
    -1002547413437: {'dest': 'zdcall', 'topic': 4810}
}

# অটো রিপ্লাই কমান্ড ভেরিয়েবল (ডিফল্ট: !fn)
current_reply_command = "!fn"

client = TelegramClient(session_name, api_id, api_hash)

# ---------------------------------------------------------
# সার্ভার সেটআপ (Railway Keep Alive)
# ---------------------------------------------------------
class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'Bot is Running with Custom Caption Feature')

def run_server():
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
# ফিচার ২ (আপডেটেড): ম্যানুয়াল মুভ + কাস্টম ক্যাপশন
# ---------------------------------------------------------
# প্যাটার্ন ব্যাখ্যা:
# ^/ -> স্ল্যাশ দিয়ে শুরু
# (cl|bw|zb) -> গ্রুপ ১: কমান্ড
# (?:\s+(.+))?$ -> গ্রুপ ২ (অপশনাল): স্পেস এর পর যা লেখা থাকবে তাই ক্যাপশন
@client.on(events.NewMessage(outgoing=True, pattern=r'^/(cl|bw|zb)(?:\s+(.+))?$'))
async def manual_move_message(event):
    # কমান্ড ডিটেক্ট করা
    cmd = event.pattern_match.group(1)
    # কাস্টম ক্যাপশন ডিটেক্ট করা (যদি থাকে)
    custom_caption = event.pattern_match.group(2)
    
    # রিপ্লাই করা মেসেজটি ধরা
    reply_msg = await event.get_reply_message()
    
    if not reply_msg:
        await event.edit("❌ Please reply to a message.")
        return

    try:
        destination = None
        topic_id = None

        # গন্তব্য ঠিক করা
        if cmd == 'zb':
            destination = TARGET_BOT_ID
            topic_id = None 
        elif cmd == 'cl':
            destination = 'zdcall'
            topic_id = 4808
        elif cmd == 'bw':
            destination = 'zdcall'
            topic_id = 4810
        
        # ক্যাপশন নির্ধারণ করা: কাস্টম ক্যাপশন থাকলে সেটা, না হলে অরিজিনালটা
        final_caption = custom_caption if custom_caption else reply_msg.text

        # ১. মেসেজটি নির্দিষ্ট গন্তব্যে পাঠানো
        if reply_msg.media:
            await client.send_file(destination, reply_msg.media, caption=final_caption, reply_to=topic_id)
        else:
            # যদি মিডিয়া না থাকে শুধু টেক্সট হয়
            text_to_send = custom_caption if custom_caption else reply_msg.text
            await client.send_message(destination, text_to_send, reply_to=topic_id)
        
        # ২. অরিজিনাল মেসেজটি ডিলিট করা
        await reply_msg.delete()
        
        # ৩. আপনার কমান্ড মেসেজটিও ডিলিট করা
        await event.delete()
        
        print(f"Moved via /{cmd} to {destination} with caption: {final_caption}")

    except Exception as e:
        print(f"Error in manual move: {e}")
        await event.edit(f"❌ Error: {e}")

# ---------------------------------------------------------
# ফিচার ৩: সেভড মেসেজ + অটো টপিক রাউটিং
# ---------------------------------------------------------
@client.on(events.NewMessage(chats=target_groups))
async def save_or_route_content(event):
    if event.media:
        try:
            chat = await event.get_chat()
            chat_id = event.chat_id
            
            path = await event.download_media()
            caption_text = f"Source: {chat.title}\n\n{event.text if event.text else ''}"

            if chat_id in TOPIC_MAPPING:
                dest_info = TOPIC_MAPPING[chat_id]
                destination = dest_info['dest']
                topic_id = dest_info['topic']
                
                await client.send_file(destination, path, caption=caption_text, reply_to=topic_id)
                print(f"Routed media from {chat_id} to {destination}/{topic_id}")
            else:
                await client.send_file('me', path, caption=caption_text)
                print(f"Saved media from {chat.title} to Saved Messages")

            if path and os.path.exists(path):
                os.remove(path)

        except Exception as e:
            print(f"Error in save/route: {e}")

# ---------------------------------------------------------
# ফিচার ৪: মিডিয়া ফরোয়ার্ড এবং ডিলিট (বট ফরোয়ার্ডিং)
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
# ফিচার ৫: লিংক ফরোয়ার্ড
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
# ফিচার ৬: অটো রিপ্লাই (Bot Reply)
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
    print("Userbot started with Custom Caption Feature...")
    await client.run_until_disconnected()

threading.Thread(target=run_server, daemon=True).start()

nest_asyncio.apply()
client.loop.run_until_complete(main())
