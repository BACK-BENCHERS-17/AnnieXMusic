from pyrogram import filters
from pyrogram.enums import ParseMode
from pyrogram.types import InlineKeyboardMarkup
from ANNIEMUSIC.utils.inline import InlineKeyboardButton
from ANNIEMUSIC import app

import asyncio
import httpx
import ipaddress
import html

IPINFO_TOKEN = "6274faab58da61"
IPQUALITYSCORE_API_KEY = "952ztTq41AxoXam43pStVjVNcEjo1ntQ"

def _flag_emoji(country_code: str | None) -> str:
    if not country_code or len(country_code) != 2:
        return "🏳️"
    cc = country_code.upper()
    return "".join(chr(0x1F1E6 + ord(c) - 65) for c in cc)

def _score_badge(score: int | None) -> tuple[str, str]:
    if score is None:
        return "❓ Unknown", "░░░░░░░░░░ 0/100"
    blocks = max(0, min(10, round(score / 10)))
    bar = "█" * blocks + "░" * (10 - blocks)
    if score <= 20:
        return "✅ Low Risk", f"{bar} {score}/100"
    elif score <= 60:
        return "⚠️ Medium Risk", f"{bar} {score}/100"
    else:
        return "❌ High Risk", f"{bar} {score}/100"

def _escape(v: str | None) -> str:
    return html.escape(v or "N/A")

def _split_asn_org(org: str | None) -> tuple[str, str]:
    if not org:
        return "N/A", "N/A"
    parts = org.split(maxsplit=1)
    if parts and parts[0].startswith("AS"):
        asn = parts[0]
        isp = parts[1] if len(parts) > 1 else "N/A"
        return asn, isp
    return "N/A", org

def _build_card(ip: str, info: dict, score: int | None) -> tuple[str, InlineKeyboardMarkup]:
    country = info.get("country")
    flag = _flag_emoji(country)
    city = info.get("city")
    region = info.get("region")
    loc = info.get("loc")
    org = info.get("org")
    timezone = info.get("timezone")
    postal = info.get("postal")
    asn, isp = _split_asn_org(org)
    badge, bar = _score_badge(score)

    s_ip      = _escape(ip)
    s_city    = _escape(city)
    s_region  = _escape(region)
    s_country = _escape(country)
    s_postal  = _escape(postal)
    s_tz      = _escape(timezone)
    s_asn     = _escape(asn)
    s_isp     = _escape(isp)

    maps_q = loc.replace(" ", "") if loc else ""
    maps_url = f"https://maps.google.com/?q={maps_q}" if maps_q else f"https://duckduckgo.com/?q={s_ip}"
    ipinfo_url = f"https://ipinfo.io/{s_ip}"
    ipqs_url = f"https://www.ipqualityscore.com/free-ip-lookup-proxy-vpn-test/lookup/{s_ip}"
    abuse_url = f"https://www.abuseipdb.com/check/{s_ip}"

    text = (
        f"<blockquote><emoji id=\"5042334757040423886\">⚡️</emoji> <b>IP Intelligence</b>\n"
        f"{flag} <b>{s_ip}</b></blockquote>\n"
        f"<blockquote><emoji id=\"5039598514980520994\">❤️‍🔥</emoji> <b>Risk:</b> {badge}\n"
        f"<code>{bar}</code></blockquote>\n"
        f"<blockquote><emoji id=\"5449449325434266744\">❄️</emoji> <b>City:</b> <code>{s_city}</code>\n"
        f"<emoji id=\"5972072533833289156\">🔹</emoji> <b>Region:</b> <code>{s_region}</code>\n"
        f"<emoji id=\"5041975203853239332\">🎁</emoji> <b>Country:</b> <code>{s_country}</code>\n"
        f"<emoji id=\"5042334757040423886\">⚡️</emoji> <b>Postal:</b> <code>{s_postal}</code>\n"
        f"<emoji id=\"5039598514980520994\">❤️‍🔥</emoji> <b>Timezone:</b> <code>{s_tz}</code>\n"
        f"<emoji id=\"5449449325434266744\">❄️</emoji> <b>ISP:</b> <code>{s_isp}</code>\n"
        f"<emoji id=\"5972072533833289156\">🔹</emoji> <b>ASN:</b> <code>{s_asn}</code></blockquote>"
    )

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🗺️ View on Maps", url=maps_url),
            InlineKeyboardButton("ℹ️ ipinfo", url=ipinfo_url),
        ],
        [
            InlineKeyboardButton("🛡️ IPQualityScore", url=ipqs_url),
            InlineKeyboardButton("🚫 AbuseIPDB", url=abuse_url),
        ],
    ])
    return text, keyboard

