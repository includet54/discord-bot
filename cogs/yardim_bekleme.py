import discord
from discord.ext import commands
from discord.ui import View, Button, Modal, TextInput
from datetime import datetime, timezone

# ==================== AYARLAR ====================
YARDIM_BEKLEME = 1532829788824404274          # Yardım Bekleme ses kanalı
YARDIM_SESI = 1532829837150916719             # YARDIM ses kanalı
ONEMLI_LOG = 1532829734742786168              # ÖNEMLİ LOG BİLDİRİM
ONLY_MODERATOR = 1532828404347437287          # Only Moderatör kanalı

KURUCU_ROLE = 1529546007635824680
UST_YONETIM_ROLE = 1539167256246747186
YONETICI_ROLE = 1534798061845483694

YONETIM_ROLLER = [KURUCU_ROLE, UST_YONETIM_ROLE, YONETICI_ROLE]
# =================================================

# Aktif destekleri tutmak için (member_id → {log_msg, start_time, staff_id})
active_supports = {}


class SupportModal(Modal, title="Destek Sonucu"):
    reason = TextInput(
        label="Katılımcı Neden Yardım istedi? Sonuç nasıl bitti?",
        style=discord.TextStyle.paragraph,
        placeholder="Açıklama yaz...",
        required=True,
        max_length=1000
    )

    def __init__(self, member_id: int, staff_id: int, duration: str):
        super().__init__()
        self.member_id = member_id
        self.staff_id = staff_id
        self.duration = duration

    async def on_submit(self, interaction: discord.Interaction):
        only_mod = interaction.guild.get_channel(ONLY_MODERATOR)
        member = interaction.guild.get_member(self.member_id)
        staff = interaction.guild.get_member(self.staff_id)

        embed = discord.Embed(
            title="📋 Destek Raporu",
            color=0x3498DB,
            timestamp=datetime.now(timezone.utc)
        )
        embed.add_field(name="Yetkili", value=staff.mention if staff else f"<@{self.staff_id}>", inline=True)
        embed.add_field(name="Katılımcı", value=member.mention if member else f"<@{self.member_id}>", inline=True)
        embed.add_field(name="Süre", value=self.duration, inline=True)
        embed.add_field(name="Açıklama", value=self.reason.value, inline=False)

        if only_mod:
            await only_mod.send(embed=embed)

        await interaction.response.send_message("✅ Rapor gönderildi.", ephemeral=True)


