from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.types import Message
import httpx
from ANNIEMUSIC import app
from config import OWNER_ID


def chunk_string(text, chunk_size):
    return [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]


@app.on_message(filters.command("allrepo") & filters.user(OWNER_ID))
async def all_repo_command(client: Client, message: Message):
    if len(message.command) < 2:
        return await message.reply_text(
            "<blockquote><emoji id=\"5042334757040423886\">⚡️</emoji> <b>GitHub Repos</b></blockquote>\n"
            "<blockquote><emoji id=\"5039598514980520994\">❤️‍🔥</emoji> Please enter a GitHub username.\n"
            "<b>Example:</b> <code>/allrepo CertifiedDevloper</code></blockquote>",
            parse_mode=ParseMode.HTML
        )

    username = message.command[1].strip()

    try:
        repo_info = await get_all_repository_info(username)

        if not repo_info:
            return await message.reply_text(
                "<blockquote><emoji id=\"5042334757040423886\">⚡️</emoji> <b>No public repositories found</b> or user does not exist.</blockquote>",
                parse_mode=ParseMode.HTML
            )

        chunks = chunk_string(repo_info, 4000)

        for chunk in chunks:
            await message.reply_text(chunk, disable_web_page_preview=True, parse_mode=ParseMode.HTML)

    except Exception as e:
        print(f"Error in /allrepo: {e}")
        await message.reply_text(
            "<blockquote><emoji id=\"5042334757040423886\">⚡️</emoji> <b>An error occurred</b> while fetching repositories.</blockquote>",
            parse_mode=ParseMode.HTML
        )


async def get_all_repository_info(username: str) -> str:
    url = f"https://api.github.com/users/{username}/repos"
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(url)

    if response.status_code != 200:
        return None

    data = response.json()
    if not data:
        return None

    info_lines = [
        f"<blockquote><emoji id=\"5041975203853239332\">🎁</emoji> <b><a href=\"{repo['html_url']}\">{repo['name']}</a></b>\n"
        f"<emoji id=\"5042334757040423886\">⚡️</emoji> Stars: <code>{repo['stargazers_count']}</code> | Forks: <code>{repo['forks_count']}</code>\n"
        f"<emoji id=\"5972072533833289156\">🔹</emoji> {repo['description'] or 'No description'}</blockquote>"
        for repo in data
    ]

    profile_link = f"<blockquote><emoji id=\"5039598514980520994\">❤️‍🔥</emoji> <a href=\"https://github.com/{username}\">View GitHub Profile</a></blockquote>"
    return f"{profile_link}\n\n" + "\n\n".join(info_lines)