async def fetch_ipinfo(client: httpx.AsyncClient, ip: str) -> dict | None:
    url = f"https://ipinfo.io/{ip}?token={IPINFO_TOKEN}"
    try:
        r = await client.get(url, timeout=10)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None

async def fetch_ipqs(client: httpx.AsyncClient, ip: str) -> int | None:
    url = f"https://ipqualityscore.com/api/json/ip/{IPQUALITYSCORE_API_KEY}/{ip}"
    try:
        r = await client.get(url, timeout=12)
        if r.status_code == 200:
            data = r.json()
            fs = data.get("fraud_score")
            return int(fs) if isinstance(fs, (int, float, str)) and str(fs).isdigit() else None
    except Exception:
        pass
    return None

@app.on_message(filters.command(["ip"]))
async def ip_info_and_score(_, message):
    if len(message.command) != 2:
        await message.reply_text(
            "<blockquote><emoji id=\"5042334757040423886\">⚡️</emoji> <b>IP Lookup</b></blockquote>\n"
            "<blockquote><emoji id=\"5039598514980520994\">❤️‍🔥</emoji> Please provide an IP address.\n"
            "<b>Example:</b> <code>/ip 8.8.8.8</code></blockquote>",
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
        )
        return

    ip_raw = message.command[1].strip()

    try:
        ip_obj = ipaddress.ip_address(ip_raw)
        if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_reserved or ip_obj.is_multicast:
            await message.reply_text(
                "<blockquote><emoji id=\"5042334757040423886\">⚡️</emoji> That looks like a <b>non-routable</b> or <b>private</b> address.\n"
                "Please provide a public IP.</blockquote>",
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
            )
            return
    except ValueError:
        await message.reply_text(
            "<blockquote><emoji id=\"5042334757040423886\">⚡️</emoji> <b>Invalid IP format.</b> Please provide a valid IPv4 or IPv6 address.\n"
            "<b>Example:</b> <code>/ip 1.1.1.1</code></blockquote>",
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
        )
        return

    wait_msg = await message.reply_text(
        "<blockquote><emoji id=\"5039598514980520994\">❤️‍🔥</emoji> <b>Analyzing IP...</b> fetching intelligence 🔍</blockquote>",
        parse_mode=ParseMode.HTML
    )

    async with httpx.AsyncClient(headers={"User-Agent": "AnnieX/IpIntel/1.0"}) as client:
        ipinfo_task = fetch_ipinfo(client, ip_raw)
        ipqs_task = fetch_ipqs(client, ip_raw)
        ipinfo, score = await asyncio.gather(ipinfo_task, ipqs_task)

    if not ipinfo and score is None:
        await wait_msg.edit_text(
            "<blockquote><emoji id=\"5042334757040423886\">⚡️</emoji> <b>Unable to fetch details</b> for the provided IP. Please try again later.</blockquote>",
            parse_mode=ParseMode.HTML
        )
        return

    text, keyboard = _build_card(ip_raw, ipinfo or {}, score)
    await wait_msg.edit_text(
        text,
        reply_markup=keyboard,
        disable_web_page_preview=True,
        parse_mode=ParseMode.HTML,
    )
