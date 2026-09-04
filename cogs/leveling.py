import discord
from discord.ext import commands
import json, os

DATA_FILE = "data/levels.json"

def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

class Leveling(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data = load_data()

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return
        uid = str(message.author.id)
        user = self.data.setdefault(uid, {"xp": 0, "level": 1})
        user["xp"] += 5

        gerekli_xp = user["level"] * 100
        if user["xp"] >= gerekli_xp:
            user["level"] += 1
            user["xp"] = 0
            await message.channel.send(f"🎉 {message.author.mention} seviye **{user['level']}** oldu!")

        save_data(self.data)

    @discord.app_commands.command(name="seviye", description="Seviyeni gösterir")
    async def seviye(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        user = self.data.setdefault(uid, {"xp": 0, "level": 1})
        await interaction.response.send_message(
            f"📊 Seviye: **{user['level']}** | XP: **{user['xp']}/{user['level']*100}**"
        )

async def setup(bot):
    await bot.add_cog(Leveling(bot))
