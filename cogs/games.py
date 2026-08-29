"""Fun / game commands."""
import random

import discord
from discord.ext import commands

from helpers import ok, err, embed


KISS_GIFS = [
    "https://media.tenor.com/tGgIZ2u2LrsAAAAC/anime-kiss.gif",
    "https://media.tenor.com/A57S3F7ZuMAAAAC/kiss-anime.gif",
    "https://media.tenor.com/OWmnpbZssI4AAAAC/anime-kiss.gif",
]
HUG_GIFS = [
    "https://media.tenor.com/kCZjTqCKiggAAAAC/hug.gif",
    "https://media.tenor.com/9Iu4bIQ8MYIAAAAC/anime-hug.gif",
    "https://media.tenor.com/kBmdbmYysCUAAAAC/hug-anime.gif",
]
SLAP_GIFS = [
    "https://media.tenor.com/Ws6Dm1ZW_vMAAAAC/anime-slap.gif",
    "https://media.tenor.com/gsRE-XbH04IAAAAC/slap-anime-slap.gif",
]
CLAP_GIFS = [
    "https://media.tenor.com/HZgWLXwVKr0AAAAC/anime-clap.gif",
    "https://media.tenor.com/1r8gDbcMUB4AAAAC/clapping-anime.gif",
]
KILL_GIFS = [
    "https://media.tenor.com/CggkveldsdIAAAAC/anime-kill.gif",
    "https://media.tenor.com/oXFcHwHRUZgAAAAC/anime-death.gif",
]
DANCE_PET_GIFS = [
    "https://media.tenor.com/x8v1oNUOmg4AAAAi/dance-dancing.gif",
    "https://media.tenor.com/GfSW-LMlHDkAAAAi/dog-dance.gif",
    "https://media.tenor.com/rlSTOZeeYtIAAAAi/cat-dance-cat.gif",
    "https://media.tenor.com/QOLoBqZ9YnAAAAAi/cat-cat-dance.gif",
]

MAGIC_8BALL = [
    "Certamente.", "Senza dubbio.", "Sì, decisamente.", "Puoi contarci.",
    "Molto probabile.", "Le prospettive sono buone.", "Sì.", "I segnali indicano di sì.",
    "Risposta poco chiara, riprova.", "Chiedi di nuovo più tardi.",
    "Meglio non dirtelo ora.", "Non posso prevederlo ora.",
    "Non ci contare.", "La mia risposta è no.", "Le mie fonti dicono no.",
    "Le prospettive non sono buone.", "Molto dubbioso.",
]


