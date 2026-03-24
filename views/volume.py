import discord
from discord.ui import View, Button


class VolumeControlView(View):
    def __init__(self, cog, player):
        super().__init__(timeout=30)
        self.cog = cog
        self.player = player

    @discord.ui.button(emoji="🔇", label="ปิดเสียง", style=discord.ButtonStyle.danger)
    async def mute(self, interaction: discord.Interaction, button: Button):
        self.player.volume = 0.0
        embed = discord.Embed(title="🔇 ปิดเสียงแล้ว", description="ระดับเสียง: **0%**", color=0xEF4444)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(emoji="🔉", label="-10%", style=discord.ButtonStyle.secondary)
    async def volume_down(self, interaction: discord.Interaction, button: Button):
        self.player.volume = max(0.0, self.player.volume - 0.1)
        embed = discord.Embed(
            title="🔊 ปรับระดับเสียง",
            description=f"ระดับเสียง: **{int(self.player.volume * 100)}%**",
            color=0x7C3AED,
        )
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(emoji="🔊", label="+10%", style=discord.ButtonStyle.secondary)
    async def volume_up(self, interaction: discord.Interaction, button: Button):
        self.player.volume = min(2.0, self.player.volume + 0.1)
        embed = discord.Embed(
            title="🔊 ปรับระดับเสียง",
            description=f"ระดับเสียง: **{int(self.player.volume * 100)}%**",
            color=0x7C3AED,
        )
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(emoji="📢", label="สูงสุด", style=discord.ButtonStyle.success)
    async def max_volume(self, interaction: discord.Interaction, button: Button):
        self.player.volume = 1.0
        embed = discord.Embed(
            title="📢 เสียงสูงสุด", description="ระดับเสียง: **100%**", color=0x22C55E
        )
        await interaction.response.edit_message(embed=embed, view=self)
