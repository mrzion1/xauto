<div align="center">

# Postdeck

**A local desktop dashboard for planning X (Twitter) posts across several accounts, built on top of AdsPower browser profiles.**

![Python](https://img.shields.io/badge/python-3.11+-111?logo=python&logoColor=white)
![Flet](https://img.shields.io/badge/UI-Flet-111)
![Platform](https://img.shields.io/badge/platform-Windows-111)
![License](https://img.shields.io/badge/license-MIT-111)

<img src="docs/img/home.png" alt="Postdeck home screen" width="860">

</div>

---

## Why

Running a few X accounts usually means a separate anti-detect browser profile
per account, a pile of drafts somewhere, and no quick way to see which account
is about to run out of planned posts. Postdeck keeps all of that on one screen:

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
| 🚧 | Review and approve queued posts in the app |
| 🚧 | Push approved posts into X's native scheduler through AdsPower |
| 🚧 | Share published posts to Telegram chats |

## Requirements

- Windows 10 / 11
- Python **3.11+** on `PATH`
- [AdsPower](https://www.adspower.com/) with the **Local API** enabled
  (*AdsPower → Automation → API*). The free plan is enough: Postdeck only
  starts profiles, it does not list them.

## Quick start

```bash
git clone https://github.com/mrzion1/postdeck.git
cd postdeck
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

Posts live in `data/queue.json`. The format is documented in
[docs/QUEUE_FORMAT.md](docs/QUEUE_FORMAT.md), with a ready-to-copy example in
[examples/queue.example.json](examples/queue.example.json).

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
```

Project layout and design decisions: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## License

[MIT](LICENSE)
