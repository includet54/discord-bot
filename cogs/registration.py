import discord
from discord.ext import commands
from discord import app_commands
import re
import aiohttp

# ============================
# BURAYA KENDİ ID'LERİNİ YAZ
# ============================
KAYIT_KANAL_ID = 1532831582753128530      # Kayıt butonunun olacağı kanal
ONAY_KANAL_ID = 1532828473972752555       # Onaylama kanalı
UYE_ROL_ID = 1533908873772273715          # Onaylanınca verilecek rol

YETKILI_ROL_IDLERI = [
    1529546007635824680,  # KURUCU
    1539167256246747186,  # ÜST YÖNETİM
    1534798061845483694,  # YÖNETİCİ
    1537934087166369812,  # YÖNETİM EKİBİ
]
# ============================


def yetkili_mi(member: discord.Member) -> bool:
    if member.guild_permissions.administrator:
        return True
    return any(rol.id in YETKILI_ROL_IDLERI for rol in member.roles)


async def roblox_kullanici_adi_al(link: str):
    """Roblox profil linkinden kullanıcı adını çeker. Bulamazsa None döner."""
    eslesme = re.search(r"/users/(\d+)", link)
    if not eslesme:
        return None
    user_id = eslesme.group(1)
    url = f"https://users.roblox.com/v1/users/{user_id}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                return data.get("name")
    except Exception:
        return None


class KayitModal(discord.ui.Modal, title="📋 Kayıt Formu"):
    gercek_ad = discord.ui.TextInput(
        label="Gerçek adın nedir?",
        placeholder="Örn: Ahmet Yılmaz",
        max_length=50,
        required=True,
    )
    roblox_link = discord.ui.TextInput(
        label="Roblox Profil Linkini yapıştır",
        placeholder="https://www.roblox.com/users/123456789/profile",
        max_length=200,
        required=True,
    )

    async def on_submit(self, interaction: discord.Interaction):
        onay_kanal = interaction.guild.get_channel(ONAY_KANAL_ID)
        if onay_kanal is None:
            return await interaction.response.send_message(
                "Onaylama kanalı bulunamadı, yöneticiye haber ver.", ephemeral=True
            )

        embed = discord.Embed(
            title="🆕 Yeni Kayıt Başvurusu",
            color=discord.Color.blurple(),
        )
        embed.add_field(name="Discord Kullanıcı", value=f"{interaction.user.mention}", inline=False)
        embed.add_field(name="Gerçek Adı", value=self.gercek_ad.value, inline=False)
        embed.add_field(name="Roblox Profil Linki", value=self.roblox_link.value, inline=False)
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.set_footer(text=f"ID:{interaction.user.id}")
        embed.timestamp = discord.utils.utcnow()

        await onay_kanal.send(embed=embed, view=OnayView())

        await interaction.response.send_message(
            "✅ Kayıt başvurun alındı! Yetkililer en kısa sürede inceleyecek.", ephemeral=True
        )


class KayitButonView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="✅ Kayıt Ol", style=discord.ButtonStyle.green, custom_id="kayit_ol_buton")
    async def kayit_ol(self, interaction: discord.Interaction, button: discord.ui.Button):
        if UYE_ROL_ID in [rol.id for rol in interaction.user.roles]:
            return await interaction.response.send_message("Zaten kayıtlısın!", ephemeral=True)
        await interaction.response.send_modal(KayitModal())


