import requests
import os
from pyrogram import Client, filters, enums
from pyrogram.types import Message
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from ANNIEMUSIC import app


def download_website(url):
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/58.0.3029.110 Safari/537.3"
        )
    }

    retries = Retry(total=5, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
    session = requests.Session()
    session.mount("http://", HTTPAdapter(max_retries=retries))
    session.mount("https://", HTTPAdapter(max_retries=retries))

    try:
        response = session.get(url, headers=headers)
        if response.status_code == 200:
            return response.text
        else:
            return f"❌ Failed to download source code. Status code: {response.status_code}"
    except Exception as e:
        return f"❌ An error occurred: {str(e)}"


@app.on_message(filters.command("webdl"))
async def web_download(client: Client, message: Message):
    if len(message.command) < 2:
        return await message.reply_text(
            "<blockquote><emoji id=\"5042334757040423886\">⚡️</emoji> <b>Web Downloader</b></blockquote>\n"
            "<blockquote><emoji id=\"5039598514980520994\">❤️‍🔥</emoji> Please enter a valid URL.\n"
            "<b>Example:</b> <code>/webdl https://example.com</code></blockquote>",
            parse_mode=enums.ParseMode.HTML
        )

    url = message.command[1]
    status_msg = await message.reply_text(
        "<blockquote><emoji id=\"5042334757040423886\">⚡️</emoji> Downloading website source...</blockquote>",
        parse_mode=enums.ParseMode.HTML
    )

    source_code = download_website(url)

    if source_code.startswith("❌"):
        return await status_msg.edit_text(
            f"<blockquote><emoji id=\"5042334757040423886\">⚡️</emoji> {source_code}</blockquote>",
            parse_mode=enums.ParseMode.HTML
        )

    file_path = "website_source.txt"
    try:
        with open(file_path, "w", encoding="utf-8") as file:
            file.write(source_code)

        await message.reply_document(
            document=file_path,
            caption=f"<blockquote><emoji id=\"5041975203853239332\">🎁</emoji> <b>Source code of:</b> <code>{url}</code></blockquote>",
            parse_mode=enums.ParseMode.HTML
        )
    except Exception as e:
        await message.reply_text(
            f"<blockquote><emoji id=\"5042334757040423886\">⚡️</emoji> <b>Failed to send the file:</b> <code>{e}</code></blockquote>",
            parse_mode=enums.ParseMode.HTML
        )
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

    await status_msg.delete()
