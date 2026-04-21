import discord
from discord.ext import commands
from db import get_db
import time
import os

TOKEN = os.getenv("TOKEN")

intents = discord.Intents.default()
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ================= VERIFY =================
class Verify(discord.ui.Modal, title="Code"):
    code = discord.ui.TextInput(label="Code")

    async def on_submit(self, interaction: discord.Interaction):

        conn = get_db()
        c = conn.cursor()

        c.execute("SELECT * FROM codes WHERE code=?", (self.code.value,))
        data = c.fetchone()

        if not data:
            return await interaction.response.send_message("❌ invalide", ephemeral=True)

        code, guild_id, role_id, used_by, max_uses, uses, premium, expires_at = data

        if expires_at and time.time() > expires_at:
            return await interaction.response.send_message("⏳ expiré", ephemeral=True)

        if max_uses != -1 and uses >= max_uses:
            return await interaction.response.send_message("❌ utilisé", ephemeral=True)

        # mark used
        c.execute("UPDATE codes SET uses = uses + 1, used_by=? WHERE code=?",
                  (interaction.user.id, self.code.value))

        conn.commit()

        role = interaction.guild.get_role(int(role_id))

        if role:
            await interaction.user.add_roles(role)

        await interaction.response.send_message("✅ OK", ephemeral=True)

        # LOGS
        channel = discord.utils.get(interaction.guild.text_channels, name="logs")
        if channel:
            embed = discord.Embed(
                title="Code utilisé",
                description=f"{interaction.user} a utilisé {self.code.value}",
                color=0x00ff00
            )
            await channel.send(embed=embed)

# ================= VIEW =================
class View(discord.ui.View):
    @discord.ui.button(label="Verify", style=discord.ButtonStyle.green)
    async def v(self, interaction, button):
        await interaction.response.send_modal(Verify())

@bot.event
async def on_ready():
    print(f"Bot ready {bot.user}")
    @bot.event
    global bot_guild_ids
    bot_guild_ids = [g.id for g in bot.guilds]

@bot.tree.command(name="panel")
async def panel(interaction: discord.Interaction):
    await interaction.response.send_message("verify", view=View())

bot.run(TOKEN)
