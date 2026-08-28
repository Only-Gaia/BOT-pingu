"""Invite tracker."""
import discord
from discord.ext import commands

from ..db import invites_cache, get_guild, update_guild
from ..helpers import ok, embed


class Invites(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._cache: dict = {}

    @commands.Cog.listener()
    async def on_ready(self):
        for guild in self.bot.guilds:
            await self._refresh_cache(guild)

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        await self._refresh_cache(guild)

    async def _refresh_cache(self, guild: discord.Guild):
        try:
            invs = await guild.invites()
            self._cache[guild.id] = {i.code: i.uses for i in invs}
        except Exception:
            self._cache[guild.id] = {}

    @commands.Cog.listener()
    async def on_invite_create(self, invite):
        self._cache.setdefault(invite.guild.id, {})[invite.code] = invite.uses

    @commands.Cog.listener()
    async def on_invite_delete(self, invite):
        self._cache.setdefault(invite.guild.id, {}).pop(invite.code, None)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        guild = member.guild
        before = self._cache.get(guild.id, {})
        try:
            after_invs = await guild.invites()
        except Exception:
            return
        after = {i.code: i.uses for i in after_invs}
        used = None
        for code, uses in after.items():
            if uses > before.get(code, 0):
                inviter = next((i.inviter for i in after_invs if i.code == code), None)
                used = (code, inviter)
                break
        self._cache[guild.id] = after
        if used and used[1]:
            inviter = used[1]
            await invites_cache.update_one(
                {"guild_id": guild.id, "user_id": inviter.id},
                {"$inc": {"total": 1},
                 "$setOnInsert": {"guild_id": guild.id, "user_id": inviter.id}},
                upsert=True,
            )
            g = await get_guild(guild.id)
            ch_id = g.get("invites_channel")
            if ch_id:
                ch = guild.get_channel(ch_id)
                if ch:
                    doc = await invites_cache.find_one({"guild_id": guild.id, "user_id": inviter.id})
                    total = doc["total"] if doc else 1
                    await ch.send(embed=embed(
                        title="📨 Nuovo invito",
                        description=f"{member.mention} invitato da {inviter.mention} (ora ha **{total}** inviti).",
                    ))

    @commands.command(name="showinvites", aliases=["invites"])
    async def showinvites(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        doc = await invites_cache.find_one({"guild_id": ctx.guild.id, "user_id": member.id})
        total = doc["total"] if doc else 0
        await ctx.send(embed=embed(
            title=f"📨 Inviti di {member.display_name}",
            description=f"**{total}** inviti.",
        ))

    @commands.command(name="setinviteschannel")
    @commands.has_permissions(manage_guild=True)
    async def setinviteschannel(self, ctx, channel: discord.TextChannel):
        await update_guild(ctx.guild.id, {"invites_channel": channel.id})
        await ctx.send(embed=ok(f"Canale inviti impostato su {channel.mention}."))

    @commands.command(name="resetinvites")
    @commands.has_permissions(manage_guild=True)
    async def resetinvites(self, ctx, member: discord.Member = None):
        if member:
            await invites_cache.update_one(
                {"guild_id": ctx.guild.id, "user_id": member.id},
                {"$set": {"total": 0}},
                upsert=True,
            )
            return await ctx.send(embed=ok(f"Inviti di {member.mention} azzerati."))
        await invites_cache.update_many({"guild_id": ctx.guild.id}, {"$set": {"total": 0}})
        await ctx.send(embed=ok("Tutti gli inviti del server sono stati azzerati."))

    @commands.command(name="addinvites")
    @commands.has_permissions(manage_guild=True)
    async def addinvites(self, ctx, member: discord.Member, amount: int):
        await invites_cache.update_one(
            {"guild_id": ctx.guild.id, "user_id": member.id},
            {"$inc": {"total": amount},
             "$setOnInsert": {"guild_id": ctx.guild.id, "user_id": member.id}},
            upsert=True,
        )
        await ctx.send(embed=ok(f"Aggiunti {amount} inviti a {member.mention}."))

    @commands.command(name="removeinvites")
    @commands.has_permissions(manage_guild=True)
    async def removeinvites(self, ctx, member: discord.Member, amount: int):
        await invites_cache.update_one(
            {"guild_id": ctx.guild.id, "user_id": member.id},
            {"$inc": {"total": -amount},
             "$setOnInsert": {"guild_id": ctx.guild.id, "user_id": member.id}},
            upsert=True,
        )
        await ctx.send(embed=ok(f"Rimossi {amount} inviti a {member.mention}."))


async def setup(bot):
    await bot.add_cog(Invites(bot))
