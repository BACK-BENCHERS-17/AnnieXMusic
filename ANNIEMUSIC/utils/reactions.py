from pyrogram.types import Message

async def react_to_command(message: Message):
    try:
        await message.react(emoji="❤")
    except Exception:
        pass
