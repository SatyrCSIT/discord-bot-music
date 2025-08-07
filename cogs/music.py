import discord
from discord.ext import commands, tasks
from discord import app_commands
from discord.ui import View, Button, Select
import asyncio
import logging
import yt_dlp
from collections import deque
import random
import time

logger = logging.getLogger("music")

FFMPEG_OPTIONS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn",
}


class MusicPlayer:
    def __init__(self):
        self.queue = deque()
        self.history = deque()
        self.current = None
        self.voice_client = None
        self.channel = None
        self.message = None
        self.requester = None
        self.volume = 1.0
        self.paused = False
        self.loop = False
        self.shuffle = False
        self.start_time = None


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.music_channels = {}
        self.players = {}
        self.auto_cleanup.start()

    def get_audio_source(self, query: str):
        ydl_opts = {
            "format": "bestaudio",
            "quiet": True,
            "default_search": "ytsearch",
            "noplaylist": True,
            "extract_flat": False,
            "source_address": "0.0.0.0",
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(query, download=False)
            if "entries" in info:
                info = info["entries"][0]
            title = info.get("title", "Unknown Title")
            url = info["url"]
            duration = info.get("duration", 0)
            thumbnail = info.get("thumbnail")
            uploader = info.get("uploader", "Unknown Artist")
            view_count = info.get("view_count", 0)
            source = discord.FFmpegPCMAudio(url, **FFMPEG_OPTIONS)
            return source, title, duration, thumbnail, uploader, view_count

    def format_duration(self, seconds):
        if seconds is None:
            return "Live"
        mins, secs = divmod(int(seconds), 60)
        hours, mins = divmod(mins, 60)
        if hours > 0:
            return f"{hours:02d}:{mins:02d}:{secs:02d}"
        return f"{mins:02d}:{secs:02d}"

    def format_number(self, num):
        if num >= 1000000:
            return f"{num/1000000:.1f}M"
        elif num >= 1000:
            return f"{num/1000:.1f}K"
        return str(num)

    def get_progress_bar(self, current_time, total_time, length=20):
        if total_time == 0:
            return "━" * length

        progress = min(current_time / total_time, 1.0)
        filled = int(progress * length)
        bar = "━" * filled + "◉" + "━" * (length - filled - 1)
        return bar[:length]

    async def play_next(self, guild_id):
        player = self.players[guild_id]

        if player.loop and player.current:
            player.queue.appendleft(player.current)

        if player.queue:
            if player.shuffle:
                index = random.randint(0, len(player.queue) - 1)
                track = player.queue[index]
                player.queue.remove(track)
            else:
                track = player.queue.popleft()

            if player.current:
                player.history.appendleft(player.current)

            source, title, duration, thumbnail, uploader, view_count, requester = track
            player.current = (
                source,
                title,
                duration,
                thumbnail,
                uploader,
                view_count,
                requester,
            )
            player.start_time = time.time()

            player.voice_client.play(
                source,
                after=lambda e: asyncio.run_coroutine_threadsafe(
                    self.play_next(guild_id), self.bot.loop
                ),
            )
            await self.send_embed(player)
        else:
            if player.message:
                try:
                    await player.message.delete()
                except:
                    pass
            player.current = None
            await player.voice_client.disconnect()
            player.voice_client = None

    async def send_embed(self, player):
        source, title, duration, thumbnail, uploader, view_count, requester = (
            player.current
        )

        # สร้าง embed หลักที่สวยงาม
        embed = discord.Embed(title="", description="", color=0x1DB954)

        # ตั้งค่า thumbnail และ author
        embed.set_thumbnail(url=thumbnail)
        embed.set_author(
            name="🎵 Damkoeng Music Player",
            icon_url="https://cdn.discordapp.com/emojis/741605543046807626.gif",
        )

        # ข้อมูลเพลงแบบสวยงาม
        song_info = f"**{title}**\n"
        song_info += f"👨‍🎤 **Artist:** {uploader}\n"
        song_info += f"⏱️ **Duration:** {self.format_duration(duration)}\n"
        song_info += f"👁️ **Views:** {self.format_number(view_count)}\n"
        song_info += f"🎧 **Requested by:** {requester.mention}\n"

        embed.add_field(name="🎶 Now Playing", value=song_info, inline=False)

        # Progress bar พร้อมเวลา
        if player.start_time and duration:
            current_time = time.time() - player.start_time
            progress_bar = self.get_progress_bar(current_time, duration)
            time_display = f"{self.format_duration(current_time)} / {self.format_duration(duration)}"
        else:
            progress_bar = "━" * 20
            time_display = "00:00 / 00:00"

        embed.add_field(
            name="📊 Progress",
            value=f"```{progress_bar}```\n{time_display}",
            inline=False,
        )

        # ข้อมูลคิว
        queue_info = f"📝 **Queue:** {len(player.queue)} songs\n"
        queue_info += f"🔊 **Volume:** {int(player.volume * 100)}%\n"
        queue_info += f"🔂 **Loop:** {'✅' if player.loop else '❌'}\n"
        queue_info += f"🔀 **Shuffle:** {'✅' if player.shuffle else '❌'}\n"
        queue_info += f"📍 **Channel:** {player.channel.mention}"

        embed.add_field(name="⚙️ Player Status", value=queue_info, inline=True)

        # แสดงเพลงถัดไป
        if player.queue:
            next_track = player.queue[0]
            next_title = (
                next_track[1][:50] + "..." if len(next_track[1]) > 50 else next_track[1]
            )
            embed.add_field(
                name="⏭️ Up Next",
                value=f"**{next_title}**\nby {next_track[4]}",
                inline=True,
            )
        else:
            embed.add_field(name="⏭️ Up Next", value="*Queue is empty*", inline=True)

        # Footer สวยๆ
        embed.set_footer(
            text="🎵 พัฒนาโดย SUPERTONG | พิมพ์ชื่อเพลงหรือ URL เพื่อเพิ่มลงคิว",
            icon_url="https://cdn.discordapp.com/emojis/741605543046807626.gif",
        )

        embed.timestamp = discord.utils.utcnow()

        # สร้าง control buttons ที่สวยงาม
        view = EnhancedControlButtons(self, player)

        if player.message:
            try:
                await player.message.edit(embed=embed, view=view)
            except:
                player.message = await player.channel.send(embed=embed, view=view)
        else:
            player.message = await player.channel.send(embed=embed, view=view)

    @app_commands.command(name="create_music_room", description="สร้างห้องเพลง")
    async def create_music_room(self, interaction: discord.Interaction):
        # ตอบกลับทันทีเพื่อไม่ให้ timeout
        response_embed = discord.Embed(
            title="🎵 Creating Music Room...",
            description="Please wait while I create your personal music room! ⏳",
            color=0xFFFF00,
        )
        await interaction.response.send_message(embed=response_embed, ephemeral=True)

        try:
            name = f"🎵┃{interaction.user.display_name}-music"

            # สร้าง category สำหรับห้องเพลง
            category = discord.utils.get(
                interaction.guild.categories, name="🎵 MUSIC ROOMS"
            )
            if not category:
                category = await interaction.guild.create_category("🎵 MUSIC ROOMS")

            channel = await interaction.guild.create_text_channel(
                name=name,
                category=category,
                topic=f"🎵 Music Room {interaction.user.display_name}",
            )
            self.music_channels[channel.id] = channel

            # สร้าง embed แนะนำที่สวยงาม
            welcome_embed = discord.Embed(
                title="🎵 Damkoeng Music Room",
                description="**Welcome to your personal music paradise! ✨**",
                color=0x9932CC,
            )

            welcome_embed.set_image(url="attachment://Damkoeng.jpg")

            welcome_embed.add_field(
                name="Start",
                value=("```\n" "• Type name song or url to play music ˚ ⊹\n" "```"),
                inline=False,
            )

            welcome_embed.add_field(
                name="🎛️ Control Panel",
                value=(
                    "⏹️ **Stop** - Stop music and disconnect\n"
                    "⏸️ **Pause** - Pause current song\n"
                    "▶️ **Resume** - Resume playback\n"
                    "⏭️ **Skip** - Skip to next song\n"
                ),
                inline=True,
            )

            welcome_embed.add_field(
                name="🔧 Advanced Controls",
                value=(
                    "🔁 **Previous** - Play previous song\n"
                    "🔀 **Shuffle** - Toggle shuffle mode\n"
                    "🔂 **Loop** - Toggle loop mode\n"
                    "🔊 **Volume** - Adjust volume\n"
                ),
                inline=True,
            )

            welcome_embed.add_field(
                name="💡 Pro Tips",
                value=(
                    "• Join a voice channel first\n"
                    "• Support YouTube, Spotify links\n"
                    "• Queue unlimited songs\n"
                ),
                inline=False,
            )

            welcome_embed.set_footer(
                text="🎵 พัฒนาโดย SUPERTONG | ขอให้สนุกกับการฟังเพลง!",
                icon_url=interaction.user.display_avatar.url,
            )

            welcome_embed.timestamp = discord.utils.utcnow()

            try:
                file = discord.File("assets/Damkoeng.jpg", filename="Damkoeng.jpg")
                await channel.send(embed=welcome_embed, file=file)
            except:
                await channel.send(embed=welcome_embed)

            # อัพเดท response message
            success_embed = discord.Embed(
                title="✅ Music Room Created!",
                description=f"🎵 Your music room {channel.mention} is ready!\n🎧 Join a voice channel and start typing song names!",
                color=0x00FF00,
            )

            try:
                await interaction.edit_original_response(embed=success_embed)
            except:
                pass  # ถ้าแก้ไขไม่ได้ก็ไม่เป็นไร

            logger.info(f"Created enhanced music room: {channel.name}")

        except Exception as e:
            logger.error(f"Error creating music room: {e}")
            error_embed = discord.Embed(
                title="❌ Error Creating Room",
                description="Something went wrong while creating your music room. Please try again.",
                color=0xFF0000,
            )
            try:
                await interaction.edit_original_response(embed=error_embed)
            except:
                pass

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        if message.channel.id not in self.music_channels:
            return

        try:
            await message.delete()
        except:
            pass

        guild = message.guild
        player = self.players.get(guild.id)
        if not player:
            player = MusicPlayer()
            self.players[guild.id] = player

        voice_state = message.author.voice
        if not voice_state or not voice_state.channel:
            error_embed = discord.Embed(
                title="❌ Error",
                description="Please join a voice channel first!",
                color=0xFF0000,
            )
            error_msg = await message.channel.send(embed=error_embed)
            await asyncio.sleep(3)
            try:
                await error_msg.delete()
            except:
                pass
            return

        if not player.voice_client:
            vc = await voice_state.channel.connect()
            player.voice_client = vc
            player.channel = message.channel

        # แสดง loading message
        loading_embed = discord.Embed(
            title="🔍 Searching...",
            description=f"Looking for: **{message.content}**",
            color=0xFFFF00,
        )
        loading_msg = await message.channel.send(embed=loading_embed)

        try:
            source, title, duration, thumb, uploader, view_count = (
                await asyncio.to_thread(self.get_audio_source, message.content)
            )
            player.queue.append(
                (source, title, duration, thumb, uploader, view_count, message.author)
            )

            # แสดง added to queue message
            added_embed = discord.Embed(
                title="✅ Added to Queue",
                description=f"**{title}**\nby {uploader}",
                color=0x00FF00,
            )
            added_embed.set_thumbnail(url=thumb)
            added_embed.add_field(
                name="Position in Queue", value=f"#{len(player.queue)}", inline=True
            )
            added_embed.add_field(
                name="Duration", value=self.format_duration(duration), inline=True
            )

            try:
                await loading_msg.edit(embed=added_embed)
                await asyncio.sleep(3)
                await loading_msg.delete()
            except:
                pass

        except Exception as e:
            logger.warning(f"Error loading audio: {e}")
            error_embed = discord.Embed(
                title="❌ Error",
                description="Could not load the song. Please try again with a different query.",
                color=0xFF0000,
            )
            try:
                await loading_msg.edit(embed=error_embed)
                await asyncio.sleep(3)
                await loading_msg.delete()
            except:
                pass
            return

        if not player.voice_client.is_playing():
            await self.play_next(guild.id)

    @tasks.loop(minutes=1)
    async def auto_cleanup(self):
        for channel_id in list(self.music_channels):
            channel = self.bot.get_channel(channel_id)
            if channel and isinstance(channel, discord.TextChannel):
                if len(channel.members) == 0:
                    try:
                        await channel.delete()
                        del self.music_channels[channel_id]
                        logger.info(f"Deleted inactive music room: {channel.name}")
                    except Exception as e:
                        logger.warning(f"Error deleting channel: {e}")


class EnhancedControlButtons(View):
    def __init__(self, cog, player):
        super().__init__(timeout=None)
        self.cog = cog
        self.player = player

    @discord.ui.button(emoji="⏹️", style=discord.ButtonStyle.danger, label="Stop")
    async def stop(self, interaction: discord.Interaction, button: Button):
        await self.player.voice_client.disconnect()
        if self.player.message:
            try:
                await self.player.message.delete()
            except:
                pass

        embed = discord.Embed(
            title="⏹️ Music Stopped",
            description="Disconnected from voice channel",
            color=0xFF0000,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(emoji="⏸️", style=discord.ButtonStyle.primary, label="Pause")
    async def pause(self, interaction: discord.Interaction, button: Button):
        if self.player.voice_client.is_playing():
            self.player.voice_client.pause()
            embed = discord.Embed(
                title="⏸️ Music Paused",
                description="Playback has been paused",
                color=0xFFA500,
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(emoji="▶️", style=discord.ButtonStyle.success, label="Resume")
    async def resume(self, interaction: discord.Interaction, button: Button):
        if self.player.voice_client.is_paused():
            self.player.voice_client.resume()
            embed = discord.Embed(
                title="▶️ Music Resumed",
                description="Playback has been resumed",
                color=0x00FF00,
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(emoji="⏭️", style=discord.ButtonStyle.secondary, label="Skip")
    async def skip(self, interaction: discord.Interaction, button: Button):
        if self.player.current:
            current_title = self.player.current[1]
            self.player.voice_client.stop()
            embed = discord.Embed(
                title="⏭️ Song Skipped",
                description=(
                    f"Skipped: **{current_title[:50]}...**"
                    if len(current_title) > 50
                    else f"Skipped: **{current_title}**"
                ),
                color=0x00BFFF,
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(
        emoji="🔁", style=discord.ButtonStyle.secondary, label="Previous"
    )
    async def previous(self, interaction: discord.Interaction, button: Button):
        if self.player.history:
            self.player.queue.appendleft(self.player.current)
            self.player.current = self.player.history.popleft()
            self.player.voice_client.stop()
            embed = discord.Embed(
                title="🔁 Previous Song",
                description="Playing previous song",
                color=0x9370DB,
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(emoji="🔀", style=discord.ButtonStyle.secondary, label="Shuffle")
    async def toggle_shuffle(self, interaction: discord.Interaction, button: Button):
        self.player.shuffle = not self.player.shuffle
        state = "Enabled" if self.player.shuffle else "Disabled"
        color = 0x00FF00 if self.player.shuffle else 0xFF0000
        embed = discord.Embed(
            title=f"🔀 Shuffle {state}",
            description=f"Shuffle mode is now {state.lower()}",
            color=color,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(emoji="🔂", style=discord.ButtonStyle.secondary, label="Loop")
    async def toggle_loop(self, interaction: discord.Interaction, button: Button):
        self.player.loop = not self.player.loop
        state = "Enabled" if self.player.loop else "Disabled"
        color = 0x00FF00 if self.player.loop else 0xFF0000
        embed = discord.Embed(
            title=f"🔂 Loop {state}",
            description=f"Loop mode is now {state.lower()}",
            color=color,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(emoji="🔊", style=discord.ButtonStyle.secondary, label="Volume")
    async def volume_control(self, interaction: discord.Interaction, button: Button):
        view = VolumeControlView(self.cog, self.player)
        embed = discord.Embed(
            title="🔊 Volume Control",
            description=f"Current volume: **{int(self.player.volume * 100)}%**\nUse the buttons below to adjust",
            color=0x1DB954,
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class VolumeControlView(View):
    def __init__(self, cog, player):
        super().__init__(timeout=30)
        self.cog = cog
        self.player = player

    @discord.ui.button(emoji="🔇", label="Mute", style=discord.ButtonStyle.danger)
    async def mute(self, interaction: discord.Interaction, button: Button):
        self.player.volume = 0.0
        embed = discord.Embed(title="🔇 Muted", color=0xFF0000)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(emoji="🔉", label="-10%", style=discord.ButtonStyle.secondary)
    async def volume_down(self, interaction: discord.Interaction, button: Button):
        self.player.volume = max(0.0, self.player.volume - 0.1)
        embed = discord.Embed(
            title="🔊 Volume Control",
            description=f"Volume: **{int(self.player.volume * 100)}%**",
            color=0x1DB954,
        )
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(emoji="🔊", label="+10%", style=discord.ButtonStyle.secondary)
    async def volume_up(self, interaction: discord.Interaction, button: Button):
        self.player.volume = min(2.0, self.player.volume + 0.1)
        embed = discord.Embed(
            title="🔊 Volume Control",
            description=f"Volume: **{int(self.player.volume * 100)}%**",
            color=0x1DB954,
        )
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(emoji="📢", label="Max", style=discord.ButtonStyle.success)
    async def max_volume(self, interaction: discord.Interaction, button: Button):
        self.player.volume = 1.0
        embed = discord.Embed(
            title="📢 Max Volume", description="Volume: **100%**", color=0x00FF00
        )
        await interaction.response.edit_message(embed=embed, view=self)


async def setup(bot):
    await bot.add_cog(Music(bot))
