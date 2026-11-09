"""Command line interface for filling the queue from scripts (or an AI assistant).

    python -m xauto add-post --account workmadz --at "2026-11-10 19:45" \\
        --text-file post.txt --media clip.mp4 --notes notes.txt
    python -m xauto list [--account workmadz]
    python -m xauto set-status <post_id> approved
    python -m xauto move <post_id> --at "2026-11-10 20:05"
    python -m xauto shift --account workmadz --days -1
    python -m xauto schedule --account workmadz [--dry-run] [--post <id>]
    python -m xauto remove <post_id>

Every command goes through the same repositories as the UI, so the queue file
stays valid and the running app picks changes up automatically.
"""

from __future__ import annotations

import argparse
import logging
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .config import ensure_dirs, post_dir
from .models import Post, PostStatus, TelegramStatus, new_id, normalize_handle
from .services.media import is_image, is_video
from .storage import AccountRepository, QueueRepository

MAX_IMAGES = 4
MAX_VIDEOS = 1


class CliError(Exception):
    """User-facing error: printed without a traceback."""


# --- Parsing helpers -----------------------------------------------------------


def parse_when(value: str, tz_offset: str) -> datetime:
    """'2026-11-10 19:45' + '+03:00' -> aware datetime. ISO strings with an offset win."""
    try:
        parsed = datetime.fromisoformat(value.strip().replace(" ", "T"))
    except ValueError as exc:
        raise CliError(f"bad --at value {value!r}, expected 'YYYY-MM-DD HH:MM'") from exc
    if parsed.tzinfo is not None:
        return parsed

    sign = -1 if tz_offset.startswith("-") else 1
    hours, _, minutes = tz_offset.lstrip("+-").partition(":")
    offset = timedelta(hours=int(hours), minutes=int(minutes or 0)) * sign
    return parsed.replace(tzinfo=timezone(offset))


def validate_media(files: list[Path]) -> None:
    for file in files:
        if not file.is_file():
            raise CliError(f"media file not found: {file}")
        if not (is_image(file) or is_video(file)):
            raise CliError(f"unsupported media type: {file.name}")

    videos = [f for f in files if is_video(f)]
    images = [f for f in files if is_image(f)]
    # X rules: up to 4 images, or exactly one video, never mixed.
    if videos and images:
        raise CliError("X does not allow mixing images and a video in one post")
    if len(videos) > MAX_VIDEOS or len(images) > MAX_IMAGES:
        raise CliError(f"too many attachments (max {MAX_IMAGES} images or {MAX_VIDEOS} video)")


# --- Commands --------------------------------------------------------------------


def cmd_add_post(args: argparse.Namespace) -> int:
    handle = normalize_handle(args.account)
    known = {a.handle for a in AccountRepository().load()}
    if handle not in known:
        raise CliError(f"unknown account @{handle}; add it in the app first (known: {', '.join(sorted(known)) or 'none'})")

    text = Path(args.text_file).read_text(encoding="utf-8").strip()
    if not text:
        raise CliError("post text is empty")

    media = [Path(m) for m in args.media]
    validate_media(media)

    post = Post(
        id=new_id(),
        account=handle,
        scheduled_at=parse_when(args.at, args.tz),
        text=text,
        telegram=TelegramStatus.OFF if args.no_telegram else TelegramStatus.PENDING,
    )

    # Copy attachments into the post's own folder so the queue is self-contained.
    folder = post_dir(post.id)
    folder.mkdir(parents=True, exist_ok=True)
    for file in media:
        shutil.copy2(file, folder / file.name)
        post.media.append(file.name)
    if args.notes:
        shutil.copy2(args.notes, folder / "notes.txt")

    QueueRepository().upsert(post)
    print(f"added {post.id}  @{handle}  {post.scheduled_at.isoformat(timespec='minutes')}  media={post.media}")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    repo = QueueRepository()
    posts = repo.for_account(args.account) if args.account else repo.load()
    for post in posts:
        first_line = post.text.splitlines()[0][:70] if post.text else ""
        print(f"{post.id}  {post.scheduled_at:%Y-%m-%d %H:%M %z}  @{post.account:<16} {post.status.value:<10} {first_line}")
    if not posts:
        print("queue is empty")
    return 0


def cmd_set_status(args: argparse.Namespace) -> int:
    repo = QueueRepository()
    post = repo.get(args.post_id)
    if post is None:
        raise CliError(f"no post with id {args.post_id}")
    post.status = PostStatus(args.status)
    repo.upsert(post)
    print(f"{post.id} -> {post.status.value}")
    return 0


