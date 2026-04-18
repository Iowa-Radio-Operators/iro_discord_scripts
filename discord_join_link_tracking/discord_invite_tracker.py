"""
Discord Invite Usage Tracker — Monthly Report
-----------------------------------------------
On the 1st of each month, fetches invite usage for codes listed in
invite_codes.txt and posts a formatted report to your admin channel.

Requirements:
    pip install requests python-dotenv

Files:
    .env              — bot token, guild ID, admin channel ID
    invite_codes.txt  — comma-separated: code,Description

Bot permissions required:
    - Manage Guild    (read invite data)
    - Send Messages   (post to admin channel)

Run:
    python3 discord_invite_tracker.py          # waits for the 1st and posts
    python3 discord_invite_tracker.py --now    # post immediately (for testing)
"""

import os
import time
import csv
import logging
import argparse
from datetime import datetime, timezone, timedelta

import requests
from dotenv import load_dotenv

load_dotenv()

# ── Configuration ─────────────────────────────────────────────────────────────

BOT_TOKEN:        str = os.getenv("DISCORD_BOT_TOKEN", "")
GUILD_ID:         str = os.getenv("DISCORD_GUILD_ID", "")
ADMIN_CHANNEL_ID: str = os.getenv("DISCORD_ADMIN_CHANNEL_ID", "")
INVITE_CODES_FILE: str = os.getenv("INVITE_CODES_FILE", "invite_codes.txt")

API_BASE = "https://discord.com/api/v10"

# ── Logging ───────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("invite-tracker")


# ── Load tracked codes from file ──────────────────────────────────────────────

