import os
import discord
from discord.ext import commands
from bot import bot


# Required environment variables:
# VOICE_TOKEN, VOICE_LOBBY_ID, VOICE_CATEGORY_ID, VOICE_PANEL_CHANNEL_ID

LOBBY_ID = int(os.getenv("VOICE_LOBBY_ID", "0"))
CATEGORY_ID = int(os.getenv("VOICE_CATEGORY_ID", "0"))
PANEL_CHANNEL_ID = int(os.getenv("VOICE_PANEL_CHANNEL_ID", "0"))



def owner_id_of(channel: discord.VoiceChannel):
    # Owner is saved in the channel topic, so it survives bot restarts.
    topic = channel.topic or ""
    if topic.startswith("voice-owner:"):
        try:
            return int(topic.split(":", 1)[1])
        except ValueError:
            return None
    return None


def owned_room(member: discord.Member):
    if not member.voice or not isinstance(member.voice.channel, discord.VoiceChannel):
        return None
    channel = member.voice.channel
    if channel.category_id != CATEGORY_ID or owner_id_of(channel) != member.id:
        return None
    return channel


class RenameModal(discord.ui.Modal, title="Đổi tên phòng thoại"):
    new_name = discord.ui.TextInput(
        label="Tên phòng mới",
        placeholder="Nhập tên phòng...",
        min_length=1,
        max_length=90,
    )

    async def on_submit(self, interaction: discord.Interaction):
        room = owned_room(interaction.user)
        if room is None:
            return await interaction.response.send_message(
                "Bạn cần ở trong phòng thoại do chính bạn tạo.", ephemeral=True
            )
        await room.edit(name=str(self.new_name), reason="Chủ phòng đổi tên")
        await interaction.response.send_message(
            f"Đã đổi tên phòng thành **{room.name}**.", ephemeral=True
        )


class LimitModal(discord.ui.Modal, title="Giới hạn người tham gia"):
    limit = discord.ui.TextInput(
        label="Số người (0 = không giới hạn)",
        placeholder="Ví dụ: 5",
        min_length=1,
        max_length=2,
    )

    async def on_submit(self, interaction: discord.Interaction):
        room = owned_room(interaction.user)
        if room is None:
            return await interaction.response.send_message(
                "Bạn cần ở trong phòng thoại do chính bạn tạo.", ephemeral=True
            )
        try:
            value = int(str(self.limit))
            if not 0 <= value <= 99:
                raise ValueError
        except ValueError:
            return await interaction.response.send_message(
                "Hãy nhập số từ 0 đến 99.", ephemeral=True
            )
        await room.edit(user_limit=value, reason="Chủ phòng thay đổi giới hạn")
        message = "Đã bỏ giới hạn người tham gia." if value == 0 else f"Phòng được giới hạn **{value}** người."
        await interaction.response.send_message(message, ephemeral=True)


