"""Ticket system with panel & controls."""
import discord
from discord.ext import commands

from ..db import tickets as tickets_col
from ..helpers import embed


TICKET_TOPICS = [
    ("partnership", "🤝 Partnership"),
    ("staff",       "🛡️ Provino Staff"),
    ("segnala",     "🚨 Segnala Utente"),
    ("giveaway",    "🎉 Riscatta Giveaway"),
    ("aiuto",       "❓ Aiuto Generale"),
]


class TicketOpenButton(discord.ui.Button):
    def __init__(self, key: str, label: str):
        super().__init__(style=discord.ButtonStyle.primary, label=label, custom_id=f"ticket_open_{key}")
        self.key = key
        self.label_text = label

    async def callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        user = interaction.user
        existing = await tickets_col.find_one({"guild_id": guild.id, "user_id": user.id, "closed": False})
        if existing:
            ch = guild.get_channel(existing["channel_id"])
            if ch:
                return await interaction.response.send_message(
                    f"Hai già un ticket aperto: {ch.mention}", ephemeral=True
                )
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True),
        }
        name = f"ticket-{self.key}-{user.name}".lower().replace(" ", "-")[:90]
        try:
            ch = await guild.create_text_channel(name, overwrites=overwrites, topic=f"Ticket {self.key} di {user}")
        except discord.Forbidden:
            return await interaction.response.send_message("Permessi insufficienti per creare canali.", ephemeral=True)

        await tickets_col.insert_one({
            "guild_id": guild.id,
            "user_id": user.id,
            "channel_id": ch.id,
            "topic": self.key,
            "claimed_by": None,
            "closed": False,
        })

        e = embed(
            title=self.label_text,
            description=f"Ciao {user.mention}, uno staff ti risponderà a breve.\n\nUsa i pulsanti sotto per gestire il ticket.",
        )
        await ch.send(content=user.mention, embed=e, view=TicketControlView())
        await interaction.response.send_message(f"Ticket creato: {ch.mention}", ephemeral=True)


class TicketPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        for key, label in TICKET_TOPICS:
            self.add_item(TicketOpenButton(key, label))


class AddUserModal(discord.ui.Modal, title="Aggiungi utente al ticket"):
    user_id = discord.ui.TextInput(label="ID utente", placeholder="123456789012345678", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            uid = int(str(self.user_id).strip())
        except Exception:
            return await interaction.response.send_message("ID non valido.", ephemeral=True)
        member = interaction.guild.get_member(uid)
        if not member:
            return await interaction.response.send_message("Utente non trovato nel server.", ephemeral=True)
        await interaction.channel.set_permissions(member, view_channel=True, send_messages=True, read_message_history=True)
        await interaction.response.send_message(f"✅ {member.mention} aggiunto al ticket.")


class TicketControlView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Claim", style=discord.ButtonStyle.success, custom_id="ticket_claim")
    async def claim(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.manage_channels:
            return await interaction.response.send_message("Solo lo staff può fare claim.", ephemeral=True)
        await tickets_col.update_one({"channel_id": interaction.channel.id}, {"$set": {"claimed_by": interaction.user.id}})
        await interaction.response.send_message(f"🛡️ {interaction.user.mention} ha preso in carico il ticket.")

    @discord.ui.button(label="Unclaim", style=discord.ButtonStyle.secondary, custom_id="ticket_unclaim")
    async def unclaim(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.manage_channels:
            return await interaction.response.send_message("Solo lo staff.", ephemeral=True)
        await tickets_col.update_one({"channel_id": interaction.channel.id}, {"$set": {"claimed_by": None}})
        await interaction.response.send_message(f"↩️ {interaction.user.mention} ha rilasciato il ticket.")

    @discord.ui.button(label="Aggiungi utente", style=discord.ButtonStyle.primary, custom_id="ticket_add")
    async def add_user(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.manage_channels:
            return await interaction.response.send_message("Solo lo staff.", ephemeral=True)
        await interaction.response.send_modal(AddUserModal())

    @discord.ui.button(label="Chiudi", style=discord.ButtonStyle.danger, custom_id="ticket_close")
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.manage_channels:
            return await interaction.response.send_message("Solo lo staff.", ephemeral=True)
        await tickets_col.update_one({"channel_id": interaction.channel.id}, {"$set": {"closed": True}})
        await interaction.response.send_message("Chiusura in corso... 🔒")
        try:
            await interaction.channel.delete(reason=f"Chiuso da {interaction.user}")
        except Exception:
            pass

    @discord.ui.button(label="Chiudi con reaction", style=discord.ButtonStyle.danger, custom_id="ticket_close_react")
    async def close_react(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.manage_channels:
            return await interaction.response.send_message("Solo lo staff.", ephemeral=True)
        e = embed(title="Chiudi ticket", description="Reagisci con 🔒 entro 15s per confermare la chiusura.")
        msg = await interaction.channel.send(embed=e)
        await msg.add_reaction("🔒")

        def check(reaction, user):
            return (
                reaction.message.id == msg.id
                and str(reaction.emoji) == "🔒"
                and user.guild_permissions.manage_channels
                and not user.bot
            )

        try:
            await interaction.client.wait_for("reaction_add", timeout=15.0, check=check)
        except Exception:
            return await msg.edit(embed=embed(description="Chiusura annullata."))
        await tickets_col.update_one({"channel_id": interaction.channel.id}, {"$set": {"closed": True}})
        try:
            await interaction.channel.delete(reason=f"Chiuso via reaction da {interaction.user}")
        except Exception:
            pass


class Tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        bot.add_view(TicketPanelView())
        bot.add_view(TicketControlView())

    @commands.command(name="pannelloticket", aliases=["ticketpanel", "panel"])
    @commands.has_permissions(manage_guild=True)
    async def pannelloticket(self, ctx):
        e = embed(
            title="🎫 Centro Ticket",
            description=(
                "Apri un ticket scegliendo un argomento qui sotto.\n\n"
                "• 🤝 **Partnership** — proposte di collaborazione\n"
                "• 🛡️ **Provino Staff** — candidati per lo staff\n"
                "• 🚨 **Segnala Utente** — segnala un comportamento\n"
                "• 🎉 **Riscatta Giveaway** — vinto un giveaway?\n"
                "• ❓ **Aiuto Generale** — qualsiasi altra richiesta"
            ),
        )
        await ctx.send(embed=e, view=TicketPanelView())


async def setup(bot):
    await bot.add_cog(Tickets(bot))
