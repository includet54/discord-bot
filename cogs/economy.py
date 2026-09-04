
import discord
from discord.ext import commands
from discord import app_commands
import json, os, random

DATA_FILE = "data/economy.json"

def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data = load_data()

    def get_balance(self, user_id):
        return self.data.setdefault(str(user_id), {"cüzdan": 0, "banka": 0})

    @app_commands.command(name="bakiye", description="Bakiyeni gösterir")
    async def bakiye(self, interaction: discord.Interaction):
        b = self.get_balance(interaction.user.id)
        save_data(self.data)
        await interaction.response.send_message(
            f"💰 Cüzdan: **{b['cüzdan']}**\n🏦 Banka: **{b['banka']}**"
        )

    @app_commands.command(name="calis", description="Çalışıp para kazan")
    async def calis(self, interaction: discord.Interaction):
        kazanc = random.randint(50, 200)
        b = self.get_balance(interaction.user.id)
        b["cüzdan"] += kazanc
        save_data(self.data)
        await interaction.response.send_message(f"Çalıştın ve **{kazanc}** kazandın!")

    @app_commands.command(name="para-ver", description="Başka birine para gönder")
    @app_commands.describe(uye="Kime göndereceksin", miktar="Ne kadar")
    async def para_ver(self, interaction: discord.Interaction, uye: discord.Member, miktar: int):
        gonderen = self.get_balance(interaction.user.id)
        alan = self.get_balance(uye.id)
        if miktar <= 0:
            return await interaction.response.send_message("Geçerli bir miktar gir.", ephemeral=True)
        if gonderen["cüzdan"] < miktar:
            return await interaction.response.send_message("Yeterli paran yok.", ephemeral=True)
        gonderen["cüzdan"] -= miktar
        alan["cüzdan"] += miktar
        save_data(self.data)
        await interaction.response.send_message(f"{uye.mention} kişisine **{miktar}** gönderildi.")

async def setup(bot):
    await bot.add_cog(Economy(bot))