class MemberActionSelect(discord.ui.UserSelect):
    def __init__(self, action: str):
        self.action = action
        placeholder = "Chọn người cần mời vào phòng" if action == "invite" else "Chọn người cần mời ra khỏi phòng"
        super().__init__(placeholder=placeholder, min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        room = owned_room(interaction.user)
        if room is None:
            return await interaction.response.send_message(
                "Bạn cần ở trong phòng thoại do chính bạn tạo.", ephemeral=True
            )
        target = self.values[0]
        if not isinstance(target, discord.Member):
            return await interaction.response.send_message("Không tìm thấy thành viên.", ephemeral=True)

        if self.action == "invite":
            await room.set_permissions(target, view_channel=True, connect=True)
            await interaction.response.send_message(
                f"Đã cấp quyền vào phòng cho **{target.display_name}**.", ephemeral=True
            )
        else:
            if target not in room.members:
                return await interaction.response.send_message(
                    "Thành viên này không ở trong phòng của bạn.", ephemeral=True
                )
            if target.id == interaction.user.id:
                return await interaction.response.send_message(
                    "Bạn không thể tự mời mình ra khỏi phòng.", ephemeral=True
                )
            await target.move_to(None, reason=f"Chủ phòng {interaction.user} đã mời ra")
            await interaction.response.send_message(
                f"Đã mời **{target.display_name}** rời phòng.", ephemeral=True
            )


class MemberActionView(discord.ui.View):
    def __init__(self, action: str):
        super().__init__(timeout=60)
        self.add_item(MemberActionSelect(action))


class VoiceRoomPanel(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def get_room(self, interaction: discord.Interaction):
        room = owned_room(interaction.user)
        if room is None:
            await interaction.response.send_message(
                "Bạn cần ở trong phòng thoại tạm do chính bạn tạo để dùng bảng điều khiển.",
                ephemeral=True,
            )
            return None
        return room

    @discord.ui.button(label="Đổi tên", emoji="✏️", style=discord.ButtonStyle.primary, custom_id="voice:rename")
    async def rename(self, interaction: discord.Interaction, button: discord.ui.Button):
        if await self.get_room(interaction):
            await interaction.response.send_modal(RenameModal())

    @discord.ui.button(label="Giới hạn", emoji="👥", style=discord.ButtonStyle.primary, custom_id="voice:limit")
    async def limit(self, interaction: discord.Interaction, button: discord.ui.Button):
        if await self.get_room(interaction):
            await interaction.response.send_modal(LimitModal())

    @discord.ui.button(label="Khóa / Mở khóa", emoji="🔒", style=discord.ButtonStyle.secondary, custom_id="voice:lock")
    async def lock(self, interaction: discord.Interaction, button: discord.ui.Button):
        room = await self.get_room(interaction)
        if room is None:
            return
        overwrite = room.overwrites_for(interaction.guild.default_role)
        currently_locked = overwrite.connect is False
        await room.set_permissions(
            interaction.guild.default_role,
            view_channel=True,
            connect=True if currently_locked else False,
        )
        await interaction.response.send_message(
            "Đã mở khóa phòng." if currently_locked else "Đã khóa phòng.",
            ephemeral=True,
        )

    @discord.ui.button(label="Mời người vào", emoji="➕", style=discord.ButtonStyle.success, custom_id="voice:invite")
    async def invite(self, interaction: discord.Interaction, button: discord.ui.Button):
        if await self.get_room(interaction):
            await interaction.response.send_message(
                "Chọn thành viên muốn mời:", view=MemberActionView("invite"), ephemeral=True
            )

    @discord.ui.button(label="Mời ra khỏi phòng", emoji="🚪", style=discord.ButtonStyle.danger, custom_id="voice:kick")
    async def kick(self, interaction: discord.Interaction, button: discord.ui.Button):
        if await self.get_room(interaction):
            await interaction.response.send_message(
                "Chọn thành viên muốn mời ra:", view=MemberActionView("kick"), ephemeral=True
            )


async def ensure_panel():
    channel = bot.get_channel(PANEL_CHANNEL_ID)
    if not isinstance(channel, discord.TextChannel):
        print("Không tìm thấy kênh bảng điều khiển. Kiểm tra VOICE_PANEL_CHANNEL_ID.")
        return
    async for message in channel.history(limit=50):
        if message.author.id == bot.user.id and message.embeds:
            if message.embeds[0].title == "🎙️ BẢNG ĐIỀU KHIỂN PHÒNG THOẠI":
                return
    embed = discord.Embed(
        title="🎙️ BẢNG ĐIỀU KHIỂN PHÒNG THOẠI",
        description=(
            "Vào kênh **Tạo phòng thoại** để bot tạo phòng riêng cho bạn.\n"
            "Sau đó vào phòng của mình và bấm nút bên dưới để quản lý.\n\n"
            "✏️ Đổi tên  •  👥 Giới hạn người\n"
            "🔒 Khóa / mở khóa  •  ➕ Mời người vào\n"
            "🚪 Mời người rời phòng\n\n"
            "Chỉ chủ phòng mới sử dụng được các nút quản lý."
        ),
        color=discord.Color.blurple(),
    )
    await channel.send(embed=embed, view=VoiceRoomPanel())


@bot.event
async def on_voice_state_update(member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
    if after.channel and after.channel.id == LOBBY_ID:
        guild = member.guild
        category = guild.get_channel(CATEGORY_ID)
        if not isinstance(category, discord.CategoryChannel):
            print("VOICE_CATEGORY_ID không đúng hoặc không phải danh mục.")
            return
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=True, connect=True),
            member: discord.PermissionOverwrite(
                view_channel=True, connect=True, speak=True,
                manage_channels=True, move_members=True
            ),
        }
        try:
            room = await guild.create_voice_channel(
                name=f"🔊・{member.display_name}"[:100],
                category=category,
                overwrites=overwrites,
                topic=f"voice-owner:{member.id}",
                reason="Tạo phòng thoại tạm",
            )
            await member.move_to(room, reason="Chuyển vào phòng thoại vừa tạo")
        except discord.Forbidden:
            print("Bot thiếu quyền Manage Channels hoặc Move Members.")
        except discord.HTTPException as error:
            print(f"Không tạo được phòng: {error}")

    if before.channel and isinstance(before.channel, discord.VoiceChannel):
        old = before.channel
        if old.category_id == CATEGORY_ID and owner_id_of(old) is not None and len(old.members) == 0:
            try:
                await old.delete(reason="Phòng thoại tạm đã trống")
            except discord.HTTPException as error:
                print(f"Không xóa được phòng trống: {error}")

