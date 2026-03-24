import discord
from discord.ui import View, Button

from .volume import VolumeControlView


class EnhancedControlButtons(View):
    def __init__(self, cog, player):
        super().__init__(timeout=None)
        self.cog = cog
        self.player = player

    @discord.ui.button(emoji="⏹️", style=discord.ButtonStyle.danger, label="หยุด")
    async def stop(self, interaction: discord.Interaction, button: Button):
        await self.player.voice_client.disconnect()
        if self.player.message:
            try:
                await self.player.message.delete()
            except:
                pass

        embed = discord.Embed(
            title="⏹️ หยุดเล่นเพลงแล้ว",
            description="ออกจากห้องเสียงเรียบร้อย",
            color=0xEF4444,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(emoji="⏸️", style=discord.ButtonStyle.primary, label="พัก")
    async def pause(self, interaction: discord.Interaction, button: Button):
        if self.player.voice_client.is_playing():
            self.player.voice_client.pause()
            embed = discord.Embed(
                title="⏸️ พักเพลงชั่วคราว",
                description="กดปุ่ม **เล่นต่อ** เพื่อฟังต่อ",
                color=0xF59E0B,
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(emoji="▶️", style=discord.ButtonStyle.success, label="เล่นต่อ")
    async def resume(self, interaction: discord.Interaction, button: Button):
        if self.player.voice_client.is_paused():
            self.player.voice_client.resume()
            embed = discord.Embed(
                title="▶️ เล่นเพลงต่อ",
                description="กลับมาเล่นเพลงต่อแล้ว",
                color=0x22C55E,
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(emoji="⏭️", style=discord.ButtonStyle.secondary, label="ข้าม")
    async def skip(self, interaction: discord.Interaction, button: Button):
        if self.player.current:
            current_title = self.player.current[1]
            self.player.voice_client.stop()
            display_title = (
                f"{current_title[:50]}..."
                if len(current_title) > 50
                else current_title
            )
            embed = discord.Embed(
                title="⏭️ ข้ามเพลง",
                description=f"ข้ามเพลง: **{display_title}**",
                color=0x3B82F6,
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(
        emoji="🔁", style=discord.ButtonStyle.secondary, label="ย้อนกลับ"
    )
    async def previous(self, interaction: discord.Interaction, button: Button):
        if self.player.history:
            self.player.queue.appendleft(self.player.current)
            self.player.current = self.player.history.popleft()
            self.player.voice_client.stop()
            embed = discord.Embed(
                title="🔁 เพลงก่อนหน้า",
                description="กำลังเล่นเพลงก่อนหน้า",
                color=0x8B5CF6,
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(emoji="🔀", style=discord.ButtonStyle.secondary, label="สุ่ม")
    async def toggle_shuffle(self, interaction: discord.Interaction, button: Button):
        self.player.shuffle = not self.player.shuffle
        state = "เปิด ✅" if self.player.shuffle else "ปิด ❌"
        color = 0x22C55E if self.player.shuffle else 0xEF4444
        embed = discord.Embed(
            title=f"🔀 สุ่มเพลง: {state}",
            description=f"โหมดสุ่มเพลง{' เปิดใช้งานแล้ว' if self.player.shuffle else ' ปิดแล้ว'}",
            color=color,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(emoji="🔂", style=discord.ButtonStyle.secondary, label="วนซ้ำ")
    async def toggle_loop(self, interaction: discord.Interaction, button: Button):
        self.player.loop = not self.player.loop
        state = "เปิด ✅" if self.player.loop else "ปิด ❌"
        color = 0x22C55E if self.player.loop else 0xEF4444
        embed = discord.Embed(
            title=f"🔂 วนซ้ำ: {state}",
            description=f"โหมดวนซ้ำ{' เปิดใช้งานแล้ว' if self.player.loop else ' ปิดแล้ว'}",
            color=color,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(emoji="🔊", style=discord.ButtonStyle.secondary, label="เสียง")
    async def volume_control(self, interaction: discord.Interaction, button: Button):
        view = VolumeControlView(self.cog, self.player)
        embed = discord.Embed(
            title="🔊 ปรับระดับเสียง",
            description=f"ระดับเสียงปัจจุบัน: **{int(self.player.volume * 100)}%**\nกดปุ่มด้านล่างเพื่อปรับ",
            color=0x7C3AED,
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
