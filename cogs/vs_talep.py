import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button, Select, UserSelect

# ==================== AYARLAR ====================
VS_TALEP_KANAL_ID = 1537136926287593503          # [vs talep] kanalı
VS_SONUC_KANAL_ID = 1537142672953708685          # [vs sonuç] kanalı

KURUCU_ROLE = 1529546007635824680
UST_YONETIM_ROLE = 1539167256246747186
YONETICI_ROLE = 1534798061845483694

PVP_MANAGER_ROLE = 1539169640326893589
DRIVE_MANAGER_ROLE = 1539169263124746350

YONETIM_ROLLER = [KURUCU_ROLE, UST_YONETIM_ROLE, YONETICI_ROLE]
# =================================================

class VSTypeSelect(Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="PVP", value="PVP", description="PVP kapışması", emoji="⚔️"),
            discord.SelectOption(label="DRIVE", value="DRIVE", description="Drive kapışması", emoji="🚗"),
        ]
        super().__init__(
            placeholder="Hangi türde kapışmak istiyorsun?",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="vs_type_select"
        )

    async def callback(self, interaction: discord.Interaction):
        self.view.selected_type = self.values[0]
        await interaction.response.defer()


class VSUserSelect(UserSelect):
    def __init__(self):
        super().__init__(
            placeholder="Kiminle kapışmak istiyorsun? (Mağdur)",
            min_values=1,
            max_values=1,
            custom_id="vs_user_select"
        )

    async def callback(self, interaction: discord.Interaction):
        self.view.selected_user = self.values[0]
        await interaction.response.defer()


class VSRequestView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.selected_user = None
        self.selected_type = None
        self.add_item(VSUserSelect())
        self.add_item(VSTypeSelect())

    @discord.ui.button(label="Talebi Gönder", style=discord.ButtonStyle.danger, emoji="⚔️", custom_id="vs_submit")
    async def submit(self, interaction: discord.Interaction, button: Button):
        if self.selected_user is None or self.selected_type is None:
            await interaction.response.send_message(
                "❌ Lütfen **hem kişiyi** hem de **türü** seçmelisin!",
                ephemeral=True
            )
            return

        if self.selected_user.id == interaction.user.id:
            await interaction.response.send_message("❌ Kendinle kapışamazsın!", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        guild = interaction.guild
        requester = interaction.user
        victim = self.selected_user
        vs_type = self.selected_type

        # Kanal ismi
        channel_name = f"vs-{requester.display_name[:10]}-vs-{victim.display_name[:10]}".lower().replace(" ", "-")

        # Overwrites
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            requester: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            victim: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
        }

        # Yönetim rolleri
        for role_id in YONETIM_ROLLER:
            role = guild.get_role(role_id)
            if role:
                overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)

        # Manager rolü
        manager_role_id = PVP_MANAGER_ROLE if vs_type == "PVP" else DRIVE_MANAGER_ROLE
        manager_role = guild.get_role(manager_role_id)
        if manager_role:
            overwrites[manager_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)

        # Kanal oluştur
        category = interaction.channel.category
        new_channel = await guild.create_text_channel(
            name=channel_name,
            overwrites=overwrites,
            category=category,
            reason=f"VS Talebi: {requester} vs {victim} ({vs_type})"
        )

        # Sabit mesaj + butonlar
        embed = discord.Embed(
            title="⚔️ VS Talebi Açıldı",
            description=(
                f"**Açan:** {requester.mention}\n"
                f"**Mağdur:** {victim.mention}\n"
                f"**Tür:** `{vs_type}`\n\n"
                f"Yönetim ekibi aşağıdan sonucu belirlesin."
            ),
            color=0xE74C3C
        )

        view = VSChannelView(requester.id, victim.id, vs_type, new_channel.id)
        msg = await new_channel.send(
            content=f"{requester.mention} {victim.mention} "
                    f"{' '.join([f'<@&{r}>' for r in YONETIM_ROLLER])} "
                    f"<@&{manager_role_id}>",
            embed=embed,
            view=view
        )
        await msg.pin()

        await interaction.followup.send(
            f"✅ VS talebin oluşturuldu → {new_channel.mention}",
            ephemeral=True
        )


