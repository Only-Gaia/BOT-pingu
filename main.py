"""Main Discord bot entry point."""
import os
import logging
from pathlib import Path
import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

logger = logging.getLogger("discord_bot")
logging.basicConfig(level=logging.INFO)

PREFIX = os.environ.get("BOT_PREFIX", "?")
TOKEN = os.environ.get("DISCORD_TOKEN")

intents = discord.Intents.all()
bot = commands.Bot(
    command_prefix=PREFIX,
    intents=intents,
    help_command=None,
    case_insensitive=True,
)

INITIAL_COGS = [
    "cogs.moderation",
    "cogs.automod",
    "cogs.economy",
    "cogs.games",
    "cogs.levels",
    "cogs.tickets",
    "cogs.giveaway",
    "cogs.invites",
    "cogs.welcome",
    "cogs.misc",
]


@bot.event
async def on_ready():
    logger.info("Bot connesso come %s (id=%s)", bot.user, bot.user.id if bot.user else "?")
    await bot.change_presence(activity=discord.Game(name=f"{PREFIX}help"))


@bot.event
async def on_command_error(ctx, error):
    from helpers import err
    if isinstance(error, commands.CommandNotFound):
        return
    if isinstance(error, commands.MissingPermissions):
        return await ctx.send(embed=err("Ti mancano i permessi per usare questo comando."))
    if isinstance(error, commands.MissingRequiredArgument):
        return await ctx.send(embed=err(f"Argomento mancante: `{error.param.name}`."))
    if isinstance(error, commands.BadArgument):
        return await ctx.send(embed=err(f"Argomento non valido: {error}"))
    if isinstance(error, commands.CommandOnCooldown):
        return await ctx.send(embed=err(f"Rilassa! Riprova tra {int(error.retry_after)}s."))
    logger.exception("Command error: %s", error)
    try:
        await ctx.send(embed=err(f"Errore imprevisto: `{error}`"))
    except Exception:
        pass


async def _load_cogs():
    for c in INITIAL_COGS:
        try:
            await bot.load_extension(c)
            logger.info("Cog caricato: %s", c)
        except Exception as e:
            logger.exception("Errore nel caricare %s: %s", c, e)


async def start_bot():
    if not TOKEN:
        logger.error("DISCORD_TOKEN non impostato.")
        return
    await _load_cogs()
    try:
        await bot.start(TOKEN)
    except discord.LoginFailure:
        logger.error("Token Discord non valido.")
    except Exception:
        logger.exception("Bot crashed")


if __name__ == "__main__":
    import asyncio
    asyncio.run(start_bot())
