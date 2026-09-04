import discord
from discord.ext import commands
from discord import app_commands
import json, os

DATA_DIR = "data"
BAKIYE_FILE = os.path.join(DATA_DIR, "bakiye.json")
ENVANTER_FILE = os.path.join(DATA_DIR, "envanter.json")
PENDING_FILE = os.path.join(DATA_DIR, "pending_kills.json")

GUILD_ID = 1529545898294509589

UYE_ROL_ID = 1533908873772273715
YONETIM_ROL_IDLERI = [
    1529546007635824680,  # KURUCU
    1539167256246747186,  # ÜST YÖNETİM
    1534798061845483694,  # YÖNETİCİ
    1537934087166369812,  # YÖNETİM EKİBİ
]
KURUCU_ROL_ID = 1529546007635824680

OLU_ROL_ID = 1544777693030125720
KATIL_ROL_ID = 1544778370523332670

OLAYLAR_KANAL_ID = 1544760160042356828

BASLANGIC_PARA = 1000
OLDURME_ODULU = 10000

ESYALAR = {
    "biçak": {"isim": "Bıçak", "emoji": "🗡️", "fiyat": 800},
    "totem": {"isim": "Ölümsüzlük Totemi", "emoji": "✝️", "fiyat": 1000},
    "kit": {"isim": "Yardım Kiti", "emoji": "❤️‍🩹", "fiyat": 500},
    "zirh": {"isim": "Demir Zırh", "emoji": "🪖", "fiyat": 3000},
    "dokunulmazlik": {"isim": "Dokunulmazlık", "emoji": "⛔", "fiyat": 100000},
}


def yukle(dosya):
    if not os.path.exists(dosya):
        return {}
    with open(dosya, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}


