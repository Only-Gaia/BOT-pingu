"""Moderation commands."""
from datetime import timedelta, datetime, timezone

import discord
from discord.ext import commands

from ..db import warns as warns_col
from ..helpers import ok, err, embed


class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="pex")
    @commands.has_permissions(manage_roles=True)
    async def pex(self, ctx, member: discord.Member, *, role: discord.Role):
        await member.add_roles(role, reason=f"pex by {ctx.author}")
        await ctx.send(embed=ok(f"Ruolo {role.mention} aggiunto a {member.mention}."))

    @commands.command(name="depex")
    @commands.has_permissions(manage_roles=True)
    async def depex(self, ctx, member: discord.Member, *, role: discord.Role):
        await member.remove_roles(role, reason=f"depex by {ctx.author}")
        await ctx.send(embed=ok(f"Ruolo {role.mention} rimosso da {member.mention}."))

    @commands.command(name="timeout")
    @commands.has_permissions(moderate_members=True)
    async def timeout(self, ctx, member: discord.Member, minutes: int, *, reason: str = "Nessun motivo"):
        until = discord.utils.utcnow() + timedelta(minutes=minutes)
        await member.timeout(until, reason=reason)
        await ctx.send(embed=ok(f"{member.mention} in timeout per {minutes} min.\n**Motivo:** {reason}"))

    @commands.command(name="untimeout")
    @commands.has_permissions(moderate_members=True)
    async def untimeout(self, ctx, member: discord.Member):
        await member.timeout(None, reason=f"untimeout by {ctx.author}")
        await ctx.send(embed=ok(f"Timeout rimosso da {member.mention}."))

    @commands.command(name="ban")
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx, member: discord.Member, *, reason: str = "Nessun motivo"):
        await member.ban(reason=reason, delete_message_days=0)
        await ctx.send(embed=ok(f"{member} bannato.\n**Motivo:** {reason}"))

    @commands.command(name="unban")
    @commands.has_permissions(ban_members=True)
    async def unban(self, ctx, user_id: int):
        user = await self.bot.fetch_user(user_id)
        await ctx.guild.unban(user, reason=f"unban by {ctx.author}")
        await ctx.send(embed=ok(f"{user} sbannato."))

    @commands.command(name="kick")
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx, member: discord.Member, *, reason: str = "Nessun motivo"):
        await member.kick(reason=reason)
        await ctx.send(embed=ok(f"{member} espulso.\n**Motivo:** {reason}"))

    @commands.command(name="changename")
    @commands.has_permissions(manage_nicknames=True)
    async def changename(self, ctx, member: discord.Member, *, new_name: str):
        await member.edit(nick=new_name, reason=f"changename by {ctx.author}")
        await ctx.send(embed=ok(f"Nickname di {member.mention} cambiato in **{new_name}**."))

    @commands.command(name="warn")
    @commands.has_permissions(moderate_members=True)
    async def warn(self, ctx, member: discord.Member, *, reason: str = "Nessun motivo"):
        w = {
            "guild_id": ctx.guild.id,
            "user_id": member.id,
            "moderator_id": ctx.author.id,
            "reason": reason,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        r = await warns_col.insert_one(w)
        count = await warns_col.count_documents({"guild_id": ctx.guild.id, "user_id": member.id})
        e = embed(title="⚠️ Warn", description=f"{member.mention} ha ricevuto un warn.", color=0xfee75c)
        e.add_field(name="Motivo", value=reason, inline=False)
        e.add_field(name="Warn totali", value=str(count), inline=True)
        e.add_field(name="ID Warn", value=str(r.inserted_id), inline=True)
        await ctx.send(embed=e)

    @commands.command(name="unwarn")
    @commands.has_permissions(moderate_members=True)
    async def unwarn(self, ctx, member: discord.Member):
        latest = await warns_col.find_one(
            {"guild_id": ctx.guild.id, "user_id": member.id},
            sort=[("created_at", -1)],
        )
        if not latest:
            return await ctx.send(embed=err("Questo utente non ha warn."))
        await warns_col.delete_one({"_id": latest["_id"]})
        await ctx.send(embed=ok(f"Ultimo warn di {member.mention} rimosso."))

    @commands.command(name="clearwarn", aliases=["clear_warn", "resetwarn", "reset_warn"])
    @commands.has_permissions(moderate_members=True)
    async def clearwarn(self, ctx, member: discord.Member):
        res = await warns_col.delete_many({"guild_id": ctx.guild.id, "user_id": member.id})
        await ctx.send(embed=ok(f"Rimossi {res.deleted_count} warn di {member.mention}."))

    @commands.command(name="warncount")
    async def warncount(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        cursor = warns_col.find({"guild_id": ctx.guild.id, "user_id": member.id}).sort("created_at", -1)
        items = await cursor.to_list(length=25)
        e = embed(title=f"Warn di {member.display_name}", description=f"Totale: **{len(items)}**")
        for i, w in enumerate(items[:10], 1):
            mod = ctx.guild.get_member(w["moderator_id"])
            e.add_field(name=f"#{i} — {w['reason']}", value=f"da {mod.mention if mod else w['moderator_id']}", inline=False)
        await ctx.send(embed=e)

    @commands.command(name="purge")
    @commands.has_permissions(manage_messages=True)
    async def purge(self, ctx, amount: int):
        if amount < 1 or amount > 100:
            return await ctx.send(embed=err("Fornisci un numero tra 1 e 100."))
        deleted = await ctx.channel.purge(limit=amount + 1)
        msg = await ctx.send(embed=ok(f"Eliminati {len(deleted)-1} messaggi."))
        await msg.delete(delay=3)

    @commands.command(name="lock")
    @commands.has_permissions(manage_channels=True)
    async def lock(self, ctx):
        overwrite = ctx.channel.overwrites_for(ctx.guild.default_role)
        overwrite.send_messages = False
        await ctx.channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)
        await ctx.send(embed=ok("Canale bloccato 🔒"))

    @commands.command(name="unlock")
    @commands.has_permissions(manage_channels=True)
    async def unlock(self, ctx):
        overwrite = ctx.channel.overwrites_for(ctx.guild.default_role)
        overwrite.send_messages = None
        await ctx.channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)
        await ctx.send(embed=ok("Canale sbloccato 🔓"))


async def setup(bot):
    await bot.add_cog(Moderation(bot))
