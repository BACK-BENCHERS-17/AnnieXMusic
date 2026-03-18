from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ParseMode
from ANNIEMUSIC import app
import httpx
import re


async def get_anime_info(anime_name):
    url = 'https://graphql.anilist.co'
    query = '''
    query ($anime: String) {
      Media (search: $anime, type: ANIME) {
        id
        title {
          romaji
          english
          native
        }
        description(asHtml: false)
        episodes
        status
        averageScore
        coverImage {
          large
        }
      }
    }
    '''
    variables = {"anime": anime_name}
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(url, json={'query': query, 'variables': variables})

    data = response.json()

    if 'errors' in data:
        return None, f"<blockquote><emoji id=\"5042334757040423886\">⚡️</emoji> <b>Error:</b> {data['errors'][0]['message']}</blockquote>"

    return data['data']['Media'], None


def clean_description(desc):
    if not desc:
        return "No description available."
    desc = re.sub(r"<br\s*/?>", "\n", desc)
    desc = re.sub(r"<[^>]+>", "", desc)
    return desc.strip()[:800] + "..." if len(desc) > 800 else desc


@app.on_message(filters.command("anime"))
async def anime_info(client: Client, message: Message):
    if len(message.command) < 2:
        return await message.reply_text(
            "<blockquote><emoji id=\"5042334757040423886\">⚡️</emoji> <b>Anime Search</b></blockquote>\n"
            "<blockquote><emoji id=\"5039598514980520994\">❤️‍🔥</emoji> Please provide an anime name.\n"
            "<b>Example:</b> <code>/anime Naruto</code></blockquote>",
            parse_mode=ParseMode.HTML
        )

    anime_name = " ".join(message.command[1:])
    result, error = await get_anime_info(anime_name)

    if not result:
        return await message.reply_text(
            error or "<blockquote><emoji id=\"5042334757040423886\">⚡️</emoji> <b>Anime not found.</b></blockquote>",
            parse_mode=ParseMode.HTML
        )

    title = result['title']['romaji']
    english = result['title'].get('english')
    native = result['title']['native']
    episodes = result.get('episodes', 'N/A')
    status = result.get('status', 'N/A')
    score = result.get('averageScore', 'N/A')
    desc = clean_description(result.get('description'))
    image = result['coverImage']['large']

    english_line = f"<emoji id=\"5449449325434266744\">❄️</emoji> <b>Title (English):</b> {english}\n" if english else ""

    caption = (
        f"<blockquote><emoji id=\"5041975203853239332\">🎁</emoji> <b>{title}</b></blockquote>\n"
        f"<blockquote>"
        f"<emoji id=\"5042334757040423886\">⚡️</emoji> <b>Romaji:</b> {title}\n"
        f"{english_line}"
        f"<emoji id=\"5972072533833289156\">🔹</emoji> <b>Native:</b> {native}\n"
        f"<emoji id=\"5039598514980520994\">❤️‍🔥</emoji> <b>Episodes:</b> {episodes}\n"
        f"<emoji id=\"5449449325434266744\">❄️</emoji> <b>Score:</b> {score}/100\n"
        f"<emoji id=\"5041975203853239332\">🎁</emoji> <b>Status:</b> {status}"
        f"</blockquote>\n"
        f"<blockquote><emoji id=\"5972072533833289156\">🔹</emoji> <b>Description:</b>\n{desc}</blockquote>"
    )

    await message.reply_photo(
        image,
        caption=caption,
        parse_mode=ParseMode.HTML
    )
