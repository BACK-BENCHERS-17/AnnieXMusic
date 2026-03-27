import sys
from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGO_DB_URI, MONGO_DB_NAME
from ..logging import LOGGER

if not MONGO_DB_URI:
    LOGGER(__name__).error("MONGO_DB_URI is not set! Please add your MongoDB URI to your environment variables.")
    sys.exit(1)

if not MONGO_DB_URI.startswith("mongodb"):
    LOGGER(__name__).error("Invalid MONGO_DB_URI! It must start with 'mongodb://' or 'mongodb+srv://'")
    sys.exit(1)

LOGGER(__name__).info("Connecting to your Mongo Database...")

try:
    _mongo_async_ = AsyncIOMotorClient(MONGO_DB_URI, serverSelectionTimeoutMS=5000)
    mongodb = _mongo_async_[MONGO_DB_NAME]
    import asyncio
    loop = asyncio.get_event_loop()
    if loop.is_running():
        pass
    LOGGER(__name__).info(f"Connected to your Mongo Database. (DB: {MONGO_DB_NAME})")
except Exception as e:
    LOGGER(__name__).error(f"Failed to connect to your Mongo Database: {e}")
    sys.exit(1)