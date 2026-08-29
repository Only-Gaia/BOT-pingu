"""Welcome & goodbye messages."""
import discord
from discord.ext import commands
from db import get_guild, update_guild
from helpers import ok, embed


def _fmt(msg: str, member: discord.Member) -> str:
    return (
        msg
        .replace("{user}", member.mention)
        .replace("{username}", member.name)
        .replace("{server}", member.guild.name)
        .replace("{count}", str(member.guild.member_count or 0))
    )


class Welcome(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="setwelcome")
    @commands.has_permissions(manage_guild=True)
    async def setwelcome(self, ctx, channel: discord.TextChannel, *, message: str):
        await update_guild(ctx.guild.id, {"welcome": {"channel": channel.id, "message": message}})
        await ctx.send(embed=ok(f"Messaggio di benvenuto impostato in {channel.mention}."))

    @commands.command(name="setgoodbye")
    @commands.has_permissions(manage_guild=True)
    async def setgoodbye(self, ctx, channel: discord.TextChannel, *, message: str):
        await update_guild(ctx.guild.id, {"goodbye": {"channel": channel.id, "message": message}})
        await ctx.send(embed=ok(f"Messaggio di addio impostato in {channel.mention}."))

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        g = await get_guild(member.guild.id)
        w = g.get("welcome") or {}
        if w.get("channel") and w.get("message"):
            ch = member.guild.get_channel(w["channel"])
            if ch:
                await ch.send(embed=embed(title="👋 Benvenuto!", description=_fmt(w["message"], member)))

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        g = await get_guild(member.guild.id)
        gb = g.get("goodbye") or {}
        if gb.get("channel") and gb.get("message"):
            ch = member.guild.get_channel(gb["channel"])
            if ch:
                await ch.send(embed=embed(title="😢 Addio", description=_fmt(gb["message"], member)))
        lm = g.get("leave_messages") or {}
        if lm.get("channel") and lm.get("message"):
            ch = member.guild.get_channel(lm["channel"])
            if ch:
                await ch.send(embed=embed(title="Utente uscito", description=_fmt(lm["message"], member)))


async def setup(bot):
    await bot.add_cog(Welcome(bot))
