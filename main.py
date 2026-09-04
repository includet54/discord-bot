import discord
from discord.ext import commands
from discord import app_commands
from config import TOKEN
import os

GUILD_ID = 1529545898294509589  # <-- kendi sunucu ID'ni buraya yaz

intents = discord.Intents.all()

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        for filename in os.listdir("./cogs"):
            if filename.endswith(".py"):
                try:
                    await self.load_extension(f"cogs.{filename[:-3]}")
                    print(f"Yüklendi: {filename}")
                except Exception as e:
                    print(f"Hata: {filename} → {e}")

        # Kalıcı butonlar - bot yeniden başlasa bile butonlar çalışsın diye
                from cogs.registration import KayitButonView, OnayView
        from cogs.tickets import TicketPanelView, CloseTicketView
        from cogs.market import MarketView, TotemView   # 👈 EKLE

        self.add_view(KayitButonView())
        self.add_view(OnayView())
        self.add_view(TicketPanelView())
        self.add_view(CloseTicketView())
        self.add_view(MarketView())    # 👈 EKLE
        self.add_view(TotemView())     # 👈 EKLE

        guild = discord.Object(id=GUILD_ID)
        self.tree.copy_global_to(guild=guild)
        synced = await self.tree.sync(guild=guild)
        print(f"{len(synced)} slash komut senkronize edildi.")

bot = MyBot()

@bot.event
async def on_ready():
    print(f"Bot basariyla giris yapti: {bot.user}")
    print("------")

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    import traceback
    traceback.print_exception(type(error), error, error.__traceback__)
    msg = "Komut çalışırken bir hata oluştu."
    try:
        if interaction.response.is_done():
            await interaction.followup.send(msg, ephemeral=True)
        else:
            await interaction.response.send_message(msg, ephemeral=True)
    except:
        pass

bot.run(TOKEN)