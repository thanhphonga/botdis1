import os
import discord
from discord.ext import commands

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def setup_hook():
    from modules.ticket import TicketView, CloseButton
    from modules.voice import VoiceRoomPanel
    from modules.music import MusicControls

    bot.add_view(TicketView())
    bot.add_view(CloseButton())
    bot.add_view(VoiceRoomPanel())
    bot.add_view(MusicControls())

@bot.event
async def on_ready():
    print(f"Bot đã đăng nhập: {bot.user}")
    from modules.voice import ensure_panel
    await ensure_panel()

# Load all three feature modules; they share this exact bot instance.
import modules.ticket
import modules.voice
import modules.music

if __name__ == "__main__":
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("Thiếu BOT_TOKEN trong GitHub Secrets / Environment Variables.")

    required = {
        "TICKET_CATEGORY_ID": os.getenv("TICKET_CATEGORY_ID"),
        "VOICE_LOBBY_ID": os.getenv("VOICE_LOBBY_ID"),
        "VOICE_CATEGORY_ID": os.getenv("VOICE_CATEGORY_ID"),
        "VOICE_PANEL_CHANNEL_ID": os.getenv("VOICE_PANEL_CHANNEL_ID"),
    }
    missing = [name for name, value in required.items() if not value]
    if missing:
        raise RuntimeError("Thiếu cấu hình: " + ", ".join(missing))

    bot.run(token)
