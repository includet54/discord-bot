import discord
from discord.ext import commands
from discord import app_commands

# ============================
TICKET_KANAL_ID = 1534770099179884564
TICKET_KATEGORI_ID = None
BILET_LOG_KANAL_ID = 1532828404347437287   # Kapatılan ticket loglarının gideceği kanal

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
    return any(r.id in YETKILI_ROL_IDLERI for r in member.roles)


class CloseTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🔒 Kapat", style=discord.ButtonStyle.red, custom_id="ticket_kapat_buton")
    async def kapat(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not yetkili_mi(interaction.user):
            return await interaction.response.send_message(
                "❌ Bu işlemi sadece yetkililer yapabilir.", ephemeral=True
            )

        kanal = interaction.channel
        topic = kanal.topic or ""
        acan_id = None
        if "acan_id:" in topic:
            try:
                acan_id = int(topic.split("acan_id:")[1].strip())
            except Exception:
                acan_id = None

        acan_uye = kanal.guild.get_member(acan_id) if acan_id else None

        log_kanal = kanal.guild.get_channel(BILET_LOG_KANAL_ID)
        if log_kanal:
            embed = discord.Embed(
                title="🔒 Ticket Kapatıldı",
                color=discord.Color.red(),
            )
            embed.add_field(name="Kanal", value=f"#{kanal.name}", inline=True)
            embed.add_field(name="Açan Kişi", value=acan_uye.mention if acan_uye else "Bilinmiyor (ayrılmış olabilir)", inline=True)
            embed.add_field(name="Kapatan Kişi", value=interaction.user.mention, inline=True)
            embed.add_field(name="Açılış Tarihi", value=discord.utils.format_dt(kanal.created_at, style="F"), inline=False)
            embed.timestamp = discord.utils.utcnow()
            await log_kanal.send(embed=embed)

        await interaction.response.send_message("Kanal 5 saniye içinde silinecek...")
        await kanal.delete(delay=5)


class TicketPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🎫 Ticket Aç", style=discord.ButtonStyle.green, custom_id="ticket_ac_buton")
    async def ticket_ac(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        kanal_adi = f"ticket-{interaction.user.name}".lower()
        var_olan = discord.utils.get(guild.text_channels, name=kanal_adi)
        if var_olan:
            return await interaction.response.send_message(
                f"Zaten açık bir ticket'ın var: {var_olan.mention}", ephemeral=True
            )

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True),
        }
        for rol_id in YETKILI_ROL_IDLERI:
            rol = guild.get_role(rol_id)
            if rol:
                overwrites[rol] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)

        kategori = guild.get_channel(TICKET_KATEGORI_ID) if TICKET_KATEGORI_ID else None

        try:
            kanal = await guild.create_text_channel(
                kanal_adi,
                overwrites=overwrites,
                category=kategori,
                topic=f"acan_id:{interaction.user.id}",
            )
        except discord.Forbidden:
            return await interaction.response.send_message("Botun kanal oluşturma yetkisi yok.", ephemeral=True)

        rol_etiketleri = " ".join(f"<@&{rid}>" for rid in YETKILI_ROL_IDLERI)

        embed = discord.Embed(
            title="🎫 Destek Talebi",
            description=f"{interaction.user.mention} bir destek talebi oluşturdu.\nYetkililer en kısa sürede ilgilenecek.",
            color=discord.Color.blurple(),
        )

        await kanal.send(content=f"{interaction.user.mention} {rol_etiketleri}", embed=embed, view=CloseTicketView())
        await interaction.response.send_message(f"Ticket açıldı: {kanal.mention}", ephemeral=True)


class Tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ticket-panel", description="Ticket panelini gönderir")
    async def ticket_panel(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.manage_channels:
            return await interaction.response.send_message("Yetkin yok.", ephemeral=True)
        embed = discord.Embed(
            title="🎫 Destek Sistemi",
            description="Destek almak için aşağıdaki butona tıkla, senin için özel bir kanal açılacak.",
            color=discord.Color.blurple(),
        )
        await interaction.channel.send(embed=embed, view=TicketPanelView())
        await interaction.response.send_message("Panel gönderildi.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Tickets(bot))