def kaydet(dosya, data):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(dosya, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def para_formatla(miktar):
    return f"{miktar:,}".replace(",", ".")


def yetkili_mi(member: discord.Member) -> bool:
    if member.guild_permissions.administrator:
        return True
    return any(r.id in YONETIM_ROL_IDLERI for r in member.roles)


def kurucu_mu(member: discord.Member) -> bool:
    if member.guild_permissions.administrator:
        return True
    return any(r.id == KURUCU_ROL_ID for r in member.roles)


def ekonomi_kullanabilir_mi(member: discord.Member) -> bool:
    if any(r.id == OLU_ROL_ID for r in member.roles):
        return False
    if yetkili_mi(member):
        return True
    return any(r.id == UYE_ROL_ID for r in member.roles)


class MarketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def satin_al(self, interaction: discord.Interaction, item_key: str):
        cog = interaction.client.get_cog("Market")
        if cog:
            await cog.esya_satin_al(interaction, item_key)

    @discord.ui.button(label="Bıçak - 800₺", emoji="🗡️", style=discord.ButtonStyle.gray, custom_id="market_buy_biçak")
    async def buy_knife(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.satin_al(interaction, "biçak")

    @discord.ui.button(label="Ölümsüzlük Totemi - 1000₺", emoji="✝️", style=discord.ButtonStyle.gray, custom_id="market_buy_totem")
    async def buy_totem(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.satin_al(interaction, "totem")

    @discord.ui.button(label="Yardım Kiti - 500₺", emoji="❤️‍🩹", style=discord.ButtonStyle.gray, custom_id="market_buy_kit")
    async def buy_kit(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.satin_al(interaction, "kit")

    @discord.ui.button(label="Demir Zırh - 3000₺", emoji="🪖", style=discord.ButtonStyle.gray, custom_id="market_buy_zirh")
    async def buy_zirh(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.satin_al(interaction, "zirh")

    @discord.ui.button(label="Dokunulmazlık - 100000₺", emoji="⛔", style=discord.ButtonStyle.gray, custom_id="market_buy_dokunulmazlik")
    async def buy_dok(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.satin_al(interaction, "dokunulmazlik")


class TotemView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🩸 Totemi kullan ve Canlan", style=discord.ButtonStyle.green, custom_id="totem_kullan_buton")
    async def totem_kullan(self, interaction: discord.Interaction, button: discord.ui.Button):
        cog = interaction.client.get_cog("Market")
        if cog:
            await cog.totem_karar_ver(interaction, kullan=True)

    @discord.ui.button(label="☠️ Ölümü kabullen", style=discord.ButtonStyle.red, custom_id="totem_kabullen_buton")
    async def totem_kabullen(self, interaction: discord.Interaction, button: discord.ui.Button):
        cog = interaction.client.get_cog("Market")
        if cog:
            await cog.totem_karar_ver(interaction, kullan=False)


class Market(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bakiye = yukle(BAKIYE_FILE)
        self.envanter = yukle(ENVANTER_FILE)
        self.pending = yukle(PENDING_FILE)

    # ---------- Yardımcı fonksiyonlar ----------
    def bakiye_al(self, uid):
        uid = str(uid)
        if uid not in self.bakiye:
            self.bakiye[uid] = BASLANGIC_PARA
            kaydet(BAKIYE_FILE, self.bakiye)
        return self.bakiye[uid]

    def bakiye_ayarla(self, uid, miktar):
        self.bakiye[str(uid)] = max(0, miktar)
        kaydet(BAKIYE_FILE, self.bakiye)

    def envanter_al(self, uid):
        uid = str(uid)
        return self.envanter.setdefault(uid, {})

    def esya_ekle(self, uid, key, adet=1):
        env = self.envanter_al(uid)
        env[key] = env.get(key, 0) + adet
        kaydet(ENVANTER_FILE, self.envanter)

    def esya_sahibi_mi(self, uid, key):
        env = self.envanter_al(uid)
        return env.get(key, 0) > 0

    def esya_sil(self, uid, key, adet=1):
        env = self.envanter_al(uid)
        if env.get(key, 0) < adet:
            return False
        env[key] -= adet
        if env[key] <= 0:
            del env[key]
        kaydet(ENVANTER_FILE, self.envanter)
        return True

    async def olay_bildir(self, guild, saldiran, kisi, aciklama):
        kanal = guild.get_channel(OLAYLAR_KANAL_ID)
        if kanal is None:
            return
        embed = discord.Embed(title="🔫 Katliam Olayı", description=aciklama, color=discord.Color.dark_red())
        embed.add_field(name="Saldıran", value=saldiran.mention, inline=True)
        embed.add_field(name="Mağdur", value=kisi.mention, inline=True)
        embed.timestamp = discord.utils.utcnow()
        await kanal.send(embed=embed)

    async def olumu_uygula(self, guild, saldiran, kisi):
        olu_rol = guild.get_role(OLU_ROL_ID)
        katil_rol = guild.get_role(KATIL_ROL_ID)

        if olu_rol:
            try:
                await kisi.add_roles(olu_rol, reason="Katledildi")
            except discord.Forbidden:
                pass

        rol_verildi = False
        if katil_rol and katil_rol not in saldiran.roles:
            try:
                await saldiran.add_roles(katil_rol, reason="Katliam yaptı")
                rol_verildi = True
            except discord.Forbidden:
                pass

        self.bakiye_ayarla(saldiran.id, self.bakiye_al(saldiran.id) + OLDURME_ODULU)

        aciklama = (
            f"☠️ {kisi.mention} hiçbir korumaya sahip değildi ve **{saldiran.mention}** tarafından katledildi.\n"
            f"💰 {saldiran.mention} hesabına **{para_formatla(OLDURME_ODULU)}₺** yatırıldı."
        )
        if rol_verildi:
            aciklama += f"\n🏷️ {saldiran.mention} artık **Katil** rolüne sahip."

        await self.olay_bildir(guild, saldiran, kisi, aciklama)

    # ---------- Listener'lar ----------
    @commands.Cog.listener()
    async def on_member_join(self, member):
        if member.bot:
            return
        self.bakiye_al(member.id)

    @commands.Cog.listener()
    async def on_ready(self):
        guild = self.bot.get_guild(GUILD_ID)
        if guild is None:
            return
        for member in guild.members:
            if member.bot:
                continue
            self.bakiye_al(member.id)

    # ---------- Para komutları ----------
    @app_commands.command(name="param", description="Bakiyeni gösterir")
    async def param(self, interaction: discord.Interaction):
        if not ekonomi_kullanabilir_mi(interaction.user):
            return await interaction.response.send_message("Bu komutu kullanma yetkin yok.", ephemeral=True)
        bakiye = self.bakiye_al(interaction.user.id)
        embed = discord.Embed(title="💰 Bakiyen", description=f"**{para_formatla(bakiye)}₺**", color=discord.Color.gold())
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="para-gonder", description="Başka bir kişiye para gönderir")
    @app_commands.describe(miktar="Gönderilecek miktar", kisi="Kime gönderilecek")
    async def para_gonder(self, interaction: discord.Interaction, miktar: int, kisi: discord.Member):
        gonderen = interaction.user
        if not ekonomi_kullanabilir_mi(gonderen):
            return await interaction.response.send_message("Bu komutu kullanma yetkin yok.", ephemeral=True)
        if kisi.id == gonderen.id:
            return await interaction.response.send_message("Kendine para gönderemezsin.", ephemeral=True)
        if miktar <= 0:
            return await interaction.response.send_message("Geçerli bir miktar gir.", ephemeral=True)
        gonderen_bakiye = self.bakiye_al(gonderen.id)
        if gonderen_bakiye < miktar:
            return await interaction.response.send_message("Yeterli bakiyen yok.", ephemeral=True)
        self.bakiye_ayarla(gonderen.id, gonderen_bakiye - miktar)
        self.bakiye_ayarla(kisi.id, self.bakiye_al(kisi.id) + miktar)
        await interaction.response.send_message(f"✅ {kisi.mention} kişisine **{para_formatla(miktar)}₺** gönderildi.")

    @app_commands.command(name="para-ekle", description="[KURUCU] Bir kişiye para ekler")
    @app_commands.describe(miktar="Eklenecek miktar", kisi="Kime eklenecek")
    async def para_ekle(self, interaction: discord.Interaction, miktar: int, kisi: discord.Member):
        if not kurucu_mu(interaction.user):
            return await interaction.response.send_message("Bu komutu kullanma yetkin yok.", ephemeral=True)
        if miktar <= 0:
            return await interaction.response.send_message("Geçerli bir miktar gir.", ephemeral=True)
        self.bakiye_ayarla(kisi.id, self.bakiye_al(kisi.id) + miktar)
        await interaction.response.send_message(f"✅ {kisi.mention} kişisine **{para_formatla(miktar)}₺** eklendi.")

    @app_commands.command(name="para-al", description="[KURUCU] Bir kişiden para siler")
    @app_commands.describe(miktar="Silinecek miktar", kisi="Kimden silinecek")
    async def para_al(self, interaction: discord.Interaction, miktar: int, kisi: discord.Member):
        if not kurucu_mu(interaction.user):
            return await interaction.response.send_message("Bu komutu kullanma yetkin yok.", ephemeral=True)
        if miktar <= 0:
            return await interaction.response.send_message("Geçerli bir miktar gir.", ephemeral=True)
        yeni = max(0, self.bakiye_al(kisi.id) - miktar)
        self.bakiye_ayarla(kisi.id, yeni)
        await interaction.response.send_message(f"✅ {kisi.mention} kişisinden **{para_formatla(miktar)}₺** silindi.")

    # ---------- Market ----------
    @app_commands.command(name="market-arayuz", description="Market arayüzünü DM olarak açar")
    async def market_arayuz(self, interaction: discord.Interaction):
        if not ekonomi_kullanabilir_mi(interaction.user):
            return await interaction.response.send_message("Bu komutu kullanma yetkin yok.", ephemeral=True)
        embed = discord.Embed(
            title="🛒 Market",
            description="Satın almak istediğin eşyayı seç:\n\n" + "\n".join(
                f"{v['emoji']} **{v['isim']}** — {para_formatla(v['fiyat'])}₺" for v in ESYALAR.values()
            ),
            color=discord.Color.blue(),
        )
        embed.set_footer(text=f"Bakiyen: {para_formatla(self.bakiye_al(interaction.user.id))}₺")
        try:
            await interaction.user.send(embed=embed, view=MarketView())
            await interaction.response.send_message("📩 Market arayüzü DM olarak gönderildi.", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("DM'lerin kapalı olduğu için market arayüzü gönderilemedi.", ephemeral=True)

    async def esya_satin_al(self, interaction: discord.Interaction, key: str):
        guild = self.bot.get_guild(GUILD_ID)
        member = guild.get_member(interaction.user.id) if guild else None
        if member and not ekonomi_kullanabilir_mi(member):
            return await interaction.response.send_message("Bu işlemi yapma yetkin yok.", ephemeral=True)

        esya = ESYALAR[key]
        bakiye = self.bakiye_al(interaction.user.id)
        if bakiye < esya["fiyat"]:
            return await interaction.response.send_message(
                f"❌ Yeterli bakiyen yok. ({para_formatla(esya['fiyat'])}₺ gerekli)", ephemeral=True
            )

        self.bakiye_ayarla(interaction.user.id, bakiye - esya["fiyat"])
        self.esya_ekle(interaction.user.id, key, 1)

        await interaction.response.send_message(
            f"✅ {esya['emoji']} **{esya['isim']}** satın alındı! Yeni bakiyen: **{para_formatla(self.bakiye_al(interaction.user.id))}₺**",
            ephemeral=True,
        )

    # ---------- Envanter ----------
    @app_commands.command(name="envanter", description="Bir kişinin envanterini gösterir")
    @app_commands.describe(kisi="Envanteri görüntülenecek kişi")
    async def envanter(self, interaction: discord.Interaction, kisi: discord.Member):
        if not ekonomi_kullanabilir_mi(interaction.user):
            return await interaction.response.send_message("Bu komutu kullanma yetkin yok.", ephemeral=True)
        env = self.envanter_al(kisi.id)
        if not env:
            aciklama = "Envanterde hiç eşya yok."
        else:
            satirlar = []
            for key, adet in env.items():
                esya = ESYALAR.get(key)
                if esya:
                    satirlar.append(f"{esya['emoji']} {esya['isim']} — **{adet}** adet")
            aciklama = "\n".join(satirlar)
        embed = discord.Embed(title=f"🎒 {kisi.display_name} — Envanter", description=aciklama, color=discord.Color.orange())
        embed.set_thumbnail(url=kisi.display_avatar.url)
        await interaction.response.send_message(embed=embed)

    # ---------- Katliam sistemi ----------
    @app_commands.command(name="katliam-yap", description="Bir kişiyi öldürmeye çalışır (Bıçak gerekir)")
    @app_commands.describe(kisi="Öldürmek istediğin kişi")
    async def katliam_yap(self, interaction: discord.Interaction, kisi: discord.Member):
        saldiran = interaction.user
        if not ekonomi_kullanabilir_mi(saldiran):
            return await interaction.response.send_message("Bu komutu kullanma yetkin yok.", ephemeral=True)
        if kisi.id == saldiran.id:
            return await interaction.response.send_message("Kendini öldüremezsin.", ephemeral=True)
        if any(r.id == OLU_ROL_ID for r in kisi.roles):
            return await interaction.response.send_message(f"{kisi.mention} zaten ölü.", ephemeral=True)
        if not self.esya_sahibi_mi(saldiran.id, "biçak"):
            return await interaction.response.send_message("Bu işlemi yapmak için envanterinde 🗡️ Bıçak olmalı.", ephemeral=True)

        await interaction.response.defer()

        # ⛔ Dokunulmazlık - sonsuz koruma
        if self.esya_sahibi_mi(kisi.id, "dokunulmazlik"):
            await interaction.followup.send(f"⛔ {kisi.mention} **Dokunulmazlığa** sahip, katledilemez!")
            await self.olay_bildir(
                interaction.guild, saldiran, kisi,
                f"⛔ {saldiran.mention} saldırmaya çalıştı ama {kisi.mention} **Dokunulmazlık** sayesinde etkilenmedi."
            )
            return

        # 🪖 Demir Zırh - tek kullanımlık koruma
        if self.esya_sahibi_mi(kisi.id, "zirh"):
            self.esya_sil(kisi.id, "zirh", 1)
            await interaction.followup.send(f"🪖 {kisi.mention} **Demir Zırh** sayesinde bıçak saldırısından kurtuldu! (Zırh kırıldı)")
            await self.olay_bildir(
                interaction.guild, saldiran, kisi,
                f"🪖 {kisi.mention}'un üzerindeki **Demir Zırh**, {saldiran.mention}'ın saldırısını engelledi ve kırıldı. Mağdur hayatta kaldı."
            )
            return

        # ✝️ Ölümsüzlük Totemi - DM ile seçim
        if self.esya_sahibi_mi(kisi.id, "totem"):
            self.pending[str(kisi.id)] = {"saldiran": saldiran.id}
            kaydet(PENDING_FILE, self.pending)
            try:
                embed = discord.Embed(
                    title="💀 Ölüm Anı!",
                    description=(
                        f"**{interaction.guild.name}** sunucusunda **{saldiran.display_name}** seni bıçakladı!\n\n"
                        f"Envanterinde bir **✝️ Ölümsüzlük Totemi** var. Ne yapmak istersin?"
                    ),
                    color=discord.Color.dark_red(),
                )
                await kisi.send(embed=embed, view=TotemView())
                await interaction.followup.send(f"💉 {kisi.mention} saldırıya uğradı, karar vermesi için DM gönderildi...")
            except discord.Forbidden:
                self.esya_sil(kisi.id, "totem", 1)
                self.pending.pop(str(kisi.id), None)
                kaydet(PENDING_FILE, self.pending)
                await interaction.followup.send(f"✝️ {kisi.mention}'a DM gönderilemedi, totem otomatik devreye girdi ve hayatta kaldı.")
                await self.olay_bildir(
                    interaction.guild, saldiran, kisi,
                    f"✝️ Mağdura DM gönderilemediği için **Ölümsüzlük Totemi** otomatik kullanıldı, mağdur hayatta kaldı."
                )
            return

        # Hiçbir koruma yok -> direkt ölür
        await self.olumu_uygula(interaction.guild, saldiran, kisi)
        await interaction.followup.send(f"🗡️ {kisi.mention} hiçbir korumaya sahip değildi ve **öldürüldü**.")

    async def totem_karar_ver(self, interaction: discord.Interaction, kullan: bool):
        uid = str(interaction.user.id)
        bekleyen = self.pending.get(uid)
        if not bekleyen:
            return await interaction.response.send_message("Bu işlem artık geçerli değil.", ephemeral=True)

        guild = self.bot.get_guild(GUILD_ID)
        saldiran = guild.get_member(bekleyen["saldiran"]) if guild else None
        kisi_member = guild.get_member(interaction.user.id) if guild else None

        self.pending.pop(uid, None)
        kaydet(PENDING_FILE, self.pending)

        if not guild or not saldiran or not kisi_member:
            return await interaction.response.edit_message(content="Bir hata oluştu, işlem tamamlanamadı.", embed=None, view=None)

        if kullan:
            self.esya_sil(kisi_member.id, "totem", 1)
            await interaction.response.edit_message(content="✝️ Totemini kullandın ve hayata döndün! 🩸", embed=None, view=None)
            await self.olay_bildir(
                guild, saldiran, kisi_member,
                f"✝️ {kisi_member.mention}, envanterindeki **Ölümsüzlük Totemi**'ni kullanarak {saldiran.mention}'ın saldırısından kurtuldu."
            )
        else:
            await interaction.response.edit_message(content="☠️ Ölümü kabul ettin...", embed=None, view=None)
            await self.olumu_uygula(guild, saldiran, kisi_member)

    # ---------- Canlandırma ----------
    @app_commands.command(name="canlandir", description="Ölü birini hayata döndürür (Yardım Kiti gerekir)")
    @app_commands.describe(kisi="Canlandırılacak kişi")
    async def canlandir(self, interaction: discord.Interaction, kisi: discord.Member):
        kurtarici = interaction.user
        if not ekonomi_kullanabilir_mi(kurtarici):
            return await interaction.response.send_message("Bu komutu kullanma yetkin yok.", ephemeral=True)
        if not any(r.id == OLU_ROL_ID for r in kisi.roles):
            return await interaction.response.send_message(f"{kisi.mention} zaten hayatta.", ephemeral=True)
        if not self.esya_sahibi_mi(kurtarici.id, "kit"):
            return await interaction.response.send_message("Bu işlemi yapmak için envanterinde ❤️‍🩹 Yardım Kiti olmalı.", ephemeral=True)

        olu_rol = interaction.guild.get_role(OLU_ROL_ID)
        if olu_rol:
            try:
                await kisi.remove_roles(olu_rol, reason="Canlandırıldı")
            except discord.Forbidden:
                pass

        self.esya_sil(kurtarici.id, "kit", 1)

        await interaction.response.send_message(
            f"❤️‍🩹 {kurtarici.mention}, {kisi.mention}'ı hayata döndürdü!\n"
            f"💬 {kisi.mention}: \"Beni kurtardığın için çok teşekkür ederim {kurtarici.mention}! 🙏\""
        )

        kanal = interaction.guild.get_channel(OLAYLAR_KANAL_ID)
        if kanal:
            embed = discord.Embed(
                title="❤️‍🩹 Canlandırma Olayı",
                description=(
                    f"{kurtarici.mention}, ❤️‍🩹 **Yardım Kiti** kullanarak {kisi.mention}'ı hayata döndürdü.\n"
                    f"{kisi.mention} kendisini kurtaran {kurtarici.mention}'a teşekkür etti."
                ),
                color=discord.Color.green(),
            )
            embed.timestamp = discord.utils.utcnow()
            await kanal.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Market(bot))
