"""Misc commands: userinfo, serverinfo, invitebot, help, reset."""
import discord
from discord.ext import commands

from ..helpers import embed, ok


HELP_SECTIONS = {
    "Moderazione": [
        "pex", "depex", "timeout", "untimeout", "ban", "unban", "kick", "changename",
        "warn", "unwarn", "clearwarn", "warncount", "purge", "lock", "unlock", "reset",
    ],
    "Livelli": [
        "livello", "xpadd", "xpremove", "messagecount", "addmessages", "resetmessages", "leavemessages",
    ],
    "Automod": [
        "automod on/off", "automod link on/off", "automod spam on/off", "automod log #ch", "automod log off",
    ],
    "Economia": [
        "balance", "daily", "work", "mine", "tris", "pay", "add", "remove",
        "coinflip", "blackjack", "roulette", "leaderboard",
        "shop", "buy", "inventory", "openbox", "luckybox", "lucky",
    ],
    "Giochi": [
        "8ball", "say", "ship", "rendigay", "rendilesbica", "kiss", "clap", "slap", "hug", "kill", "nitrodonate",
    ],
    "Supporto": [
        "pannelloticket", "giveaway create/end/reroll/list",
        "setwelcome", "setgoodbye",
        "showinvites", "setinviteschannel", "resetinvites", "addinvites", "removeinvites",
        "invitebot", "userinfo", "serverinfo", "help",
    ],
}


class Misc(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="userinfo", aliases=["ui", "whois"])
    async def userinfo(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        e = embed(title=f"Info su {member}")
        e.set_thumbnail(url=member.display_avatar.url)
        e.add_field(name="ID", value=member.id, inline=True)
        e.add_field(name="Bot", value="Sì" if member.bot else "No", inline=True)
        e.add_field(name="Nickname", value=member.nick or "—", inline=True)
        e.add_field(name="Account creato", value=discord.utils.format_dt(member.created_at, "R"), inline=True)
        if member.joined_at:
            e.add_field(name="Entrato", value=discord.utils.format_dt(member.joined_at, "R"), inline=True)
        roles = [r.mention for r in member.roles if r != ctx.guild.default_role][:15]
        e.add_field(name=f"Ruoli ({len(member.roles) - 1})", value=" ".join(roles) or "—", inline=False)
        await ctx.send(embed=e)

    @commands.command(name="serverinfo", aliases=["si", "guildinfo"])
    async def serverinfo(self, ctx):
        g = ctx.guild
        e = embed(title=f"Info su {g.name}")
        if g.icon:
            e.set_thumbnail(url=g.icon.url)
        e.add_field(name="ID", value=g.id, inline=True)
        e.add_field(name="Owner", value=g.owner.mention if g.owner else "—", inline=True)
        e.add_field(name="Membri", value=g.member_count, inline=True)
        e.add_field(name="Canali", value=len(g.channels), inline=True)
        e.add_field(name="Ruoli", value=len(g.roles), inline=True)
        e.add_field(name="Creato", value=discord.utils.format_dt(g.created_at, "R"), inline=True)
        e.add_field(name="Boost", value=f"Tier {g.premium_tier} — {g.premium_subscription_count} boost", inline=True)
        await ctx.send(embed=e)

    @commands.command(name="invitebot", aliases=["invite_bot"])
    async def invitebot(self, ctx):
        app = await self.bot.application_info()
        url = discord.utils.oauth_url(
            app.id,
            permissions=discord.Permissions(administrator=True),
            scopes=["bot", "applications.commands"],
        )
        await ctx.send(embed=embed(title="🔗 Invita il bot", description=f"[Clicca qui]({url}) per aggiungermi al tuo server."))

    @commands.command(name="reset")
    @commands.has_permissions(administrator=True)
    async def reset(self, ctx, member: discord.Member):
        from ..db import update_user
        await update_user(ctx.guild.id, member.id, {
            "balance": 0, "bank": 0, "xp": 0, "level": 0, "luck": 0, "inventory": [],
        })
        await ctx.send(embed=ok(f"Dati economici/xp di {member.mention} azzerati."))

    @commands.command(name="help")
    async def help_cmd(self, ctx, *, section: str = None):
        if section:
            section = section.capitalize()
            if section not in HELP_SECTIONS:
                return await ctx.send(embed=embed(description="Sezione non trovata. Usa `?help` per la lista."))
            e = embed(
                title=f"Aiuto — {section}",
                description=", ".join(f"`?{c}`" for c in HELP_SECTIONS[section]),
            )
            return await ctx.send(embed=e)
        e = embed(
            title="📚 Comandi disponibili",
            description=f"Prefisso: `{self.bot.command_prefix}`\nUsa `?help <sezione>` per dettagli.",
        )
        for name, cmds in HELP_SECTIONS.items():
            e.add_field(name=name, value=", ".join(f"`{c}`" for c in cmds), inline=False)
        e.set_footer(text="Bot in Python — discord.py")
        await ctx.send(embed=e)


async def setup(bot):
    await bot.add_cog(Misc(bot)
