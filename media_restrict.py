import discord
from discord.ext import commands

# ==================== AYARLAR ====================
ILLEGAL_MEDYA = 1541219393374130269
MEDYA = 1532829033564213298

KURUCU_ROLE = 1529546007635824680
UST_YONETIM_ROLE = 1539167256246747186

ALLOWED_ROLES = [KURUCU_ROLE, UST_YONETIM_ROLE]
MEDIA_CHANNELS = [ILLEGAL_MEDYA, MEDYA]
# =================================================

class MediaRestrict(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        if message.channel.id not in MEDIA_CHANNELS:
            return

        # Yönetim muaf
        if any(r.id in ALLOWED_ROLES for r in message.author.roles):
            return

        # Sadece dosya / link / tepki bırakılsın → normal yazı silinsin
        has_attachment = len(message.attachments) > 0
        has_link = any(word.startswith(("http://", "https://", "www.")) for word in message.content.split())
        has_embed = len(message.embeds) > 0

        # Eğer sadece yazı varsa (dosya/link yoksa) sil
        if not (has_attachment or has_link or has_embed) and message.content.strip():
            try:
                await message.delete()
                await message.channel.send(
                    f"{message.author.mention} Bu kanal **sadece medya** içindir. Yazı yazamazsın!",
                    delete_after=5
                )
            except:
                pass


async def setup(bot: commands.Bot):
    await bot.add_cog(MediaRestrict(bot))