class VSChannelView(View):
    def __init__(self, requester_id: int, victim_id: int, vs_type: str, channel_id: int):
        super().__init__(timeout=None)
        self.requester_id = requester_id
        self.victim_id = victim_id
        self.vs_type = vs_type
        self.channel_id = channel_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        # Sadece yönetim basabilir
        user_roles = [r.id for r in interaction.user.roles]
        if not any(r in user_roles for r in YONETIM_ROLLER):
            await interaction.response.send_message("❌ Bu butonlara sadece Yönetim ekibi basabilir!", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Talebi Açan Kazandı", style=discord.ButtonStyle.success, custom_id="vs_requester_win")
    async def requester_win(self, interaction: discord.Interaction, button: Button):
        await self._finish(interaction, winner_id=self.requester_id, loser_id=self.victim_id)

    @discord.ui.button(label="Mağdur Kazandı", style=discord.ButtonStyle.primary, custom_id="vs_victim_win")
    async def victim_win(self, interaction: discord.Interaction, button: Button):
        await self._finish(interaction, winner_id=self.victim_id, loser_id=self.requester_id)

    @discord.ui.button(label="Talep İptal Edildi", style=discord.ButtonStyle.danger, custom_id="vs_cancel")
    async def cancel(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer()
        channel = interaction.guild.get_channel(self.channel_id)
        if channel:
            await channel.delete(reason="VS Talebi iptal edildi")

    async def _finish(self, interaction: discord.Interaction, winner_id: int, loser_id: int):
        await interaction.response.defer()

        sonuc_kanal = interaction.guild.get_channel(VS_SONUC_KANAL_ID)
        if sonuc_kanal:
            winner = interaction.guild.get_member(winner_id)
            loser = interaction.guild.get_member(loser_id)
            embed = discord.Embed(
                title="🏆 VS Sonucu",
                description=(
                    f"**Kazanan:** {winner.mention if winner else f'<@{winner_id}>'}\n"
                    f"**Kaybeden:** {loser.mention if loser else f'<@{loser_id}>'}\n"
                    f"**Tür:** `{self.vs_type}`"
                ),
                color=0x2ECC71
            )
            await sonuc_kanal.send(embed=embed)

        channel = interaction.guild.get_channel(self.channel_id)
        if channel:
            await channel.delete(reason="VS sonucu belirlendi")


class VSSetupView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="VS Talep Oluştur", style=discord.ButtonStyle.danger, emoji="⚔️", custom_id="vs_open_request")
    async def open_request(self, interaction: discord.Interaction, button: Button):
        view = VSRequestView()
        await interaction.response.send_message(
            "Aşağıdan **kimi** ve **hangi türde** kapışmak istediğini seç, sonra **Talebi Gönder** butonuna bas:",
            view=view,
            ephemeral=True
        )


async def setup_vs_talep(bot: commands.Bot):
    """Bot başladığında sabit mesajı atar (yoksa)."""
    channel = bot.get_channel(VS_TALEP_KANAL_ID)
    if not channel:
        return

    # Daha önce atılmış mı kontrol et
    async for msg in channel.history(limit=20):
        if msg.author == bot.user and msg.components:
            return  # Zaten var

    embed = discord.Embed(
        title="⚔️ VS TALEP",
        description=(
            "!! Vs talep için kişinin adını söyleyin ve türünü belirtin.\n\n"
            "**Bu zorunlu, talepte yazmanız gerek!**\n\n"
            "Bunu yapacağınızdan emin misiniz?"
        ),
        color=0x9B59B6
    )
    embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/000/vs.png")  # İstersen değiştir

    view = VSSetupView()
    await channel.send(embed=embed, view=view)


# Persistent view'ları kaydetmek için
async def setup(bot: commands.Bot):
    bot.add_view(VSSetupView())
    bot.add_view(VSChannelView(0, 0, "PVP", 0))  # dummy, gerçekleri runtime'da oluşturuyoruz
    # Bot hazır olunca sabit mesajı kontrol et
    @bot.listen()
    async def on_ready():
        await setup_vs_talep(bot)
