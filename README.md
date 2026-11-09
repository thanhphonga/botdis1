# Discord bot - 3 chức năng, 1 token

## Cấu trúc
- `bot.py`: khởi chạy một Discord bot duy nhất.
- `modules/ticket.py`: chức năng ticket.
- `modules/music.py`: chức năng phát nhạc.
- `modules/voice.py`: tạo và quản lý phòng thoại bằng nút bấm.

## Cài thư viện
```bash
pip install -r requirements.txt
```
Máy chủ chạy bot nhạc cần cài FFmpeg và thêm FFmpeg vào PATH.

## GitHub Secrets / Environment Variables
Chỉ có **một token**:
- `BOT_TOKEN`: token của một Discord application/bot duy nhất.

Các ID cấu hình (không phải token):
- `TICKET_CATEGORY_ID`
- `VOICE_LOBBY_ID`
- `VOICE_CATEGORY_ID`
- `VOICE_PANEL_CHANNEL_ID`
- `MUSIC_LOG_CHANNEL_ID` (không bắt buộc; mặc định có trong code)

## Chạy
```bash
python bot.py
```

## Discord Developer Portal
Bật **Message Content Intent** và **Server Members Intent** trong Bot settings.
Cấp quyền phù hợp: Manage Channels, View Channels, Send Messages, Embed Links,
Connect, Speak, Move Members, Read Message History.

## Lưu ý
- Ba chức năng chạy trên cùng một bot user và một kết nối gateway.
- Các chức năng ticket và voice dùng ID category/kênh đã cấu hình.
- GitHub chỉ lưu code; không tự chạy bot 24/7. Cần VPS/hosting chạy tiến trình lâu dài.
- Không đưa token vào code hoặc commit token lên repository.
