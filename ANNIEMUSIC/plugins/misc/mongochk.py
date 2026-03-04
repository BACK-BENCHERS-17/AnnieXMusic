import re
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ParseMode
from pymongo import MongoClient

from ANNIEMUSIC import app

mongo_url_pattern = re.compile(r"mongodb(?:\+srv)?:\/\/[^\s]+")

@app.on_message(filters.command("mongochk"))
async def mongo_command(client: Client, message: Message):
    if len(message.command) < 2:
        return await message.reply_text(
            "❌ <b>Usage:</b> `/mongochk <your_mongodb_url>`",
            parse_mode=ParseMode.HTML
        )

    mongo_url = message.command[1]

    if not re.match(mongo_url_pattern, mongo_url):
        return await message.reply_text(
            "❌ <b>Invalid MongoDB URL format.</b>\nIt should start with `mongodb://` or `mongodb+srv://`.",
            parse_mode=ParseMode.HTML
        )

    try:
        mongo_client = MongoClient(mongo_url, serverSelectionTimeoutMS=5000)
        mongo_client.server_info()
        await message.reply_text(
            "✅ <b>MongoDB URL is valid and connection was successful.</b>",
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        await message.reply_text(
            f"❌ <b>Failed to connect to MongoDB:</b>\n`{str(e)}`",
            parse_mode=ParseMode.HTML
        )
