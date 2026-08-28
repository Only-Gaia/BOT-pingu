"""MongoDB helpers for the Discord bot."""
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).parent.parent / ".env")

_client = AsyncIOMotorClient(os.environ["MONGO_URL"])
db = _client[os.environ["DB_NAME"]]

# Collections
users = db.bot_users
guilds = db.bot_guilds
warns = db.bot_warns
messages = db.bot_messages
giveaways = db.bot_giveaways
tickets = db.bot_tickets
invites_cache = db.bot_invites
lucky_claims = db.bot_lucky_claims
daily_claims = db.bot_daily_claims


async def get_user(guild_id: int, user_id: int) -> dict:
    doc = await users.find_one({"guild_id": guild_id, "user_id": user_id})
    if not doc:
        doc = {
            "guild_id": guild_id,
            "user_id": user_id,
            "balance": 0,
            "bank": 0,
            "xp": 0,
            "level": 0,
            "luck": 0,
            "inventory": [],
        }
        await users.insert_one(doc)
    return doc


async def update_user(guild_id: int, user_id: int, update: dict):
    await users.update_one(
        {"guild_id": guild_id, "user_id": user_id},
        {"$set": update},
        upsert=True,
    )


async def inc_user(guild_id: int, user_id: int, inc: dict):
    await users.update_one(
        {"guild_id": guild_id, "user_id": user_id},
        {"$inc": inc, "$setOnInsert": {"guild_id": guild_id, "user_id": user_id}},
        upsert=True,
    )


async def get_guild(guild_id: int) -> dict:
    doc = await guilds.find_one({"guild_id": guild_id})
    if not doc:
        doc = {
            "guild_id": guild_id,
            "automod": {"enabled": False, "link": False, "spam": False, "log_channel": None},
            "welcome": {"channel": None, "message": None},
            "goodbye": {"channel": None, "message": None},
            "invites_channel": None,
            "leave_messages": {"channel": None, "message": None},
        }
        await guilds.insert_one(doc)
    return doc


async def update_guild(guild_id: int, update: dict):
    await guilds.update_one(
        {"guild_id": guild_id},
        {"$set": update, "$setOnInsert": {"guild_id": guild_id}},
        upsert=True,
    )
