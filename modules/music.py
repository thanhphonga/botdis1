import os
import asyncio
import discord
from discord.ext import commands
import yt_dlp
from bot import bot


LOG_CHANNEL_ID = int(os.getenv("MUSIC_LOG_CHANNEL_ID", "1336561764858331209"))


YTDL_OPTIONS = {
    "format": "bestaudio/best",
    "noplaylist": True,
    "quiet": True,
    "default_search": "ytsearch",
    "source_address": "0.0.0.0",
}
FFMPEG_OPTIONS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn",
}

queues = {}       # guild_id -> list of track dictionaries
now_playing = {}  # guild_id -> track dictionary
player_messages = {}  # guild_id -> message


async def extract_track(query: str):
    loop = asyncio.get_running_loop()
    data = await loop.run_in_executor(
        None, lambda: yt_dlp.YoutubeDL(YTDL_OPTIONS).extract_info(query, download=False)
    )
    if "entries" in data:
        data = next((entry for entry in data["entries"] if entry), None)
    if not data:
        raise ValueError("Không tìm thấy bài hát.")
    return {
        "title": data.get("title", "Không rõ tên"),
        "url": data.get("url"),
        "webpage_url": data.get("webpage_url", query),
        "duration": data.get("duration"),
    }


def format_duration(seconds):
    if seconds is None:
        return "Không rõ"
    minutes, seconds = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours}:{minutes:02d}:{seconds:02d}" if hours else f"{minutes}:{seconds:02d}"


async def refresh_panel(guild_id: int):
    message = player_messages.get(guild_id)
    if not message:
        return
    track = now_playing.get(guild_id)
    if track:
        embed = discord.Embed(
            title="🎵 ĐANG PHÁT",
            description=f"**[{track['title']}]({track['webpage_url']})**",
            color=discord.Color.blurple(),
        )
    else:
        embed = discord.Embed(
            title="🎵 TRÌNH PHÁT NHẠC",
            description="Chưa có bài hát nào đang phát.",
            color=discord.Color.blurple(),
        )
    upcoming = queues.get(guild_id, [])
    if upcoming:
        lines = [f"`{i}.` {item['title']}" for i, item in enumerate(upcoming[:8], 1)]
        embed.add_field(name="📜 Tiếp theo", value="\n".join(lines), inline=False)
    try:
        await message.edit(embed=embed, view=MusicControls())
    except (discord.NotFound, discord.HTTPException):
        player_messages.pop(guild_id, None)


async def play_next(guild: discord.Guild):
    guild_id = guild.id
    if not queues.get(guild_id):
        now_playing.pop(guild_id, None)
        await refresh_panel(guild_id)
        return
    track = queues[guild_id].pop(0)
    voice = guild.voice_client
    if not voice or not voice.is_connected():
        now_playing.pop(guild_id, None)
        await refresh_panel(guild_id)
        return
    now_playing[guild_id] = track
    source = discord.FFmpegPCMAudio(track["url"], **FFMPEG_OPTIONS)

    def after_play(error):
        if error:
            print(f"Lỗi phát nhạc: {error}")
        asyncio.run_coroutine_threadsafe(play_next(guild), bot.loop)

    voice.play(source, after=after_play)
    await refresh_panel(guild_id)


