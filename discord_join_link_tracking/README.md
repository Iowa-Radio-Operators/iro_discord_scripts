# Join Link Tracking with auto log to the admin channel

## Requirements

- Python 3.12+
- pyenv (recommended for environment management)
- A Discord bot token — see [Setup](#setup)

Install dependencies:
```bash
pip install -r requirements.txt
```

---

## Setup

1. Clone or copy this repo to your server
2. Copy `.env.example` to `.env` and fill in your values:
```
DISCORD_BOT_TOKEN=your_bot_token_here
DISCORD_GUILD_ID=your_guild_id_here
DISCORD_ADMIN_CHANNEL_ID=your_admin_channel_id_here
```
3. Make sure the bot has been invited to your server with the correct permissions — see each script's section below for specifics

---

## Scripts

### `discord_invite_tracker.py`
Tracks invite code usage and posts a monthly report to the admin channel on the 1st of each month.

**Bot permissions required:** Manage Server, Send Messages

**Config:** Edit `invite_codes.txt` with the codes you want to track:
```
abc123, Twitter campaign
xyz789, Reddit post
```

**Run manually:**
```bash
python3 discord_invite_tracker.py --now
```

**Scheduled via cron (runs 1st of each month at midnight):**
```bash
0 0 1 * * cd /path/to/jimbot && python3 discord_invite_tracker.py --now
```

---

## Project Structure

```
jimbot/
├── .env                  # Your secrets — never commit this
├── .env.example          # Template for .env
├── .gitignore
├── requirements.txt
├── invite_codes.txt      # Invite codes to track
├── discord_invite_tracker.py
└── README.md
```

---

## Contributing

When adding a new script, please add a section above following the same format — script name, what it does, required bot permissions, and how to run it.

---

## Notes

- All scripts read credentials from `.env` via `python-dotenv`
- Guild ID = your Discord server ID (right-click server name → Copy Server ID with Developer Mode on)
- Admin channel ID = right-click the channel → Copy Channel ID