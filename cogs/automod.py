"""AutoMod: link filter, spam filter, log."""
import re
import time
from collections import defaultdict, deque

import discord
from discord.ext import commands

from db import get_guild, update_guild
from helpers import ok, err, embed

LINK_RE = re.compile(r"https?://|discord\.gg/", re.IGNORECASE)


class AutoMod(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._spam = defaultdict(lambda: deque(maxlen=6))

    @commands.group(name="automod", invoke_without_command=True)
    @commands.has_permissions(manage_guild=True)
    async def automod(self, ctx, state: str = None):
        g = await get_guild(ctx.guild.id)
        if state is None:
            am = g["automod"]
            e = embed(title="AutoMod")
            e.add_field(name="Attivo", value="Sì" if am["enabled"] else "No", inline=True)
            e.add_field(name="Link filter", value="Sì" if am["link"] else "No", inline=True)
            e.add_field(name="Spam filter", value="Sì" if am["spam"] else "No", inline=True)
            e.add_field(name="Log channel", value=f"<#{am['log_channel']}>" if am["log_channel"] else "—", inline=False)
            return await ctx.send(embed=e)
        if state.lower() not in ("on", "off"):
            return await ctx.send(embed=err("Usa `on` o `off`."))
        g["automod"]["enabled"] = state.lower() == "on"
        await update_guild(ctx.guild.id, {"automod": g["automod"]})
        await ctx.send(embed=ok(f"AutoMod {'attivato' if g['automod']['enabled'] else 'disattivato'}."))

    @automod.command(name="link")
    @commands.has_permissions(manage_guild=True)
    async def automod_link(self, ctx, state: str):
        if state.lower() not in ("on", "off"):
            return await ctx.send(embed=err("Usa `on` o `off`."))
        g = await get_guild(ctx.guild.id)
        g["automod"]["link"] = state.lower() == "on"
        await update_guild(ctx.guild.id, {"automod": g["automod"]})
        await ctx.send(embed=ok(f"AutoMod link {'attivato' if g['automod']['link'] else 'disattivato'}."))

    @automod.command(name="spam")
    @commands.has_permissions(manage_guild=True)
    async def automod_spam(self, ctx, state: str):
        if state.lower() not in ("on", "off"):
            return await ctx.send(embed=err("Usa `on` o `off`."))
        g = await get_guild(ctx.guild.id)
        g["automod"]["spam"] = state.lower() == "on"
        await update_guild(ctx.guild.id, {"automod": g["automod"]})
        await ctx.send(embed=ok(f"AutoMod spam {'attivato' if g['automod']['spam'] else 'disattivato'}."))

    @automod.command(name="log")
    @commands.has_permissions(manage_guild=True)
    async def automod_log(self, ctx, channel: discord.TextChannel = None):
        g = await get_guild(ctx.guild.id)
        g["automod"]["log_channel"] = channel.id if channel else None
        await update_guild(ctx.guild.id, {"automod": g["automod"]})
        if channel:
            await ctx.send(embed=ok(f"Log automod impostato su {channel.mention}."))
        else:
            await ctx.send(embed=ok("Log automod disattivato."))

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        if message.author.guild_permissions.manage_guild:
            return
        g = await get_guild(message.guild.id)
        am = g["automod"]
        if not am["enabled"]:
            return

        async def action(reason: str):
            try:
                await message.delete()
            except Exception:
                pass
            log_id = am.get("log_channel")
            if log_id:
                ch = message.guild.get_channel(log_id)
                if ch:
                    e = embed(title="🛡️ AutoMod",
                              description=f"{message.author.mention} in {message.channel.mention}",
                              color=0xed4245)
                    e.add_field(name="Motivo", value=reason, inline=False)
                    e.add_field(name="Contenuto", value=(message.content[:1000] or "—"), inline=False)
                    await ch.send(embed=e)

        if am["link"] and LINK_RE.search(message.content or ""):
            return await action("Link non consentito")

        if am["spam"]:
            key = (message.guild.id, message.author.id)
            q = self._spam[key]
            now = time.time()
            q.append(now)
            recent = [t for t in q if now - t < 5]
            if len(recent) >= 5:
                q.clear()
                return await action("Spam rilevato")


async def setup(bot):
    await bot.add_cog(AutoMod(bot))