def cmd_move(args: argparse.Namespace) -> int:
    repo = QueueRepository()
    post = repo.get(args.post_id)
    if post is None:
        raise CliError(f"no post with id {args.post_id}")
    post.scheduled_at = parse_when(args.at, args.tz)
    repo.upsert(post)
    print(f"{post.id} -> {post.scheduled_at.isoformat(timespec='minutes')}")
    return 0


# Posts already handed to X can't be moved from here: X owns their time now.
MOVABLE = {PostStatus.DRAFT, PostStatus.APPROVED}


def cmd_shift(args: argparse.Namespace) -> int:
    handle = normalize_handle(args.account)
    delta = timedelta(days=args.days, minutes=args.minutes)
    repo = QueueRepository()
    posts = repo.load()
    moved = [p for p in posts if p.account == handle and p.status in MOVABLE]
    for post in moved:
        post.scheduled_at += delta
    repo.save(posts)
    for post in moved:
        print(f"{post.id} -> {post.scheduled_at.isoformat(timespec='minutes')}")
    print(f"shifted {len(moved)} post(s) of @{handle} by {delta}")
    return 0


def cmd_schedule(args: argparse.Namespace) -> int:
    # Imported here so the light commands don't need Playwright installed.
    from .config import Settings
    from .scheduling import pending_posts, schedule_account

    handle = normalize_handle(args.account)
    account = next((a for a in AccountRepository().load() if a.handle == handle), None)
    if account is None:
        raise CliError(f"unknown account @{handle}")

    wanted = set(args.post) if args.post else None
    todo = pending_posts(handle, post_ids=wanted)
    if not todo:
        print("nothing to schedule (needs approved posts in the future)")
        return 0
    mode = "DRY RUN, nothing will be created on X" if args.dry_run else "LIVE"
    print(f"{mode}: {len(todo)} post(s) for @{handle}")

    def report(result) -> None:
        mark = "ok  " if result.ok else "FAIL"
        extra = f"  screenshot: {result.screenshot}" if result.screenshot else ""
        print(f"  {mark} {result.post_id}  {result.message}{extra}", flush=True)

    results = schedule_account(account, Settings.load(), dry_run=args.dry_run, post_ids=wanted, on_result=report)
    return 0 if all(r.ok for r in results) else 1


def cmd_notify(args: argparse.Namespace) -> int:
    from .config import DATA_DIR, Settings
    from .notify import run_notify

    # The scheduled task has no console, so everything also goes to data/notify.log.
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[logging.FileHandler(DATA_DIR / "notify.log", encoding="utf-8")]
        + ([logging.StreamHandler()] if sys.stderr else []),  # pythonw has no stderr
    )
    try:
        report = run_notify(Settings.load())
    except Exception:
        logging.exception("notify failed")
        return 1
    if report.sent or report.waiting or report.gave_up:
        logging.info("sent=%d waiting=%d gave_up=%d", report.sent, report.waiting, report.gave_up)
    return 0


def cmd_telegram_setup(args: argparse.Namespace) -> int:
    from .config import Settings
    from .services.telegram_bot import TelegramBot, TelegramError

    settings = Settings.load()
    if args.token:
        settings.telegram_bot_token = args.token.strip()
    try:
        bot = TelegramBot(settings.telegram_bot_token)
        name = bot.bot_username()
        chat_id = bot.latest_private_chat_id()
        if chat_id is None:
            raise CliError(f"open t.me/{name}, press Start (or send any message), then run this again")
        bot.send(chat_id, "Xauto подключен. Сюда будут приходить ссылки на вышедшие посты.")
    except TelegramError as exc:
        raise CliError(f"telegram: {exc}") from exc

    settings.telegram_chat_id = str(chat_id)
    settings.save()
    print(f"connected to @{name}, test message sent, settings saved")
    return 0


TASK_NAME = "Xauto notify"


