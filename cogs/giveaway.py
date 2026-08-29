"""Giveaway commands."""
import random
from datetime import datetime, timezone, timedelta

import discord
from discord.ext import commands, tasks

from db import giveaways as gw_col
from helpers import ok, err, embed


def parse_duration(s: str) -> int:
    unit = s[-1].lower()
    try:
        n = int(s[:-1])
    except Exception:
        return 0
    return {"s": 1, "m": 60, "h": 3600, "d": 86400}.get(unit, 0) * n


class Giveaway(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_loop.start()

    def cog_unload(self):
        self.check_loop.cancel()

    @tasks.loop(seconds=15)
    async def check_loop(self):
        now = datetime.now(timezone.utc).isoformat()
        cursor = gw_col.find({"ended": False, "ends_at": {"$lte": now}})
        async for gw in cursor:
            await self._end(gw)

    @check_loop.before_loop
    async def before_check(self):
        await self.bot.wait_until_ready()

    async def _end(self, gw: dict):
        guild = self.bot.get_guild(gw["guild_id"])
        if not guild:
            await gw_col.update_one({"_id": gw["_id"]}, {"$set": {"ended": True}})
            return
        ch = guild.get_channel(gw["channel_id"])
        if not ch:
            await gw_col.update_one({"_id": gw["_id"]}, {"$set": {"ended": True}})
            return
        try:
            msg = await ch.fetch_message(gw["message_id"])
        except Exception:
            msg = None
        participants = []
        if msg:
            for r in msg.reactions:
                if str(r.emoji) == "🎉":
                    async for u in r.users():
                        if not u.bot:
                            participants.append(u)
                    break
        winners = random.sample(participants, min(gw["winners"], len(participants))) if participants else []
        mentions = ", ".join(w.mention for w in winners) if winners else "*nessun partecipante*"
        e = embed(
            title="🎉 Giveaway concluso!",
            description=f"**Premio:** {gw['prize']}\n**Vincitori:** {mentions}",
        )
        await ch.send(embed=e)
        await gw_col.update_one(
            {"_id": gw["_id"]},
            {"$set": {"ended": True, "winners_list": [w.id for w in winners]}},
        )

    @commands.group(name="giveaway", aliases=["gw"], invoke_without_command=True)
    async def giveaway(self, ctx):
        await ctx.send(embed=embed(
            title="Giveaway",
            description=(
                "`?giveaway create <durata> <vincitori> <premio>`\n"
                "`?giveaway end <msg_id>`\n"
                "`?giveaway reroll <msg_id>`\n"
                "`?giveaway list`"
            ),
        ))

    @giveaway.command(name="create")
    @commands.has_permissions(manage_guild=True)
    async def gw_create(self, ctx, duration: str, winners: int, *, prize: str):
        secs = parse_duration(duration)
        if secs <= 0:
            return await ctx.send(embed=err("Durata non valida (es: 10m, 2h, 1d)."))
        if winners <= 0:
            return await ctx.send(embed=err("Numero vincitori non valido."))
        ends = datetime.now(timezone.utc) + timedelta(seconds=secs)
        e = embed(
            title="🎉 GIVEAWAY 🎉",
            description=(
                f"**Premio:** {prize}\n**Vincitori:** {winners}\n"
                f"**Termina:** <t:{int(ends.timestamp())}:R>\n\nReagisci con 🎉 per partecipare!"
            ),
        )
        msg = await ctx.send(embed=e)
        await msg.add_reaction("🎉")
        await gw_col.insert_one({
            "guild_id": ctx.guild.id,
            "channel_id": ctx.channel.id,
            "message_id": msg.id,
            "prize": prize,
            "winners": winners,
            "ends_at": ends.isoformat(),
            "ended": False,
            "host_id": ctx.author.id,
        })

    @giveaway.command(name="end")
    @commands.has_permissions(manage_guild=True)
    async def gw_end(self, ctx, message_id: int):
        gw = await gw_col.find_one({"message_id": message_id, "guild_id": ctx.guild.id})
        if not gw:
            return await ctx.send(embed=err("Giveaway non trovato."))
        if gw["ended"]:
            return await ctx.send(embed=err("Giveaway già concluso."))
        await gw_col.update_one({"_id": gw["_id"]}, {"$set": {"ends_at": datetime.now(timezone.utc).isoformat()}})
        await self._end(gw)

    @giveaway.command(name="reroll")
    @commands.has_permissions(manage_guild=True)
    async def gw_reroll(self, ctx, message_id: int):
        gw = await gw_col.find_one({"message_id": message_id, "guild_id": ctx.guild.id})
        if not gw:
            return await ctx.send(embed=err("Giveaway non trovato."))
        ch = ctx.guild.get_channel(gw["channel_id"])
        if not ch:
            return await ctx.send(embed=err("Canale del giveaway non trovato."))
        try:
            msg = await ch.fetch_message(message_id)
        except Exception:
            return await ctx.send(embed=err("Messaggio non trovato."))
        participants = []
        for r in msg.reactions:
            if str(r.emoji) == "🎉":
                async for u in r.users():
                    if not u.bot:
                        participants.append(u)
                break
        if not participants:
            return await ctx.send(embed=err("Nessun partecipante."))
        winner = random.choice(participants)
        await ch.send(embed=ok(f"🎉 Nuovo vincitore: {winner.mention} per **{gw['prize']}**!"))

    @giveaway.command(name="list")
    async def gw_list(self, ctx):
        cursor = gw_col.find({"guild_id": ctx.guild.id, "ended": False})
        e = embed(title="🎉 Giveaway attivi")
        n = 0
        async for gw in cursor:
            n += 1
            ends = datetime.fromisoformat(gw["ends_at"])
            e.add_field(
                name=gw["prize"],
                value=f"ID: `{gw['message_id']}` — <t:{int(ends.timestamp())}:R>",
                inline=False,
            )
        if n == 0:
            e.description = "Nessun giveaway attivo."
        await ctx.send(embed=e)


async def setup(bot):
    await bot.add_cog(Giveaway(bot))
