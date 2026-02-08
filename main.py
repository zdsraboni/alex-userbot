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

# সেশন নাম
session_name = 'Colab_session'

# ------------------- কনফিগারেশন ভেরিয়েবল -------------------
SOURCE_GROUP_ID = -1003771970765  
TARGET_BOT_ID = 8386204935        
LINK_SOURCE_GROUP_ID = -1003300886475 
LINK_SENDER_BOT_ID = 8399054856       

# টার্গেট গ্রুপ লিস্ট (অটো সেভ এর জন্য)
target_groups = [-1001166146545, -1002786332618, -1003031306912, -1002547413437, -1002573082359]

# অটো টপিক ম্যাপিং
TOPIC_MAPPING = {
    -1002786332618: {'dest': 'zdcall', 'topic': 4808},
    -1002547413437: {'dest': 'zdcall', 'topic': 4810}
}

# ব্যাচ মুভ এর গন্তব্য কনফিগারেশন (/20 কমান্ডের জন্য)
BATCH_MOVE_DEST = 'zdcall'
BATCH_MOVE_TOPIC = 4808

# অটো রিপ্লাই কমান্ড ভেরিয়েবল
current_reply_command = "!fn"

client = TelegramClient(session_name, api_id, api_hash)

# ---------------------------------------------------------
# সার্ভার সেটআপ
# ---------------------------------------------------------
class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'Bot is Running with Batch Move (/20) Feature')

def run_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), SimpleHTTPRequestHandler)
    server.serve_forever()

# ---------------------------------------------------------
# ফিচার ১: কমান্ড চেঞ্জ সিস্টেম
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
# ফিচার ২: ব্যাচ মুভ (Batch Move) - যেমন /20, /10 ইত্যাদি
# ---------------------------------------------------------
@client.on(events.NewMessage(outgoing=True, pattern=r'^/(\d+)$'))
async def batch_move_messages(event):
    try:
        # কতগুলো মেসেজ মুভ করতে হবে তা বের করা
        limit_count = int(event.pattern_match.group(1))
        
        status_msg = await event.edit(f"🔄 Processing last {limit_count} messages...")
        
        # মেসেজগুলো কালেক্ট করা
        messages_to_move = []
        ids_to_delete = [event.id] # কমান্ড মেসেজটিও ডিলিট হবে

        # max_id ব্যবহার করা হচ্ছে যাতে কমান্ড মেসেজ বাদে আগের গুলো নেওয়া হয়
        async for msg in client.iter_messages(event.chat_id, limit=limit_count, max_id=event.id):
            messages_to_move.append(msg)

        if not messages_to_move:
            await event.edit("❌ No messages found to move.")
            return

        # রিভার্স করা যাতে পুরাতন মেসেজ আগে সেন্ড হয় (সিকোয়েন্স ঠিক রাখতে)
        for msg in reversed(messages_to_move):
            try:
                # 4808 টপিকে পাঠানো
                await client.send_message(BATCH_MOVE_DEST, msg, reply_to=BATCH_MOVE_TOPIC)
                
                # সফল হলে ডিলিট লিস্টে যোগ করা
                ids_to_delete.append(msg.id)
                
                # ফ্লাড ওয়েট (FloodWait) এড়াতে ছোট বিরতি
                await asyncio.sleep(0.8) 
            except Exception as e:
                print(f"Failed to move msg {msg.id}: {e}")

        # সোর্স (Saved Messages) থেকে ডিলিট করা
        await client.delete_messages(event.chat_id, ids_to_delete)
        print(f"Successfully moved and deleted {len(messages_to_move)} messages.")

    except Exception as e:
        print(f"Error in batch move: {e}")
        await event.edit(f"❌ Error: {e}")

# ---------------------------------------------------------
# ফিচার ৩: ম্যানুয়াল মুভ + কাস্টম ক্যাপশন (/cl, /bw, /zb, /mm)
# ---------------------------------------------------------
@client.on(events.NewMessage(outgoing=True, pattern=r'^/(cl|bw|zb|mm)(?:\s+(.+))?$'))
async def manual_move_message(event):
    cmd = event.pattern_match.group(1)
    custom_caption = event.pattern_match.group(2)
    reply_msg = await event.get_reply_message()
    
    if not reply_msg:
        await event.edit("❌ Please reply to a message.")
        return

    try:
        targets = []
        if cmd == 'zb':
            targets.append({'dest': TARGET_BOT_ID, 'topic': None})
        elif cmd == 'cl':
            targets.append({'dest': 'zdcall', 'topic': 4808})
        elif cmd == 'bw':
            targets.append({'dest': 'zdcall', 'topic': 4810})
        elif cmd == 'mm':
            targets.append({'dest': TARGET_BOT_ID, 'topic': None})
            targets.append({'dest': 'zdcall', 'topic': 4808})

        final_caption = custom_caption if custom_caption else reply_msg.text

        for target in targets:
            dest = target['dest']
            topic = target['topic']
            if reply_msg.media:
                await client.send_file(dest, reply_msg.media, caption=final_caption, reply_to=topic)
            else:
                text_to_send = final_caption if final_caption else reply_msg.text
                await client.send_message(dest, text_to_send, reply_to=topic)
        
        await reply_msg.delete()
        await event.delete()

    except Exception as e:
        await event.edit(f"❌ Error: {e}")

# ---------------------------------------------------------
# ফিচার ৪: সেভড মেসেজ + অটো টপিক রাউটিং
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
                await client.send_file(dest_info['dest'], path, caption=caption_text, reply_to=dest_info['topic'])
            else:
                await client.send_file('me', path, caption=caption_text)

            if path and os.path.exists(path):
                os.remove(path)
        except Exception as e:
            print(f"Error: {e}")

# ---------------------------------------------------------
# ফিচার ৫: অটো ফরোয়ার্ড, ডিলিট, লিংক এবং রিপ্লাই
# ---------------------------------------------------------
@client.on(events.NewMessage(chats=SOURCE_GROUP_ID))
async def forward_and_delete(event):
    if event.sender_id == TARGET_BOT_ID: return
    if event.media:
        try:
            await client.send_file(TARGET_BOT_ID, event.media, caption=event.text)
            await event.delete()
        except Exception as e: print(e)

@client.on(events.NewMessage(chats=LINK_SOURCE_GROUP_ID))
async def forward_bot_link(event):
    if event.sender_id == LINK_SENDER_BOT_ID:
        if event.text and ("http" in event.text):
            try:
                await client.send_message(TARGET_BOT_ID, event.text)
            except Exception as e: print(e)

@client.on(events.NewMessage(from_users=TARGET_BOT_ID))
async def reply_fn_to_bot(event):
    if event.is_private and event.media:
        try:
            await event.reply(current_reply_command)
        except Exception as e: print(e)

# ---------------------------------------------------------
# মেইন রান
# ---------------------------------------------------------
async def main():
    await client.start()
    print("Userbot started with Batch Move (/20) Feature...")
    await client.run_until_disconnected()

threading.Thread(target=run_server, daemon=True).start()
nest_asyncio.apply()
client.loop.run_until_complete(main())