def cmd_install_task(args: argparse.Namespace) -> int:
    """Register a Windows scheduled task that runs `notify` every N minutes, without a console window."""
    from .config import ROOT_DIR

    pythonw = Path(sys.executable).with_name("pythonw.exe")
    runner = ROOT_DIR / "scripts" / "notify_task.pyw"
    action = f'"{pythonw}" "{runner}"'
    result = subprocess.run(
        ["schtasks", "/Create", "/F", "/SC", "MINUTE", "/MO", str(args.every), "/TN", TASK_NAME, "/TR", action],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise CliError(f"schtasks failed: {result.stderr.strip() or result.stdout.strip()}")
    print(f"task '{TASK_NAME}' installed: every {args.every} min -> {action}")
    return 0


def cmd_uninstall_task(args: argparse.Namespace) -> int:
    result = subprocess.run(["schtasks", "/Delete", "/F", "/TN", TASK_NAME], capture_output=True, text=True)
    print(result.stdout.strip() or result.stderr.strip())
    return 0


def cmd_remove(args: argparse.Namespace) -> int:
    repo = QueueRepository()
    if repo.get(args.post_id) is None:
        raise CliError(f"no post with id {args.post_id}")
    repo.delete(args.post_id)
    shutil.rmtree(post_dir(args.post_id), ignore_errors=True)
    print(f"removed {args.post_id}")
    return 0


# --- Entry point -------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="xauto", description="Xauto queue tools")
    sub = parser.add_subparsers(dest="command", required=True)

    add = sub.add_parser("add-post", help="add a draft post to the queue")
    add.add_argument("--account", required=True, help="handle, with or without @")
    add.add_argument("--at", required=True, help="'YYYY-MM-DD HH:MM' (or ISO with offset)")
    add.add_argument("--tz", default="+03:00", help="UTC offset for --at without one (default Moscow, +03:00)")
    add.add_argument("--text-file", required=True, help="UTF-8 file with the post text")
    add.add_argument("--media", nargs="*", default=[], help="up to 4 images or 1 video")
    add.add_argument("--notes", help="sources / notes file, stored as notes.txt next to the media")
    add.add_argument("--no-telegram", action="store_true", help="do not share this post to Telegram chats")
    add.set_defaults(handler=cmd_add_post)

    lst = sub.add_parser("list", help="show the queue")
    lst.add_argument("--account")
    lst.set_defaults(handler=cmd_list)

    status = sub.add_parser("set-status", help="change a post's status")
    status.add_argument("post_id")
    status.add_argument("status", choices=[s.value for s in PostStatus])
    status.set_defaults(handler=cmd_set_status)

    move = sub.add_parser("move", help="set a new time for one post")
    move.add_argument("post_id")
    move.add_argument("--at", required=True, help="'YYYY-MM-DD HH:MM' (or ISO with offset)")
    move.add_argument("--tz", default="+03:00", help="UTC offset for --at without one (default Moscow)")
    move.set_defaults(handler=cmd_move)

    shift = sub.add_parser("shift", help="move all draft/approved posts of an account by N days / minutes")
    shift.add_argument("--account", required=True)
    shift.add_argument("--days", type=int, default=0, help="negative = earlier")
    shift.add_argument("--minutes", type=int, default=0)
    shift.set_defaults(handler=cmd_shift)

    schedule = sub.add_parser("schedule", help="put approved posts into X's scheduler via AdsPower")
    schedule.add_argument("--account", required=True)
    schedule.add_argument("--post", action="append", help="only these post ids (repeatable)")
    schedule.add_argument("--dry-run", action="store_true",
                          help="do everything but abort X's final request (nothing is created)")
    schedule.set_defaults(handler=cmd_schedule)

    notify = sub.add_parser("notify", help="send links of posts that went live to your Telegram bot")
    notify.set_defaults(handler=cmd_notify)

    tg = sub.add_parser("telegram-setup", help="connect your Telegram bot (token from @BotFather)")
    tg.add_argument("--token", help="bot token; saved to config/settings.json (git-ignored)")
    tg.set_defaults(handler=cmd_telegram_setup)

    task = sub.add_parser("install-task", help="run `notify` automatically via Windows Task Scheduler")
    task.add_argument("--every", type=int, default=10, help="minutes between runs (default 10)")
    task.set_defaults(handler=cmd_install_task)

    untask = sub.add_parser("uninstall-task", help="remove the scheduled task")
    untask.set_defaults(handler=cmd_uninstall_task)

    remove = sub.add_parser("remove", help="delete a post and its folder")
    remove.add_argument("post_id")
    remove.set_defaults(handler=cmd_remove)
    return parser


def main(argv: list[str] | None = None) -> int:
    ensure_dirs()
    args = build_parser().parse_args(argv)
    try:
        return args.handler(args)
    except CliError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