class NitroView(discord.ui.View):
    def __init__(self, target_id: int):
        super().__init__(timeout=300)
        self.target_id = target_id

    @discord.ui.button(label="🎁 Reclama Nitro", style=discord.ButtonStyle.success, custom_id="nitro_claim")
    async def claim(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.target_id:
            return await interaction.response.send_message("Questo Nitro non è per te 😈", ephemeral=True)
        e = discord.Embed(
            title="😹 Ma quale Nitro!",
            description=f"{interaction.user.mention} sei stato trollato! Ecco a te un balletto:",
            color=0xed4245,
        )
        e.set_image(url=random.choice(DANCE_PET_GIFS))
        button.disabled = True
        button.label = "Trollato ✅"
        await interaction.response.edit_message(embed=e, view=self)


class Games(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="8ball")
    async def eight_ball(self, ctx, *, question: str):
        e = embed(
            title="🎱 Magic 8-Ball",
            description=f"**Domanda:** {question}\n**Risposta:** {random.choice(MAGIC_8BALL)}",
        )
        await ctx.send(embed=e)

    @commands.command(name="say")
    async def say(self, ctx, *, text: str):
        """?say <messaggio>  |  ?say embed | <titolo> | <descrizione>"""
        try:
            await ctx.message.delete()
        except Exception:
            pass
        if text.lower().startswith("embed"):
            parts = [p.strip() for p in text.split("|")]
            if len(parts) >= 3:
                title = parts[1]
                desc = "|".join(parts[2:]).strip()
                return await ctx.send(embed=embed(title=title, description=desc))
            return await ctx.send(embed=err("Formato: `?say embed | Titolo | Descrizione`"))
        await ctx.send(text)

    @commands.command(name="ship")
    async def ship(self, ctx, user1: discord.Member, user2: discord.Member):
        pct = hash((min(user1.id, user2.id), max(user1.id, user2.id))) % 101
        bar = "█" * (pct // 10) + "░" * (10 - pct // 10)
        name = user1.display_name[: len(user1.display_name) // 2] + user2.display_name[len(user2.display_name) // 2:]
        e = embed(
            title="💘 Ship-o-meter",
            description=(
                f"{user1.mention} 💞 {user2.mention}\n"
                f"Compatibilità: **{pct}%**\n`{bar}`\n"
                f"Nome ship: **{name}**"
            ),
        )
        await ctx.send(embed=e)

    @commands.command(name="rendigay", aliases=["gayrate", "howgay"])
    async def rendigay(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        pct = hash(("gay", member.id)) % 101
        bar = "█" * (pct // 10) + "░" * (10 - pct // 10)
        e = embed(
            title="🏳️‍🌈 Gay-o-meter",
            description=f"{member.mention} è gay al **{pct}%**\n`{bar}`",
            color=0xff69b4,
        )
        await ctx.send(embed=e)

    @commands.command(name="rendilesbica", aliases=["rendilesbico", "lesrate"])
    async def rendilesbica(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        pct = hash(("lesbo", member.id)) % 101
        bar = "█" * (pct // 10) + "░" * (10 - pct // 10)
        e = embed(
            title="🏳️‍🌈 Lesbo-o-meter",
            description=f"{member.mention} è lesbica/o al **{pct}%**\n`{bar}`",
            color=0xff69b4,
        )
        await ctx.send(embed=e)

    async def _action(self, ctx, member, gifs, verb):
        if member.id == ctx.author.id:
            return await ctx.send(embed=err(f"Non puoi fare {verb} a te stesso."))
        e = embed(description=f"{ctx.author.mention} {verb} {member.mention}!")
        e.set_image(url=random.choice(gifs))
        await ctx.send(embed=e)

    @commands.command(name="kiss")
    async def kiss(self, ctx, member: discord.Member):
        await self._action(ctx, member, KISS_GIFS, "bacia 💋")

    @commands.command(name="hug")
    async def hug(self, ctx, member: discord.Member):
        await self._action(ctx, member, HUG_GIFS, "abbraccia 🤗")

    @commands.command(name="slap")
    async def slap(self, ctx, member: discord.Member):
        await self._action(ctx, member, SLAP_GIFS, "schiaffeggia 👋")

    @commands.command(name="clap")
    async def clap(self, ctx, member: discord.Member):
        await self._action(ctx, member, CLAP_GIFS, "applaude 👏")

    @commands.command(name="kill")
    async def kill(self, ctx, member: discord.Member):
        await self._action(ctx, member, KILL_GIFS, "elimina ☠️")

    @commands.command(name="nitrodonate", aliases=["nitrogift", "nitro_donate"])
    async def nitrodonate(self, ctx, member: discord.Member):
        e = discord.Embed(
            title="🎁 Hai ricevuto Discord Nitro!",
            description=(
                f"{member.mention}, {ctx.author.mention} ti ha regalato **1 mese di Nitro**!\n"
                "Clicca il pulsante qui sotto per riscattarlo."
            ),
            color=0x5865F2,
        )
        e.set_thumbnail(url="https://images.emojiterra.com/google/android-12l/512px/1f381.png")
        await ctx.send(content=member.mention, embed=e, view=NitroView(member.id))


async def setup(bot):
    await bot.add_cog(Games(bot))
