import discord
from discord.ext import commands
from discord import app_commands
import re

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ----------- PREFIX KOMUT -----------
    @commands.command(name="temizle")
    @commands.has_permissions(manage_messages=True)
    async def temizle(self, ctx, miktar: int = 5):
        if miktar < 1 or miktar > 100:
            return await ctx.send("1-100 arası sayı gir.", delete_after=5)
        await ctx.channel.purge(limit=miktar + 1)
        await ctx.send(f"{miktar} mesaj silindi.", delete_after=3)

    # ----------- SLASH KOMUTLAR -----------
    @app_commands.command(name="kick", description="Üyeyi sunucudan atar")
    @app_commands.describe(uye="Atılacak üye", sebep="Sebep")
    async def kick(self, interaction: discord.Interaction, uye: discord.Member, sebep: str = "Sebep belirtilmedi"):
        if not interaction.user.guild_permissions.kick_members:
            return await interaction.response.send_message("Yetkin yok.", ephemeral=True)
        await uye.kick(reason=sebep)
        await interaction.response.send_message(f"{uye.mention} atıldı.\n**Sebep:** {sebep}")

    @app_commands.command(name="ban", description="Üyeyi yasaklar")
    @app_commands.describe(uye="Yasaklanacak üye", sebep="Sebep")
    async def ban(self, interaction: discord.Interaction, uye: discord.Member, sebep: str = "Sebep belirtilmedi"):
        if not interaction.user.guild_permissions.ban_members:
            return await interaction.response.send_message("Yetkin yok.", ephemeral=True)
        await uye.ban(reason=sebep)
        await interaction.response.send_message(f"{uye.mention} yasaklandı.\n**Sebep:** {sebep}")

    @app_commands.command(name="timeout", description="Üyeye timeout uygular")
    @app_commands.describe(uye="Üye", dakika="Kaç dakika", sebep="Sebep")
    async def timeout(self, interaction: discord.Interaction, uye: discord.Member, dakika: int, sebep: str = "Sebep belirtilmedi"):
        if not interaction.user.guild_permissions.moderate_members:
            return await interaction.response.send_message("Yetkin yok.", ephemeral=True)
        if dakika < 1 or dakika > 40320:
            return await interaction.response.send_message("1 ile 40320 arasında sayı gir.", ephemeral=True)
        bitis = discord.utils.utcnow() + discord.timedelta(minutes=dakika)
        await uye.timeout(bitis, reason=sebep)
        await interaction.response.send_message(f"{uye.mention} **{dakika} dakika** timeout yedi.\n**Sebep:** {sebep}")

    @app_commands.command(name="kanal-ac", description="Kategori içinde kanal oluşturur")
    @app_commands.describe(kategori="Kategori seç", isim="Kanalın adı")
    async def kanal_ac(self, interaction: discord.Interaction, kategori: discord.CategoryChannel, isim: str):
        if not interaction.user.guild_permissions.manage_channels:
            return await interaction.response.send_message("Yetkin yok.", ephemeral=True)
        kanal = await kategori.create_text_channel(name=isim)
        await interaction.response.send_message(f"Kanal oluşturuldu: {kanal.mention}")

    @app_commands.command(name="kanal-kapa", description="Kanal linkiyle kanalı siler")
    @app_commands.describe(kanal_linki="Silinecek kanalın linki")
    async def kanal_kapa(self, interaction: discord.Interaction, kanal_linki: str):
        if not interaction.user.guild_permissions.manage_channels:
            return await interaction.response.send_message("Yetkin yok.", ephemeral=True)
        eslesme = re.search(r"/channels/\d+/(\d+)", kanal_linki)
        if not eslesme:
            return await interaction.response.send_message("Geçersiz kanal linki.", ephemeral=True)
        kanal = interaction.guild.get_channel(int(eslesme.group(1)))
        if kanal is None:
            return await interaction.response.send_message("Kanal bulunamadı.", ephemeral=True)
        await kanal.delete()
        await interaction.response.send_message(f"**{kanal.name}** kanalı silindi.")

    @app_commands.command(name="mesaj-gonder", description="Bir kullanıcıya DM gönderir")
    @app_commands.describe(uye="Mesaj gönderilecek kişi", mesaj="Gönderilecek mesaj")
    async def mesaj_gonder(self, interaction: discord.Interaction, uye: discord.Member, mesaj: str):
        if not interaction.user.guild_permissions.manage_messages:
            return await interaction.response.send_message("Yetkin yok.", ephemeral=True)
        try:
            await uye.send(mesaj)
            await interaction.response.send_message(f"{uye.mention} kişisine DM gönderildi.", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("Bu kullanıcıya DM gönderilemiyor.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Moderation(bot))