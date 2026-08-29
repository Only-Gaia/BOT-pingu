"""Economy commands."""
import random
import asyncio
from datetime import datetime, timezone, timedelta

import discord
from discord.ext import commands

from db import get_user, update_user, inc_user, users, daily_claims, lucky_claims
from helpers import ok, err, embed


SHOP = {
    "box":      {"price": 500,  "desc": "Un box misterioso. Aprilo con `?openbox`."},
    "luckybox": {"price": 1500, "desc": "Un luckybox raro. Aprilo con `?luckybox`."},
    "ring":     {"price": 5000, "desc": "Un anello scintillante 💍."},
    "sword":    {"price": 2500, "desc": "Una spada affilata 🗡️."},
    "potion":   {"price": 300,  "desc": "Una pozione (bonus fortuna temporaneo)."},
}

CURRENCY = "🪙"


def _inv_add(inv, item, qty=1):
    for it in inv:
        if it["item"] == item:
            it["qty"] += qty
            return inv
    inv.append({"item": item, "qty": qty})
    return inv


def _inv_remove(inv, item, qty=1):
    for it in inv:
        if it["item"] == item:
            it["qty"] -= qty
            if it["qty"] <= 0:
                inv.remove(it)
            return True
    return False


class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="balance", aliases=["bal"])
    async def balance(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        u = await get_user(ctx.guild.id, member.id)
        e = embed(title=f"Portafoglio di {member.display_name}")
        e.add_field(name="Saldo", value=f"{u['balance']} {CURRENCY}", inline=True)
        e.add_field(name="Fortuna", value=f"{u.get('luck', 0)} 🍀", inline=True)
        await ctx.send(embed=e)

    @commands.command(name="pay")
    async def pay(self, ctx, member: discord.Member, amount: int):
        if member.id == ctx.author.id:
            return await ctx.send(embed=err("Non puoi pagare te stesso."))
        if amount <= 0:
            return await ctx.send(embed=err("Importo non valido."))
        u = await get_user(ctx.guild.id, ctx.author.id)
        if u["balance"] < amount:
            return await ctx.send(embed=err("Fondi insufficienti."))
        await inc_user(ctx.guild.id, ctx.author.id, {"balance": -amount})
        await inc_user(ctx.guild.id, member.id, {"balance": amount})
        await ctx.send(embed=ok(f"{ctx.author.mention} ha pagato {amount} {CURRENCY} a {member.mention}."))

    @commands.command(name="add")
    @commands.has_permissions(administrator=True)
    async def add_money(self, ctx, member: discord.Member, amount: int):
        await get_user(ctx.guild.id, member.id)
        await inc_user(ctx.guild.id, member.id, {"balance": amount})
        await ctx.send(embed=ok(f"Aggiunti {amount} {CURRENCY} a {member.mention}."))

    @commands.command(name="remove")
    @commands.has_permissions(administrator=True)
    async def remove_money(self, ctx, member: discord.Member, amount: int):
        await get_user(ctx.guild.id, member.id)
        await inc_user(ctx.guild.id, member.id, {"balance": -amount})
        await ctx.send(embed=ok(f"Rimossi {amount} {CURRENCY} a {member.mention}."))

    @commands.command(name="daily")
    async def daily(self, ctx):
        rec = await daily_claims.find_one({"guild_id": ctx.guild.id, "user_id": ctx.author.id})
        now = datetime.now(timezone.utc)
        if rec:
            last = datetime.fromisoformat(rec["last"])
            if now - last < timedelta(hours=20):
                left = timedelta(hours=20) - (now - last)
                h, rem = divmod(int(left.total_seconds()), 3600)
                m = rem // 60
                return await ctx.send(embed=err(f"Torna tra {h}h {m}m."))
        amount = random.randint(200, 500)
        await inc_user(ctx.guild.id, ctx.author.id, {"balance": amount})
        await daily_claims.update_one(
            {"guild_id": ctx.guild.id, "user_id": ctx.author.id},
            {"$set": {"last": now.isoformat()}},
            upsert=True,
        )
        await ctx.send(embed=ok(f"Hai ricevuto {amount} {CURRENCY} giornalieri!"))

    @commands.command(name="work")
    @commands.cooldown(1, 600, commands.BucketType.user)
    async def work(self, ctx):
        jobs = ["programmatore", "artista", "youtuber", "cuoco", "corriere", "tassista"]
        amount = random.randint(80, 250)
        await inc_user(ctx.guild.id, ctx.author.id, {"balance": amount})
        await ctx.send(embed=ok(f"Hai lavorato come **{random.choice(jobs)}** e guadagnato {amount} {CURRENCY}."))

    @commands.command(name="mine")
    @commands.cooldown(1, 300, commands.BucketType.user)
    async def mine(self, ctx):
        u = await get_user(ctx.guild.id, ctx.author.id)
        luck = u.get("luck", 0)
        loot = random.choices(
            ["carbone", "ferro", "oro", "diamante"],
            weights=[50, 30, 15 + luck, 5 + luck // 2],
        )[0]
        value = {"carbone": 30, "ferro": 80, "oro": 200, "diamante": 600}[loot]
        await inc_user(ctx.guild.id, ctx.author.id, {"balance": value})
        await ctx.send(embed=ok(f"⛏️ Hai trovato **{loot}** e guadagnato {value} {CURRENCY}!"))

    @commands.command(name="tris")
    @commands.cooldown(1, 60, commands.BucketType.user)
    async def tris(self, ctx):
        symbols = ["🍒", "🍋", "🍇", "⭐", "💎"]
        roll = [random.choice(symbols) for _ in range(3)]
        line = " | ".join(roll)
        if roll[0] == roll[1] == roll[2]:
            prize = {"🍒": 200, "🍋": 300, "🍇": 500, "⭐": 1000, "💎": 5000}[roll[0]]
            await inc_user(ctx.guild.id, ctx.author.id, {"balance": prize})
            return await ctx.send(embed=ok(f"[ {line} ]\nTRIS! +{prize} {CURRENCY}"))
        await ctx.send(embed=embed(description=f"[ {line} ]\nNessun premio. Riprova!"))

    @commands.command(name="coinflip", aliases=["cf"])
    async def coinflip(self, ctx, side: str, amount: int):
        side = side.lower()
        if side not in ("testa", "croce", "t", "c", "head", "tail"):
            return await ctx.send(embed=err("Scegli `testa` o `croce`."))
        if amount <= 0:
            return await ctx.send(embed=err("Importo non valido."))
        u = await get_user(ctx.guild.id, ctx.author.id)
        if u["balance"] < amount:
            return await ctx.send(embed=err("Fondi insufficienti."))
        chosen = "testa" if side[0] in ("t", "h") else "croce"
        result = random.choice(["testa", "croce"])
        if chosen == result:
            await inc_user(ctx.guild.id, ctx.author.id, {"balance": amount})
            return await ctx.send(embed=ok(f"🪙 {result.upper()}! Hai vinto {amount} {CURRENCY}."))
        await inc_user(ctx.guild.id, ctx.author.id, {"balance": -amount})
        await ctx.send(embed=err(f"🪙 {result.upper()}! Hai perso {amount} {CURRENCY}."))

    @commands.command(name="roulette")
    async def roulette(self, ctx, color: str, amount: int):
        color = color.lower()
        if color not in ("rosso", "nero", "verde", "red", "black", "green"):
            return await ctx.send(embed=err("Scegli `rosso`, `nero` o `verde`."))
        if amount <= 0:
            return await ctx.send(embed=err("Importo non valido."))
        u = await get_user(ctx.guild.id, ctx.author.id)
        if u["balance"] < amount:
            return await ctx.send(embed=err("Fondi insufficienti."))
        map_c = {"red": "rosso", "black": "nero", "green": "verde"}
        color = map_c.get(color, color)
        result = random.choices(["rosso", "nero", "verde"], weights=[18, 18, 1])[0]
        if color == result:
            mult = 14 if color == "verde" else 2
            win = amount * (mult - 1)
            await inc_user(ctx.guild.id, ctx.author.id, {"balance": win})
            return await ctx.send(embed=ok(f"🎰 {result.upper()}! Vinci {amount*mult} {CURRENCY} (x{mult})."))
        await inc_user(ctx.guild.id, ctx.author.id, {"balance": -amount})
        await ctx.send(embed=err(f"🎰 {result.upper()}! Perdi {amount} {CURRENCY}."))

    @commands.command(name="blackjack", aliases=["bj"])
    async def blackjack(self, ctx, amount: int):
        if amount <= 0:
            return await ctx.send(embed=err("Importo non valido."))
        u = await get_user(ctx.guild.id, ctx.author.id)
        if u["balance"] < amount:
            return await ctx.send(embed=err("Fondi insufficienti."))

        def draw():
            return random.randint(1, 11)

        def hand_val(h):
            return sum(h)

        player = [draw(), draw()]
        dealer = [draw(), draw()]

        e = embed(
            title="🃏 Blackjack",
            description=(
                f"Le tue carte: {player} (**{hand_val(player)}**)\n"
                f"Dealer mostra: {dealer[0]}\n\n"
                "Reagisci ✋ per **Stare**, 🃏 per **Hit** (15s)."
            ),
        )
        msg = await ctx.send(embed=e)
        await msg.add_reaction("🃏")
        await msg.add_reaction("✋")

        def check(reaction, user):
            return (
                user == ctx.author
                and str(reaction.emoji) in ("🃏", "✋")
                and reaction.message.id == msg.id
            )

        while hand_val(player) < 21:
            try:
                reaction, _ = await self.bot.wait_for("reaction_add", timeout=15.0, check=check)
            except asyncio.TimeoutError:
                break
            if str(reaction.emoji) == "🃏":
                player.append(draw())
                try:
                    await msg.remove_reaction(reaction, ctx.author)
                except Exception:
                    pass
                await msg.edit(embed=embed(
                    title="🃏 Blackjack",
                    description=f"Le tue carte: {player} (**{hand_val(player)}**)\n"
                                f"Dealer mostra: {dealer[0]}",
                ))
            else:
                break

        while hand_val(dealer) < 17:
            dealer.append(draw())

        pv, dv = hand_val(player), hand_val(dealer)
        if pv > 21 or (dv <= 21 and dv > pv):
            await inc_user(ctx.guild.id, ctx.author.id, {"balance": -amount})
            result = f"Hai perso {amount} {CURRENCY}."
        elif pv == dv:
            result = "Pareggio, nessun trasferimento."
        else:
            await inc_user(ctx.guild.id, ctx.author.id, {"balance": amount})
            result = f"Hai vinto {amount} {CURRENCY}!"
        await ctx.send(embed=embed(
            title="🃏 Blackjack — Risultato",
            description=f"Tu: {player} (**{pv}**)\nDealer: {dealer} (**{dv}**)\n\n{result}",
        ))

    @commands.command(name="leaderboard", aliases=["lb", "top"])
    async def leaderboard(self, ctx):
        cursor = users.find({"guild_id": ctx.guild.id}).sort("balance", -1).limit(10)
        e = embed(title="🏆 Top 10 Ricchi")
        i = 1
        async for u in cursor:
            m = ctx.guild.get_member(u["user_id"])
            name = m.display_name if m else f"User {u['user_id']}"
            e.add_field(name=f"#{i} {name}", value=f"{u.get('balance', 0)} {CURRENCY}", inline=False)
            i += 1
        if i == 1:
            e.description = "Nessuno ha ancora una economia."
        await ctx.send(embed=e)

    @commands.command(name="shop")
    async def shop(self, ctx):
        e = embed(title="🛒 Shop", description="Acquista con `?buy <item>`.")
        for name, meta in SHOP.items():
            e.add_field(name=f"{name} — {meta['price']} {CURRENCY}", value=meta["desc"], inline=False)
        await ctx.send(embed=e)

    @commands.command(name="buy")
    async def buy(self, ctx, item: str, qty: int = 1):
        item = item.lower()
        if item not in SHOP:
            return await ctx.send(embed=err("Item non presente in shop."))
        if qty <= 0:
            return await ctx.send(embed=err("Quantità non valida."))
        cost = SHOP[item]["price"] * qty
        u = await get_user(ctx.guild.id, ctx.author.id)
        if u["balance"] < cost:
            return await ctx.send(embed=err("Fondi insufficienti."))
        inv = _inv_add(u["inventory"], item, qty)
        await update_user(ctx.guild.id, ctx.author.id, {"inventory": inv})
        await inc_user(ctx.guild.id, ctx.author.id, {"balance": -cost})
        await ctx.send(embed=ok(f"Hai comprato {qty}x **{item}** per {cost} {CURRENCY}."))

    @commands.command(name="inventory", aliases=["inv"])
    async def inventory(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        u = await get_user(ctx.guild.id, member.id)
        e = embed(title=f"🎒 Inventario di {member.display_name}")
        if not u["inventory"]:
            e.description = "Vuoto."
        else:
            e.description = "\n".join(f"• **{it['item']}** x{it['qty']}" for it in u["inventory"])
        await ctx.send(embed=e)

    @commands.command(name="openbox", aliases=["open_box", "open"])
    async def openbox(self, ctx):
        u = await get_user(ctx.guild.id, ctx.author.id)
