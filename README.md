<div align="center">

<img src="assets/icon.png" alt="Xauto icon" width="96">

# Xauto

**A local desktop dashboard for planning X (Twitter) posts across several accounts, built on top of AdsPower browser profiles.**

![Python](https://img.shields.io/badge/python-3.11+-111?logo=python&logoColor=white)
![Flet](https://img.shields.io/badge/UI-Flet-111)
![Platform](https://img.shields.io/badge/platform-Windows-111)
![License](https://img.shields.io/badge/license-MIT-111)

<img src="docs/img/home.png" alt="Xauto home screen" width="860">

</div>

---

## Why

Running a few X accounts usually means a separate anti-detect browser profile
per account, a pile of drafts somewhere, and no quick way to see which account
is about to run out of planned posts. Xauto keeps all of that on one screen:

- every account as a card with its avatar, name and `@handle`;
- **one click opens the account** in its own AdsPower profile, straight on the
  X profile page, with that profile's fingerprint and proxy;
- a **traffic light per account** showing until when posts are planned
  (green: fine, yellow: refill soon, red: empty);
- a plain JSON **post queue** that can be filled by hand, by a script or by an
  AI assistant, and is picked up live while the app is open.

Everything runs locally. No accounts, cookies or proxies leave your machine.

## Features

| Status | Feature |
|:------:|---------|
| ✅ | Account list with avatars and names fetched automatically |
| ✅ | Open an account in its AdsPower profile on `x.com/<handle>` |
| ✅ | Queue overview: last planned post, days left, posts queued |
| ✅ | Live reload when `data/queue.json` changes |
| ✅ | Russian / English UI |
| ✅ | Posts screen per account, grouped by day, with media thumbnails |
| ✅ | Preview that looks like the real post on X (text, images, video with duration), approve / unapprove |
| ✅ | CLI to add posts safely: `python -m xauto add-post ...` |
| ✅ | Push approved posts into X's native scheduler through AdsPower, with a request guard that checks time, text and media before X accepts anything |
| 🚧 | Share published posts to Telegram chats |

## Requirements

- Windows 10 / 11
- Python **3.11+** on `PATH`
- [FFmpeg](https://ffmpeg.org/) on `PATH` (video thumbnails in the preview; optional)
- [AdsPower](https://www.adspower.com/) with the **Local API** enabled
  (*AdsPower → Automation → API*). The free plan is enough: Xauto only
  starts profiles, it does not list them.

## Quick start

```bash
git clone https://github.com/mrzion1/xauto.git
cd xauto
start.bat
```

`start.bat` creates a virtual environment on the first run, installs the
dependencies and launches the app. Later runs start instantly.

Then:

1. Click **Add account**.
2. Enter the X username and the **profile ID** from AdsPower (the `ID` column in the profile list).
3. The name and avatar are fetched automatically; the card appears on the home screen.
4. Use **Open in AdsPower** to jump into that account.

## Configuration

On first launch `config/settings.example.json` is copied to
`config/settings.json` (git-ignored):

```json
{
  "language": "ru",
  "adspower_api_url": "http://127.0.0.1:50325",
  "adspower_api_key": "",
  "refill_warning_days": 2
}
```

| Key | Meaning |
|-----|---------|
| `language` | `ru` or `en` (also switchable in the header). |
| `adspower_api_url` | Local API address shown in AdsPower's API settings. |
| `adspower_api_key` | Only if API key verification is turned on in AdsPower. |
| `refill_warning_days` | A card turns yellow when its queue ends within this many days. |

## Post queue

Posts live in `data/queue.json`, attachments in `data/posts/<id>/`. Add them
with `python -m xauto add-post` (validates everything) or by editing the file.
The format is documented in
[docs/QUEUE_FORMAT.md](docs/QUEUE_FORMAT.md), with a ready-to-copy example in
[examples/queue.example.json](examples/queue.example.json).

## Scheduling on X

Approved posts go into X's own scheduler, so they are published even when
your PC is off.

```bash
python -m xauto schedule --account your_handle --dry-run   # full run, nothing created
python -m xauto schedule --account your_handle             # live
```

or press **Schedule on X** on the account's posts screen.

The bot opens the account's AdsPower profile, types the post, uploads the
media and fills X's schedule dialog. The browser's own clock converts the
time, so the profile's time zone (set by its proxy) never shifts a post.
Right before X receives the request, Xauto intercepts `CreateScheduledTweet`
and compares the UTC send time, the exact text and the attachment count with
the queue. On any mismatch the request is dropped and the post is marked
failed with a screenshot in its folder.

Requires Playwright (`pip install -r requirements.txt`); no separate browser
download is needed because it attaches to AdsPower's browser.

## Privacy

This repository is public, your data is not:

- `data/` (accounts, AdsPower IDs, avatars, queue, media) and
  `config/settings.json` are git-ignored;
- a **pre-commit hook** scans every commit for IP addresses, proxies, API keys,
  tokens and e-mails, and blocks it if anything is found. Enable it once per clone:

  ```bash
  git config core.hooksPath .githooks
  ```

- CI runs the same scan over the whole repository on every push.

## Development

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-dev.txt
git config core.hooksPath .githooks

python -m pytest           # unit tests
python main.py             # run the app
python scripts/build_icon.py  # regenerate assets/icon.png and icon.ico
```

Project layout and design decisions: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## License

[MIT](LICENSE)
