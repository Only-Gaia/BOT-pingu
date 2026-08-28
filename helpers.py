"""Common helpers for the bot cogs."""
import discord

EMBED_COLOR = 0x2b2d31
OK_COLOR = 0x57f287
ERR_COLOR = 0xed4245
WARN_COLOR = 0xfee75c


def embed(title=None, description=None, color=EMBED_COLOR):
    e = discord.Embed(color=color)
    if title:
        e.title = title
    if description:
        e.description = description
    return e


def ok(description, title="Successo"):
    return embed(title=f"✅ {title}", description=description, color=OK_COLOR)


def err(description, title="Errore"):
    return embed(title=f"❌ {title}", description=description, color=ERR_COLOR)


def warn(description, title="Attenzione"):
    return embed(title=f"⚠️ {title}", description=description, color=WARN_COLOR)


def level_from_xp(xp: int) -> int:
    lvl = 0
    while (lvl + 1) ** 2 * 100 <= xp:
        lvl += 1
    return lvl


def xp_for_level(level: int) -> int:
    return level ** 2 * 100
