import os
import asyncio
import discord
from discord.ext import commands
from discord import SelectOption
from bot import bot


# Bat Message Content Intent trong Discord Developer Portal

BANNER_URL = "https://auto.creavite.co/api/out/j5OBb4qMpFSIss90mc_standard.gif"
TICKET_CATEGORY_ID = int(os.getenv("TICKET_CATEGORY_ID", "0"))


class CloseButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Đóng Ticket",
        style=discord.ButtonStyle.danger,
        custom_id="close_ticket_button",
    )
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message("Không thể đóng kênh này.", ephemeral=True)
            return

        await interaction.response.send_message("Ticket sẽ được đóng sau 3 giây.", ephemeral=True)
        await asyncio.sleep(3)

        try:
            await channel.delete(reason=f"Ticket closed by {interaction.user}")
        except discord.Forbidden:
            print("Bot thiếu quyền Manage Channels để xóa ticket.")
        except discord.HTTPException as error:
            print(f"Không thể xóa ticket: {error}")


class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.select(
        placeholder="Chọn loại hỗ trợ",
        options=[
            SelectOption(
                label="Hỗ trợ khiếu nại",
                value="support",
                description="Hỗ trợ khiếu nại",
            ),
            SelectOption(
                label="Hỗ trợ member",
                value="member",
                description="Hỗ trợ cho member",
            ),
        ],
        min_values=1,
        max_values=1,
        custom_id="ticket_select",
    )
    async def select_callback(self, interaction: discord.Interaction, select: discord.ui.Select):
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message(
                "Lệnh này chỉ sử dụng được trong máy chủ Discord.", ephemeral=True
            )
            return

        category = guild.get_channel(TICKET_CATEGORY_ID)
        if not isinstance(category, discord.CategoryChannel):
            await interaction.response.send_message(
                "Không tìm thấy category ticket. Hãy kiểm tra TICKET_CATEGORY_ID.",
                ephemeral=True,
            )
            return

        selected_option = select.values[0]
        ticket_type = "Hỗ trợ khiếu nại" if selected_option == "support" else "Hỗ trợ member"

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(
                view_channel=True, send_messages=True, read_message_history=True
            ),
        }
        if bot.user is not None:
            overwrites[bot.user] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                manage_channels=True,
            )

        safe_username = "".join(
            char.lower() if char.isalnum() else "-"
            for char in interaction.user.name
        ).strip("-")
        channel_name = f"ticket-{safe_username}"[:95]

        try:
            ticket_channel = await category.create_text_channel(
                name=channel_name,
                overwrites=overwrites,
                reason=f"Ticket created by {interaction.user}",
            )

            await interaction.response.send_message(
                f"🎫 Ticket của bạn đã được tạo tại {ticket_channel.mention}!",
                ephemeral=True,
            )

            embed = discord.Embed(
                title="🎟 Ticket Hỗ Trợ",
                description=(
                    f"Chào {interaction.user.mention}, vui lòng đợi đội ngũ hỗ trợ phản hồi.\n\n"
                    f"**Loại hỗ trợ:** {ticket_type}"
                ),
                color=discord.Color.blue(),
            )
            embed.set_image(url=BANNER_URL)
            await ticket_channel.send(
                content=interaction.user.mention, embed=embed, view=CloseButton()
            )

        except discord.Forbidden:
            message = (
                "❌ Bot chưa đủ quyền tạo kênh hoặc gửi tin nhắn. "
                "Hãy cấp Manage Channels, View Channels và Send Messages."
            )
            if not interaction.response.is_done():
                await interaction.response.send_message(message, ephemeral=True)
            else:
                await interaction.followup.send(message, ephemeral=True)
        except discord.HTTPException as error:
            print(f"Lỗi tạo ticket: {error}")
            message = "❌ Có lỗi Discord khi tạo ticket. Vui lòng thử lại sau."
            if not interaction.response.is_done():
                await interaction.response.send_message(message, ephemeral=True)
            else:
                await interaction.followup.send(message, ephemeral=True)


@bot.command()
async def ticket(ctx: commands.Context):
    embed = discord.Embed(
        title="📩 Hỗ trợ Ticket",
        description="Vui lòng chọn loại hỗ trợ bên dưới để mở ticket:",
        color=discord.Color.green(),
    )
    embed.set_image(url=BANNER_URL)
    await ctx.send(embed=embed, view=TicketView())


@bot.event
async def on_command_error(ctx: commands.Context, error: commands.CommandError):
    if isinstance(error, commands.CommandNotFound):
        return
    print(f"Lỗi lệnh: {error}")
    await ctx.send("❌ Có lỗi khi chạy lệnh. Hãy kiểm tra log của bot.")