class AfterTakeView(View):
    def __init__(self, member_id: int, staff_id: int, start_time: datetime):
        super().__init__(timeout=None)
        self.member_id = member_id
        self.staff_id = staff_id
        self.start_time = start_time

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.staff_id:
            await interaction.response.send_message("❌ Bu butonlara sadece desteği devralan yetkili basabilir!", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Desteği Bitir", style=discord.ButtonStyle.success, custom_id="support_finish")
    async def finish(self, interaction: discord.Interaction, button: Button):
        # YARDIM ses kanalındaki herkesi at
        yardim = interaction.guild.get_channel(YARDIM_SESI)
        if yardim and isinstance(yardim, discord.VoiceChannel):
            for m in list(yardim.members):
                try:
                    await m.move_to(None)
                except:
                    pass

        duration = str(datetime.now(timezone.utc) - self.start_time).split(".")[0]
        modal = SupportModal(self.member_id, self.staff_id, duration)
        await interaction.response.send_modal(modal)

        # Log mesajını güncelle / butonları kaldır
        try:
            await interaction.message.edit(view=None)
        except:
            pass

        if self.member_id in active_supports:
            del active_supports[self.member_id]

    @discord.ui.button(label="Boş", style=discord.ButtonStyle.secondary, custom_id="support_empty")
    async def empty(self, interaction: discord.Interaction, button: Button):
        yardim = interaction.guild.get_channel(YARDIM_SESI)
        if yardim and isinstance(yardim, discord.VoiceChannel):
            for m in list(yardim.members):
                try:
                    await m.move_to(None)
                except:
                    pass

        only_mod = interaction.guild.get_channel(ONLY_MODERATOR)
        staff = interaction.guild.get_member(self.staff_id)
        member = interaction.guild.get_member(self.member_id)

        if only_mod:
            await only_mod.send(
                f"**Boş Destek**\n"
                f"Yetkili: {staff.mention if staff else self.staff_id}\n"
                f"Katılımcı: {member.mention if member else self.member_id}"
            )

        await interaction.response.send_message("✅ Boş olarak kapatıldı.", ephemeral=True)
        try:
            await interaction.message.edit(view=None)
        except:
            pass

        if self.member_id in active_supports:
            del active_supports[self.member_id]


class WaitingLogView(View):
    def __init__(self, member_id: int):
        super().__init__(timeout=None)
        self.member_id = member_id

    @discord.ui.button(label="Katılımcıyı Devral", style=discord.ButtonStyle.success, emoji="✋", custom_id="take_member")
    async def take(self, interaction: discord.Interaction, button: Button):
        # Yönetim kontrolü
        if not any(r.id in YONETIM_ROLLER for r in interaction.user.roles):
            await interaction.response.send_message("❌ Sadece Yönetim basabilir!", ephemeral=True)
            return

        member = interaction.guild.get_member(self.member_id)
        if not member or not member.voice or member.voice.channel.id != YARDIM_BEKLEME:
            await interaction.response.send_message("❌ Katılımcı artık bekleme kanalında değil.", ephemeral=True)
            return

        yardim = interaction.guild.get_channel(YARDIM_SESI)
        if not yardim:
            await interaction.response.send_message("❌ YARDIM ses kanalı bulunamadı.", ephemeral=True)
            return

        # Katılımcıyı taşı + susturmayı kaldır
        try:
            await member.move_to(yardim)
            await member.edit(mute=False)
        except Exception as e:
            await interaction.response.send_message(f"❌ Taşıma hatası: {e}", ephemeral=True)
            return

        # Yetkili de YARDIM kanalındaysa oraya taşı
        if interaction.user.voice and interaction.user.voice.channel:
            try:
                await interaction.user.move_to(yardim)
            except:
                pass

        start_time = datetime.now(timezone.utc)
        active_supports[self.member_id] = {
            "staff_id": interaction.user.id,
            "start_time": start_time,
            "log_msg": interaction.message
        }

        # Butonları değiştir
        new_view = AfterTakeView(self.member_id, interaction.user.id, start_time)
        await interaction.response.edit_message(
            content=interaction.message.content + f"\n\n✅ **{interaction.user.mention}** tarafından devralındı.",
            view=new_view
        )

    @discord.ui.button(label="Katılımcıyı Beklemeden Çıkar", style=discord.ButtonStyle.danger, emoji="🚪", custom_id="kick_waiting")
    async def kick(self, interaction: discord.Interaction, button: Button):
        if not any(r.id in YONETIM_ROLLER for r in interaction.user.roles):
            await interaction.response.send_message("❌ Sadece Yönetim basabilir!", ephemeral=True)
            return

        member = interaction.guild.get_member(self.member_id)
        if member and member.voice and member.voice.channel and member.voice.channel.id == YARDIM_BEKLEME:
            try:
                await member.move_to(None)
            except:
                pass

        only_mod = interaction.guild.get_channel(ONLY_MODERATOR)
        if only_mod:
            await only_mod.send(
                f"**Beklemeden Çıkarıldı**\n"
                f"Yetkili: {interaction.user.mention}\n"
                f"Katılımcı: {member.mention if member else self.member_id}"
            )

        await interaction.response.edit_message(view=None)
        await interaction.followup.send("✅ Katılımcı çıkarıldı.", ephemeral=True)


class YardimBekleme(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        if member.bot:
            return

        # Bekleme kanalına girdi
        if after.channel and after.channel.id == YARDIM_BEKLEME:
            if before.channel is None or before.channel.id != YARDIM_BEKLEME:
                # Sustur
                try:
                    await member.edit(mute=True)
                except:
                    pass

                # Log at
                log_channel = self.bot.get_channel(ONEMLI_LOG)
                if log_channel:
                    embed = discord.Embed(
                        title="🆘 Yardım Bekleme",
                        description=f"{member.mention} **Yardım Bekleme** kanalına girdi.",
                        color=0xE67E22,
                        timestamp=datetime.now(timezone.utc)
                    )
                    view = WaitingLogView(member.id)
                    msg = await log_channel.send(
                        content=" ".join([f"<@&{r}>" for r in YONETIM_ROLLER]),
                        embed=embed,
                        view=view
                    )

        # Bekleme kanalından çıktı → susturmayı kaldır
        if before.channel and before.channel.id == YARDIM_BEKLEME:
            if after.channel is None or after.channel.id != YARDIM_BEKLEME:
                try:
                    await member.edit(mute=False)
                except:
                    pass


async def setup(bot: commands.Bot):
    await bot.add_cog(YardimBekleme(bot))
    # Persistent view'lar
    bot.add_view(WaitingLogView(0))
    bot.add_view(AfterTakeView(0, 0, datetime.now(timezone.utc)))
