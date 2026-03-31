import os


def get_web_url() -> str:
    """
    Auto-detect the web player public URL.

    Priority:
      1. WEB_APP_URL  – manual override (set this env var on Railway)
      2. RAILWAY_PUBLIC_DOMAIN / RAILWAY_STATIC_URL  – Railway auto-injects this
      3. REPLIT_DEV_DOMAIN  – Replit auto-injects this
      4. Empty string  – no URL available, hide the button
    """
    # 1. Manual override
    url = os.getenv("WEB_APP_URL", "").strip()
    if url:
        return url.rstrip("/")

    # 2. Railway
    for key in ("RAILWAY_PUBLIC_DOMAIN", "RAILWAY_STATIC_URL"):
        val = os.getenv(key, "").strip()
        if val:
            if not val.startswith("http"):
                val = f"https://{val}"
            return val.rstrip("/")

    # 3. Replit
    replit = os.getenv("REPLIT_DEV_DOMAIN", "").strip()
    if replit:
        return f"https://{replit}".rstrip("/")

    return ""


# Module-level singleton – evaluated once at import time.
WEB_URL: str = get_web_url()