class RedSebepModal(discord.ui.Modal, title="❌ Reddetme Sebebi"):
    sebep = discord.ui.TextInput(
        label="Reddetme sebebi",
        style=discord.TextStyle.paragraph,
        placeholder="Örn: Roblox linki geçersiz.",
        max_length=300,
        required=True,
    )

    def __init__(self, hedef_kullanici_id: int, orijinal_mesaj: discord.Message):
        super().__init__()
        self.hedef_kullanici_id = hedef_kullanici_id
        self.orijinal_mesaj = orijinal_mesaj

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        uye = guild.get_member(self.hedef_kullanici_id)

        dm_gonderildi = True
        if uye:
            try:
                await uye.send(
                    f"❌ **{guild.name}** sunucusundaki kayıt başvurun reddedildi.\n**Sebep:** {self.sebep.value}"
                )
            except discord.Forbidden:
                dm_gonderildi = False

        embed = self.orijinal_mesaj.embeds[0]
        yeni_embed = embed.copy()
        yeni_embed.add_field(
            name="Sonuç",
            value=f"❌ **Reddedildi** — {interaction.user.mention}\n**Sebep:** {self.sebep.value}",
            inline=False,
        )
        yeni_embed.color = discord.Color.red()

        await self.orijinal_mesaj.edit(embed=yeni_embed, view=None)

        ek_bilgi = "" if dm_gonderildi else "\n⚠️ Kullanıcıya DM gönderilemedi (DM'leri kapalı olabilir)."
        await interaction.response.send_message(f"Başvuru reddedildi.{ek_bilgi}", ephemeral=True)


class OnayView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="ONAYLA", style=discord.ButtonStyle.green, custom_id="kayit_onayla")
    async def onayla(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not yetkili_mi(interaction.user):
            return await interaction.response.send_message("Bu işlemi yapma yetkin yok.", ephemeral=True)

        embed = interaction.message.embeds[0]
        footer_text = embed.footer.text
        try:
            hedef_id = int(footer_text.split("ID:")[1])
        except Exception:
            return await interaction.response.send_message("Kullanıcı ID bulunamadı.", ephemeral=True)

        guild = interaction.guild
        uye = guild.get_member(hedef_id)
        if uye is None:
            return await interaction.response.send_message("Kullanıcı sunucuda bulunamadı (ayrılmış olabilir).", ephemeral=True)

        gercek_ad = embed.fields[1].value
        roblox_link = embed.fields[2].value

        rol = guild.get_role(UYE_ROL_ID)
        if rol:
            try:
                await uye.add_roles(rol, reason="Kayıt onaylandı")
            except discord.Forbidden:
                pass

        roblox_ad = await roblox_kullanici_adi_al(roblox_link)
        if roblox_ad is None:
            roblox_ad = "RobloxKullanıcı"

        yeni_nick = f"{gercek_ad} | {roblox_ad}"[:32]
        try:
            await uye.edit(nick=yeni_nick, reason="Kayıt onaylandı")
        except discord.Forbidden:
            pass

        try:
            await uye.send(f"✅ **{guild.name}** sunucusundaki kayıt başvurun onaylandı! Hoş geldin 🎉")
        except discord.Forbidden:
            pass

        yeni_embed = embed.copy()
        yeni_embed.add_field(
            name="Sonuç",
            value=f"✅ **Onaylandı** — {interaction.user.mention}",
            inline=False,
        )
        yeni_embed.color = discord.Color.green()

        await interaction.message.edit(embed=yeni_embed, view=None)
        await interaction.response.send_message("Kullanıcı onaylandı ve rol verildi.", ephemeral=True)

    @discord.ui.button(label="REDDET", style=discord.ButtonStyle.red, custom_id="kayit_reddet")
    async def reddet(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not yetkili_mi(interaction.user):
            return await interaction.response.send_message("Bu işlemi yapma yetkin yok.", ephemeral=True)

        embed = interaction.message.embeds[0]
        footer_text = embed.footer.text
        try:
            hedef_id = int(footer_text.split("ID:")[1])
        except Exception:
            return await interaction.response.send_message("Kullanıcı ID bulunamadı.", ephemeral=True)

        await interaction.response.send_modal(RedSebepModal(hedef_id, interaction.message))


class Registration(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="kayit-panel", description="Kayıt panelini gönderir")
    async def kayit_panel(self, interaction: discord.Interaction):
        if not yetkili_mi(interaction.user):
            return await interaction.response.send_message("Yetkin yok.", ephemeral=True)

        embed = discord.Embed(
            title="📋 Kayıt Sistemi",
            description="Sunucumuza kayıt olmak için aşağıdaki butona tıkla ve formu doldur.",
            color=discord.Color.green(),
        )
        await interaction.channel.send(embed=embed, view=KayitButonView())
        await interaction.response.send_message("Panel gönderildi.", ephemeral=True)


async def setup(bot):
    await bot.add_cog(Registration(bot))
