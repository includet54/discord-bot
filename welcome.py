import discord
from discord.ext import commands

class Welcome(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member):
        channel = discord.utils.get(member.guild.text_channels, name="hoşgeldiniz")
        
        if channel is None:
            return

        member_count = member.guild.member_count

        embed = discord.Embed(
            title="✨ Sunucumuza Hoş Geldin!",
            description=(
                f"Merhaba {member.mention}!\n\n"
                f"**{member.guild.name}** ailesine katıldığın için çok mutluyuz.\n"
                f"Seninle birlikte artık **{member_count}** kişiyiz!\n\n"
                f"📜 Kuralları okumayı unutma\n"
                f"💬 Sohbete katılmaktan çekinme\n"
                f"🎮 İyi eğlenceler dileriz!"
            ),
            color=discord.Color.from_rgb(147, 112, 219)
        )
        
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_image(url="file:///C:/Users/pcigd/Downloads/400441-robloxspin.gif")
        
        embed.set_footer(
            text=f"ID: {member.id} • Katılma",
            icon_url=member.guild.icon.url if member.guild.icon else None
        )
        embed.timestamp = discord.utils.utcnow()

        await channel.send(content=f"Hoş geldin {member.mention} 💜", embed=embed)

async def setup(bot):
    await bot.add_cog(Welcome(bot))