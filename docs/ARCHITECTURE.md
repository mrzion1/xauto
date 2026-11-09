# Architecture

```
main.py                  entry point
xauto/
├── app.py               window setup, root layout
├── config.py            paths + Settings (config/settings.json)
├── models.py            Account, Post and their enums
├── storage.py           JSON repositories with atomic writes
├── i18n.py              RU / EN strings
├── services/
│   ├── adspower.py      AdsPower Local API + Chrome DevTools tab opening
│   └── x_profile.py     public profile lookup (name, avatar)
└── ui/
    ├── theme.py         design tokens and shared widgets
    ├── background.py    animated particle backdrop
    ├── account_card.py  one account on the home screen
    ├── dialogs.py       add / edit / delete dialogs
    ├── formatting.py    date helpers
    └── home.py          home screen
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
