import discord
from discord.ext import commands, tasks
from discord import app_commands
import asyncio
import logging
import yt_dlp
import random
import time

from models.player import MusicPlayer, FFMPEG_OPTIONS
from utils.helpers import format_duration, format_number, get_progress_bar
from views.controls import EnhancedControlButtons

logger = logging.getLogger("music")


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.music_channels = {}
        self.players = {}
        self.auto_cleanup.start()

    @commands.Cog.listener()
    async def on_ready(self):
        logger.info("🔍 Restoring existing music rooms...")
        count = 0
        for guild in self.bot.guilds:
            category = discord.utils.get(guild.categories, name="🎵 MUSIC ROOMS")
            if category:
                for channel in category.text_channels:
                    if channel.name.startswith("🎵┃") and channel.name.endswith("-music"):
                        self.music_channels[channel.id] = channel
                        count += 1
        logger.info(f"✅ Restored {count} existing music rooms.")

    def get_audio_source(self, query: str):
        ydl_opts = {
            "format": "bestaudio",
            "quiet": True,
            "default_search": "ytsearch",
            "noplaylist": True,
            "extract_flat": False,
            "source_address": "0.0.0.0",
            # Enable node.js since yt-dlp disabled everything but Deno by default
            "js_runtimes": {"nodejs": {}},
            # Bypass "Sign in to confirm you're not a bot" for YouTube via client spoofing
            "extractor_args": {
                "youtube": ["player_client=android,ios,tv,web"]
            },
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

            logger.info(f"▶️ Playing: {title} in {discord.utils.get(self.bot.guilds, id=guild_id).name}")

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

        embed = discord.Embed(color=0x7C3AED)

        embed.set_author(
            name="♫ ─── กำลังเล่นเพลง ─── ♫",
            icon_url="https://cdn.discordapp.com/emojis/741605543046807626.gif",
        )

        song_block = (
            f"```ansi\n"
            f"\u001b[1;37m{title}\u001b[0m\n"
            f"```\n"
            f"> 👨‍🎤  **ศิลปิน** ─ {uploader}\n"
            f"> ⏱️  **ความยาว** ─ {format_duration(duration)}\n"
            f"> 👁️  **ยอดวิว** ─ {format_number(view_count)}\n"
            f"> 🎧  **สั่งโดย** ─ {requester.mention}\n"
        )
        embed.description = song_block

        if thumbnail:
            embed.set_thumbnail(url=thumbnail)

        if player.start_time and duration:
            current_time = time.time() - player.start_time
            progress_bar = get_progress_bar(current_time, duration, length=25)
            time_display = f"`{format_duration(current_time)}` ▸ {progress_bar} ▸ `{format_duration(duration)}`"
        else:
            progress_bar = "━" * 25
            time_display = f"`00:00` ▸ {progress_bar} ▸ `{format_duration(duration)}`"

        embed.add_field(
            name="━━━━━━━━ ♪ แถบเวลา ♪ ━━━━━━━━",
            value=time_display,
            inline=False,
        )

        loop_icon = "```ansi\n\u001b[1;32m✓ เปิด\u001b[0m\n```" if player.loop else "```ansi\n\u001b[1;31m✗ ปิด\u001b[0m\n```"
        shuffle_icon = "```ansi\n\u001b[1;32m✓ เปิด\u001b[0m\n```" if player.shuffle else "```ansi\n\u001b[1;31m✗ ปิด\u001b[0m\n```"

        status_info = (
            f"📝  **คิวเพลง** ─ `{len(player.queue)}` เพลง\n"
            f"🔊  **ระดับเสียง** ─ `{int(player.volume * 100)}%`\n"
            f"🔂  **วนซ้ำ** ─ {'`เปิด ✅`' if player.loop else '`ปิด ❌`'}\n"
            f"🔀  **สุ่มเพลง** ─ {'`เปิด ✅`' if player.shuffle else '`ปิด ❌`'}\n"
        )
        embed.add_field(name="⚙️ สถานะเครื่องเล่น", value=status_info, inline=True)

        if player.queue:
            next_tracks = []
            for i, track in enumerate(list(player.queue)[:3]):
                t = track[1][:40] + "..." if len(track[1]) > 40 else track[1]
                next_tracks.append(f"`{i+1}.` {t}")
            next_value = "\n".join(next_tracks)
            if len(player.queue) > 3:
                next_value += f"\n*...และอีก {len(player.queue) - 3} เพลง*"
        else:
            next_value = "*ว่างเปล่า ─ พิมพ์ชื่อเพลงเพื่อเพิ่ม*"

        embed.add_field(name="⏭️ เพลงถัดไป", value=next_value, inline=True)

        embed.set_footer(
            text=f"📍 {player.channel.name} ─ พิมพ์ชื่อเพลงหรือ URL เพื่อเพิ่มลงคิว",
            icon_url=requester.display_avatar.url,
        )
        embed.timestamp = discord.utils.utcnow()

        view = EnhancedControlButtons(self, player)

        if not player.message:
            try:
                async for msg in player.channel.history(limit=50):
                    if msg.author == self.bot.user and msg.embeds and any("Progress" in f.name for f in msg.embeds[0].fields):
                        player.message = msg
                        break
            except Exception as e:
                logger.warning(f"⚠️ Could not search old embed: {e}")

        if player.message:
            try:
                await player.message.edit(embed=embed, view=view)
            except:
                player.message = await player.channel.send(embed=embed, view=view)
        else:
            player.message = await player.channel.send(embed=embed, view=view)

    @app_commands.command(name="create_music_room", description="สร้างห้องเพลง")
    async def create_music_room(self, interaction: discord.Interaction):
        response_embed = discord.Embed(
            title="🎵 Creating Music Room...",
            description="Please wait while I create your personal music room! ⏳",
            color=0xFFFF00,
        )
        await interaction.response.send_message(embed=response_embed, ephemeral=True)

        try:
            name = f"🎵┃{interaction.user.display_name}-music"

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

            welcome_embed = discord.Embed(
                description=(
                    "## ♫ ─── ยินดีต้อนรับสู่ห้องเพลง ─── ♫\n"
                    f"> สร้างโดย {interaction.user.mention}\n\n"
                    "```ansi\n"
                    "\u001b[1;35m♪ พิมพ์ชื่อเพลง หรือวาง URL เพื่อเริ่มเล่นเพลง ♪\u001b[0m\n"
                    "```\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                ),
                color=0x7C3AED,
            )

            welcome_embed.set_image(url="attachment://Damkoeng.jpg")

            welcome_embed.add_field(
                name="🎛️ แผงควบคุมหลัก",
                value=(
                    "> ⏹️  **หยุด** ─ หยุดเพลงและออกจากห้อง\n"
                    "> ⏸️  **พัก** ─ พักเพลงชั่วคราว\n"
                    "> ▶️  **เล่นต่อ** ─ เล่นเพลงต่อจากที่พัก\n"
                    "> ⏭️  **ข้าม** ─ ข้ามไปเพลงถัดไป\n"
                ),
                inline=True,
            )

            welcome_embed.add_field(
                name="🔧 ตั้งค่าขั้นสูง",
                value=(
                    "> 🔁  **ย้อนกลับ** ─ เล่นเพลงก่อนหน้า\n"
                    "> 🔀  **สุ่ม** ─ สลับลำดับเพลงแบบสุ่ม\n"
                    "> 🔂  **วนซ้ำ** ─ เปิด/ปิดการเล่นซ้ำ\n"
                    "> 🔊  **เสียง** ─ ปรับระดับเสียง\n"
                ),
                inline=True,
            )

            welcome_embed.add_field(
                name="━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
                value=(
                    "💡 **คำแนะนำ**\n"
                    "```\n"
                    "• เข้าห้องเสียง (Voice Channel) ก่อนสั่งเพลง\n"
                    "• รองรับทั้ง YouTube URL และชื่อเพลง\n"
                    "• เพิ่มเพลงลงคิวได้ไม่จำกัด\n"
                    "• กดปุ่มด้านล่าง Embed เพื่อควบคุม\n"
                    "```"
                ),
                inline=False,
            )

            welcome_embed.set_footer(
                text="🎵 Damkoeng Music Bot · พัฒนาโดย SUPERTONG",
                icon_url=interaction.user.display_avatar.url,
            )
            welcome_embed.timestamp = discord.utils.utcnow()

            try:
                file = discord.File("assets/Damkoeng.jpg", filename="Damkoeng.jpg")
                await channel.send(embed=welcome_embed, file=file)
            except:
                await channel.send(embed=welcome_embed)

            success_embed = discord.Embed(
                title="✅ สร้างห้องเพลงสำเร็จ!",
                description=(
                    f"🎵 ห้องเพลงของคุณ {channel.mention} พร้อมใช้งานแล้ว!\n"
                    f"🎧 เข้าห้องเสียงแล้วพิมพ์ชื่อเพลงเลยครับ!"
                ),
                color=0x22C55E,
            )

            try:
                await interaction.edit_original_response(embed=success_embed)
            except:
                pass

            logger.info(f"🏠 Created music room: {channel.name}")

        except Exception as e:
            logger.error(f"❌ Error creating music room: {e}")
            error_embed = discord.Embed(
                title="❌ เกิดข้อผิดพลาด",
                description="ไม่สามารถสร้างห้องเพลงได้ กรุณาลองใหม่อีกครั้ง",
                color=0xEF4444,
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
                title="❌ ต้องเข้าห้องเสียงก่อน",
                description="กรุณาเข้าห้องเสียง (Voice Channel) ก่อนสั่งเพลงนะครับ!",
                color=0xEF4444,
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

        loading_embed = discord.Embed(
            title="🔍 กำลังค้นหา...",
            description=f"กำลังค้นหาเพลง: **{message.content}**",
            color=0x7C3AED,
        )
        loading_msg = await message.channel.send(embed=loading_embed)

        try:
            source, title, duration, thumb, uploader, view_count = (
                await asyncio.to_thread(self.get_audio_source, message.content)
            )
            player.queue.append(
                (source, title, duration, thumb, uploader, view_count, message.author)
            )

            added_embed = discord.Embed(
                title="✅ เพิ่มเข้าคิวแล้ว",
                description=f"**{title}**\nโดย {uploader}",
                color=0x22C55E,
            )
            added_embed.set_thumbnail(url=thumb)
            added_embed.add_field(
                name="ลำดับในคิว", value=f"`#{len(player.queue)}`", inline=True
            )
            added_embed.add_field(
                name="ความยาว", value=f"`{format_duration(duration)}`", inline=True
            )

            try:
                await loading_msg.edit(embed=added_embed)
                await asyncio.sleep(3)
                await loading_msg.delete()
            except:
                pass

        except Exception as e:
            logger.warning(f"⚠️ Error loading audio: {e}")
            error_embed = discord.Embed(
                title="❌ ไม่สามารถโหลดเพลงได้",
                description="ไม่พบเพลงที่ต้องการ กรุณาลองค้นหาด้วยคำอื่น หรือวาง URL โดยตรง",
                color=0xEF4444,
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
                        logger.info(f"🧹 Deleted inactive music room: {channel.name}")
                    except Exception as e:
                        logger.warning(f"⚠️ Error deleting channel: {e}")


async def setup(bot):
    await bot.add_cog(Music(bot))