def load_tracked_codes(path: str) -> dict[str, str]:
    """
    Read invite_codes.txt and return a dict of {code: description}.

    File format (one entry per line):
        abc123, Twitter campaign
        xyz789, Reddit post — June
        promo01, Email newsletter

    Lines starting with # are treated as comments and skipped.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Invite codes file not found: {path}\n"
            "Create invite_codes.txt with lines like:\n"
            "  abc123, Twitter campaign"
        )

    tracked: dict[str, str] = {}
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        for line_num, row in enumerate(reader, start=1):
            # Skip blank lines and comments
            if not row or row[0].strip().startswith("#"):
                continue
            if len(row) < 2:
                log.warning(
                    "invite_codes.txt line %d: expected 'code, description' — skipping: %s",
                    line_num, row,
                )
                continue
            code = row[0].strip()
            description = row[1].strip()
            if code:
                tracked[code] = description

    log.info("Loaded %d tracked invite code(s) from %s", len(tracked), path)
    return tracked


# ── Discord API helpers ───────────────────────────────────────────────────────

def _headers() -> dict:
    return {"Authorization": f"Bot {BOT_TOKEN}"}


def fetch_invites(guild_id: str) -> list[dict]:
    """Return the full invite list for the guild."""
    url = f"{API_BASE}/guilds/{guild_id}/invites"
    resp = requests.get(url, headers=_headers(), timeout=10)

    if resp.status_code == 401:
        raise PermissionError("Invalid bot token — check DISCORD_BOT_TOKEN in .env")
    if resp.status_code == 403:
        raise PermissionError(
            "Bot lacks 'Manage Guild' permission on this server."
        )
    resp.raise_for_status()
    return resp.json()


def post_message(channel_id: str, content: str) -> None:
    """Post a message to a Discord channel."""
    url = f"{API_BASE}/channels/{channel_id}/messages"
    payload = {"content": content}
    resp = requests.post(url, headers=_headers(), json=payload, timeout=10)

    if resp.status_code == 403:
        raise PermissionError(
            f"Bot cannot send messages to channel {channel_id}. "
            "Check 'Send Messages' permission."
        )
    resp.raise_for_status()
    log.info("Message posted to channel %s", channel_id)


# ── Report builder ────────────────────────────────────────────────────────────

def build_report(
    tracked_codes: dict[str, str],
    invites: list[dict],
    report_month: str,
) -> str:
    """
    Build the Discord message to post in the admin channel.

    Only includes codes listed in invite_codes.txt.
    Codes listed in the file but not found on Discord are flagged.
    """
    invite_map: dict[str, dict] = {inv["code"]: inv for inv in invites}

    lines = [
        f"\U0001f4ca **Monthly Invite Report \u2014 {report_month}**",
        "\u2500" * 36,
    ]

    found_any = False
    for code, description in tracked_codes.items():
        inv = invite_map.get(code)
        if inv is None:
            lines.append(
                f"\u26a0\ufe0f  `{code}` \u2014 {description}  "
                "*(invite not found or deleted)*"
            )
            continue

        uses     = inv.get("uses", 0)
        max_uses = inv.get("max_uses") or "\u221e"
        inviter  = inv.get("inviter", {}).get("username", "unknown")

        lines.append(
            f"\U0001f517 **{description}**\n"
            f"   Code: `{code}` | Uses this period: **{uses}** / {max_uses} "
            f"| Created by: {inviter}"
        )
        found_any = True

    if not found_any:
        lines.append("No tracked invite codes were found on this server.")

    lines.append("\u2500" * 36)
    lines.append(
        f"_Report generated "
        f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}_"
    )

    return "\n".join(lines)


# ── Scheduler ─────────────────────────────────────────────────────────────────

def seconds_until_first_of_next_month() -> float:
    """Return how many seconds until midnight UTC on the 1st of next month."""
    now = datetime.now(timezone.utc)
    if now.month == 12:
        target = datetime(now.year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        target = datetime(now.year, now.month + 1, 1, tzinfo=timezone.utc)
    return max((target - now).total_seconds(), 0)


def is_first_of_month() -> bool:
    return datetime.now(timezone.utc).day == 1


# ── Main run logic ────────────────────────────────────────────────────────────

def run_report(tracked_codes: dict[str, str]) -> None:
    """Fetch invites, build the report, and post it to the admin channel."""
    log.info("Fetching invite data from Discord …")
    invites = fetch_invites(GUILD_ID)

    report_month = datetime.now(timezone.utc).strftime("%B %Y")
    message = build_report(tracked_codes, invites, report_month)

    log.info("Posting report to admin channel %s …", ADMIN_CHANNEL_ID)
    post_message(ADMIN_CHANNEL_ID, message)
    log.info("Report posted successfully.")


def run_scheduler(tracked_codes: dict[str, str]) -> None:
    """
    Loop forever, posting a report on the 1st of each month at midnight UTC.

    If today is already the 1st when the script starts, post immediately
    then wait for the following month.
    """
    log.info("Scheduler started. Will post on the 1st of each month (midnight UTC).")

    if is_first_of_month():
        log.info("Today is the 1st — posting now.")
        run_report(tracked_codes)

    while True:
        wait = seconds_until_first_of_next_month()
        next_run = datetime.now(timezone.utc) + timedelta(seconds=wait)
        log.info(
            "Next report: %s  (%.1f hours away)",
            next_run.strftime("%Y-%m-%d %H:%M UTC"),
            wait / 3600,
        )
        time.sleep(wait)

        try:
            run_report(tracked_codes)
        except Exception as exc:
            log.error("Report failed: %s — will retry next month.", exc)


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Post a monthly Discord invite usage report to your admin channel."
    )
    parser.add_argument(
        "--now",
        action="store_true",
        help="Post the report immediately and exit (good for testing)",
    )
    parser.add_argument(
        "--codes-file",
        default=INVITE_CODES_FILE,
        metavar="FILE",
        help=f"Path to invite codes file (default: {INVITE_CODES_FILE})",
    )
    args = parser.parse_args()

    errors = []
    if not BOT_TOKEN:
        errors.append("DISCORD_BOT_TOKEN is not set in .env")
    if not GUILD_ID:
        errors.append("DISCORD_GUILD_ID is not set in .env")
    if not ADMIN_CHANNEL_ID:
        errors.append("DISCORD_ADMIN_CHANNEL_ID is not set in .env")
    if errors:
        for e in errors:
            log.error(e)
        raise SystemExit(1)

    try:
        tracked_codes = load_tracked_codes(args.codes_file)
    except FileNotFoundError as exc:
        log.error("%s", exc)
        raise SystemExit(1)

    if not tracked_codes:
        log.error("No valid invite codes found in %s — nothing to track.", args.codes_file)
        raise SystemExit(1)

    try:
        if args.now:
            run_report(tracked_codes)
        else:
            run_scheduler(tracked_codes)
    except PermissionError as exc:
        log.error("%s", exc)
        raise SystemExit(1)
    except KeyboardInterrupt:
        log.info("Stopped by user.")


if __name__ == "__main__":
    main()