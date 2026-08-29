"""Level / XP / message-count system."""
import random

import discord
from discord.ext import commands

from db import get_user, update_user, messages as msg_col, get_guild, update_guild
from helpers import ok, embed, level_from_xp, xp_for_level


class Levels(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        await msg_col.update_one(
            {"guild_id": message.guild.id, "user_id": message.author.id},
            {"$inc": {"count": 1},
             "$setOnInsert": {"guild_id": message.guild.id, "user_id": message.author.id}},
            upsert=True,
        )
        gain = random.randint(5, 15)
        u_before = await get_user(message.guild.id, message.author.id)
        new_xp = u_before["xp"] + gain
        new_level = level_from_xp(new_xp)
        old_level = u_before.get("level", 0)
        await update_user(message.guild.id, message.author.id, {"xp": new_xp, "level": new_level})
        if new_level > old_level:
            try:
                await message.channel.send(f"🎉 {message.author.mention} sei salito al **livello {new_level}**!")
            except Exception:
                pass

    @commands.command(name="livello", aliases=["level", "rank"])
    async def livello(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        u = await get_user(ctx.guild.id, member.id)
        lvl = u.get("level", 0)
        xp = u.get("xp", 0)
        need = xp_for_level(lvl + 1)
        e = embed(title=f"📈 Livello di {member.display_name}")
        e.add_field(name="Livello", value=str(lvl), inline=True)
        e.add_field(name="XP", value=f"{xp} / {need}", inline=True)
        await ctx.send(embed=e)

    @commands.command(name="xpadd")
    @commands.has_permissions(administrator=True)
    async def xpadd(self, ctx, member: discord.Member, amount: int):
        u = await get_user(ctx.guild.id, member.id)
        new_xp = max(0, u["xp"] + amount)
        await update_user(ctx.guild.id, member.id, {"xp": new_xp, "level": level_from_xp(new_xp)})
        await ctx.send(embed=ok(f"Aggiunti {amount} XP a {member.mention}."))

    @commands.command(name="xpremove")
    @commands.has_permissions(administrator=True)
    async def xpremove(self, ctx, member: discord.Member, amount: int):
        u = await get_user(ctx.guild.id, member.id)
        new_xp = max(0, u["xp"] - amount)
        await update_user(ctx.guild.id, member.id, {"xp": new_xp, "level": level_from_xp(new_xp)})
        await ctx.send(embed=ok(f"Rimossi {amount} XP a {member.mention}."))

    @commands.command(name="messagecount", aliases=["msgcount", "mc"])
    async def messagecount(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        doc = await msg_col.find_one({"guild_id": ctx.guild.id, "user_id": member.id})
        c = doc["count"] if doc else 0
        await ctx.send(embed=embed(title=f"💬 Messaggi di {member.display_name}", description=f"**{c}** messaggi."))

    @commands.command(name="addmessages")
    @commands.has_permissions(administrator=True)
    async def addmessages(self, ctx, member: discord.Member, amount: int):
        await msg_col.update_one(
            {"guild_id": ctx.guild.id, "user_id": member.id},
            {"$inc": {"count": amount},
             "$setOnInsert": {"guild_id": ctx.guild.id, "user_id": member.id}},
            upsert=True,
        )
        await ctx.send(embed=ok(f"Aggiunti {amount} messaggi a {member.mention}."))

    @commands.command(name="resetmessages")
    @commands.has_permissions(administrator=True)
    async def resetmessages(self, ctx, member: discord.Member):
        await msg_col.update_one(
            {"guild_id": ctx.guild.id, "user_id": member.id},
            {"$set": {"count": 0}},
            upsert=True,
        )
        await ctx.send(embed=ok(f"Messaggi di {member.mention} azzerati."))

    @commands.command(name="leavemessages")
    @commands.has_permissions(manage_guild=True)
    async def leavemessages(self, ctx, channel: discord.TextChannel = None, *, message: str = None):
        g = await get_guild(ctx.guild.id)
        g.setdefault("leave_messages", {})
        if channel:
            g["leave_messages"]["channel"] = channel.id
        if message:
            g["leave_messages"]["message"] = message
        await update_guild(ctx.guild.id, {"leave_messages": g["leave_messages"]})
        await ctx.send(embed=ok("Impostazioni leave-messages aggiornate."))


async def setup(bot):
    await bot.add_cog(Levels(bot))
