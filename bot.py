import discord
from discord.ext import commands, tasks
import sqlite3
import time
import os
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("TOKEN")

intents = discord.Intents.default()
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ===== DB =====
conn = sqlite3.connect("codes.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS codes (
    code TEXT PRIMARY KEY,
    role_id INTEGER,
    max_uses INTEGER,
    uses INTEGER DEFAULT 0,
    expires_at INTEGER,
    bound_user INTEGER
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS roles (
    role_id INTEGER PRIMARY KEY,
    role_name TEXT
)
""")

conn.commit()

# ===== SYNC ROLES =====
@tasks.loop(minutes=5)
async def sync_roles():
    for guild in bot.guilds:
        for role in guild.roles:
            cursor.execute(
                "INSERT OR REPLACE INTO roles VALUES (?, ?)",
                (role.id, role.name)
            )
    conn.commit()

# ===== VERIFY =====
class VerifyModal(discord.ui.Modal, title="Vérification"):
    code = discord.ui.TextInput(label="Code")

    async def on_submit(self, interaction: discord.Interaction):
        user_code = self.code.value.upper()
        user_id = interaction.user.id

        cursor.execute(
            "SELECT role_id, max_uses, uses, expires_at, bound_user FROM codes WHERE code=?",
            (user_code,)
        )
        data = cursor.fetchone()

        if not data:
            return await interaction.response.send_message("❌ Code invalide", ephemeral=True)

        role_id, max_uses, uses, expires_at, bound_user = data

        # expiration
        if expires_at and time.time() > expires_at:
            return await interaction.response.send_message("⏳ Code expiré", ephemeral=True)

        # anti leak
        if bound_user and bound_user != user_id:
            return await interaction.response.send_message("❌ Code non autorisé", ephemeral=True)

        # limite
        if max_uses != -1 and uses >= max_uses:
            return await interaction.response.send_message("❌ Code déjà utilisé", ephemeral=True)

        cursor.execute("UPDATE codes SET uses = uses + 1 WHERE code=?", (user_code,))
        conn.commit()

        role = interaction.guild.get_role(role_id)
        if role:
            await interaction.user.add_roles(role)

        await interaction.response.send_message("✅ Vérifié !", ephemeral=True)

class VerifyView(discord.ui.View):
    @discord.ui.button(label="Se vérifier", style=discord.ButtonStyle.green)
    async def verify(self, interaction: discord.Interaction, button):
        await interaction.response.send_modal(VerifyModal())

# ===== COMMAND =====
@bot.tree.command(name="panel", description="Panel vérification")
async def panel(interaction: discord.Interaction):
    await interaction.response.send_message("Clique 👇", view=VerifyView())

@bot.event
async def on_ready():
    sync_roles.start()
    print("Bot prêt")

bot.run(TOKEN)