class AddSongModal(discord.ui.Modal, title="Thêm bài hát"):
    query = discord.ui.TextInput(
        label="Tên bài hát hoặc đường dẫn",
        placeholder="Nhập tên bài hát / link YouTube...",
        max_length=300,
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            track = await extract_track(str(self.query))
            guild_id = interaction.guild_id
            if guild_id is None:
                return await interaction.followup.send("Chỉ dùng trong máy chủ Discord.", ephemeral=True)
            queues.setdefault(guild_id, []).append(track)
            voice = interaction.guild.voice_client
            if voice and not voice.is_playing() and not voice.is_paused() and guild_id not in now_playing:
                await play_next(interaction.guild)
            await interaction.followup.send(f"Đã thêm **{track['title']}** vào hàng chờ.", ephemeral=True)
            await refresh_panel(guild_id)
        except Exception as error:
            await interaction.followup.send(f"Không thêm được bài hát: {error}", ephemeral=True)


class MusicControls(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Tạm dừng", emoji="⏸️", style=discord.ButtonStyle.secondary, custom_id="music:pause")
    async def pause(self, interaction: discord.Interaction, button: discord.ui.Button):
        voice = interaction.guild.voice_client if interaction.guild else None
        if voice and voice.is_playing():
            voice.pause()
            await interaction.response.send_message("Đã tạm dừng.", ephemeral=True)
        else:
            await interaction.response.send_message("Hiện không có nhạc đang phát.", ephemeral=True)

    @discord.ui.button(label="Tiếp tục", emoji="▶️", style=discord.ButtonStyle.success, custom_id="music:resume")
    async def resume(self, interaction: discord.Interaction, button: discord.ui.Button):
        voice = interaction.guild.voice_client if interaction.guild else None
        if voice and voice.is_paused():
            voice.resume()
            await interaction.response.send_message("Đã phát tiếp.", ephemeral=True)
        else:
            await interaction.response.send_message("Nhạc không ở trạng thái tạm dừng.", ephemeral=True)

    @discord.ui.button(label="Thêm bài", emoji="➕", style=discord.ButtonStyle.primary, custom_id="music:add")
    async def add(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(AddSongModal())

    @discord.ui.button(label="Bỏ qua", emoji="⏭️", style=discord.ButtonStyle.primary, custom_id="music:skip")
    async def skip(self, interaction: discord.Interaction, button: discord.ui.Button):
        voice = interaction.guild.voice_client if interaction.guild else None
        if voice and (voice.is_playing() or voice.is_paused()):
            voice.stop()
            await interaction.response.send_message("Đã bỏ qua bài hiện tại.", ephemeral=True)
        else:
            await interaction.response.send_message("Không có bài hát nào đang phát.", ephemeral=True)

    @discord.ui.button(label="Hàng chờ", emoji="📜", style=discord.ButtonStyle.secondary, custom_id="music:queue")
    async def show_queue(self, interaction: discord.Interaction, button: discord.ui.Button):
        items = queues.get(interaction.guild_id, [])
        if not items:
            return await interaction.response.send_message("Hàng chờ đang trống.", ephemeral=True)
        lines = [f"`{i}.` {item['title']}" for i, item in enumerate(items[:15], 1)]
        await interaction.response.send_message("\n".join(lines), ephemeral=True)

    @discord.ui.button(label="Dừng nhạc", emoji="⏹️", style=discord.ButtonStyle.danger, custom_id="music:stop")
    async def stop(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild_id = interaction.guild_id
        voice = interaction.guild.voice_client if interaction.guild else None
        queues[guild_id] = []
        now_playing.pop(guild_id, None)
        if voice:
            if voice.is_playing() or voice.is_paused():
                voice.stop()
            await voice.disconnect()
        await interaction.response.send_message("Đã dừng nhạc và ngắt kết nối.", ephemeral=True)
        await refresh_panel(guild_id)


@bot.command(name="play", aliases=["phát"])
async def play(ctx, *, query: str):
    if not ctx.author.voice or not ctx.author.voice.channel:
        return await ctx.reply("Bạn cần vào kênh thoại trước.")
    try:
        voice = ctx.guild.voice_client
        if voice is None:
            voice = await ctx.author.voice.channel.connect()
        elif voice.channel != ctx.author.voice.channel:
            await voice.move_to(ctx.author.voice.channel)

        track = await extract_track(query)
        queues.setdefault(ctx.guild.id, []).append(track)

        embed = discord.Embed(
            title="🎵 TRÌNH PHÁT NHẠC",
            description=f"Đã thêm **[{track['title']}]({track['webpage_url']})** vào hàng chờ.",
            color=discord.Color.blurple(),
        )
        message = await ctx.send(embed=embed, view=MusicControls())
        player_messages[ctx.guild.id] = message

        if not voice.is_playing() and not voice.is_paused() and ctx.guild.id not in now_playing:
            await play_next(ctx.guild)

        if LOG_CHANNEL_ID:
            log_channel = bot.get_channel(LOG_CHANNEL_ID)
            if isinstance(log_channel, discord.TextChannel):
                await log_channel.send(f"🎶 {ctx.author} đã yêu cầu phát: **{track['title']}**")
    except Exception as error:
        await ctx.reply(f"Không phát được bài hát: {error}")


@bot.command(name="panel")
async def panel(ctx):
    embed = discord.Embed(
        title="🎵 TRÌNH PHÁT NHẠC",
        description="Dùng các nút bên dưới để điều khiển. Dùng `!play tên bài hát` để thêm bài đầu tiên.",
        color=discord.Color.blurple(),
    )
    message = await ctx.send(embed=embed, view=MusicControls())
    player_messages[ctx.guild.id] = message
    await refresh_panel(ctx.guild.id)

