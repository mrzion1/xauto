# Architecture

```
main.py                  entry point (GUI)
xauto/
├── __main__.py          `python -m xauto <command>` (CLI)
├── cli.py               add-post / list / move / shift / schedule / set-status / remove
├── scheduling.py        use case: approved posts -> X scheduler, saves every outcome
├── notify.py            use case: live post -> link -> your Telegram bot
├── app.py               window setup
├── config.py            paths + Settings (config/settings.json)
├── models.py            Account, Post and their enums
├── storage.py           JSON repositories with atomic writes
├── i18n.py              RU / EN strings
├── services/
│   ├── adspower.py      AdsPower Local API + Chrome DevTools tab opening
│   ├── media.py         attachment types, ffmpeg thumbnails, durations
│   ├── x_scheduler.py   Playwright over CDP: compose, upload, schedule + request guard
│   ├── x_timeline.py    finds a published post's URL on the profile page
│   ├── telegram_bot.py  Bot API: send message, discover your chat id
│   └── x_profile.py     public profile lookup (name, avatar)
└── ui/
    ├── shell.py         root Stack + navigation between screens
    ├── theme.py         design tokens and shared widgets
    ├── common.py        toasts, background threads, file watcher, avatar
    ├── background.py    animated particle backdrop
    ├── home.py          home screen
    ├── account_card.py  one account on the home screen
    ├── posts.py         an account's queue, grouped by day
    ├── preview.py       post preview styled like X, approve / unapprove
    ├── status.py        status colors and chips
    ├── dialogs.py       add / edit / delete dialogs
    └── formatting.py    dates, durations, plural-safe helpers
scripts/
├── build_icon.py        renders assets/icon.png + icon.ico with Pillow
└── check_secrets.py     pre-commit / CI scan for private data
```

## Principles

- **UI never talks to files or the network directly.** It goes through
  `storage` and `services`, which are plain Python and covered by tests.
- **Private data stays in `data/` and `config/settings.json`.** Both are
  git-ignored; a pre-commit hook (`scripts/check_secrets.py`) blocks IPs,
  proxies, keys and e-mails from ever reaching the repository.
- **Slow work runs in background threads** (AdsPower calls, avatar downloads),
  so the window never freezes.
- **The browser fingerprint is AdsPower's job.** Xauto only asks AdsPower
  to open a profile and then opens a tab through that browser's own DevTools
  port, so every account keeps its own fingerprint and proxy.
