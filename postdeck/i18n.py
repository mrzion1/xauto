"""Tiny translation table. UI strings live here, never inline in widgets."""

from __future__ import annotations

_STRINGS: dict[str, dict[str, str]] = {
    "ru": {
        "app.subtitle": "Планирование постов для X",
        "home.accounts": "Аккаунты",
        "home.add": "Добавить аккаунт",
        "home.refresh": "Обновить",
        "home.empty.title": "Пока ни одного аккаунта",
        "home.empty.hint": "Добавь аккаунт X и укажи ID его профиля в AdsPower.",
        "stats.accounts": "аккаунтов",
        "stats.queued": "постов в очереди",
        "stats.refill": "нужно заполнить",
        "stats.adspower.on": "AdsPower подключен",
        "stats.adspower.off": "AdsPower не найден",
        "card.queue.empty": "Очередь пуста",
        "card.queue.until": "Посты до {date}",
        "card.queue.days": "ещё {days} дн.",
        "card.queue.today": "заканчиваются сегодня",
        "card.queue.over": "закончились {days} дн. назад",
        "card.posts": "{count} в очереди",
        "card.open": "Открыть в AdsPower",
        "card.edit": "Изменить",
        "card.delete": "Удалить",
        "card.opening": "Открываю профиль {handle}…",
        "card.opened": "Профиль {handle} открыт",
        "dialog.add.title": "Новый аккаунт",
        "dialog.edit.title": "Аккаунт {handle}",
        "dialog.handle": "Юзернейм X",
        "dialog.handle.hint": "например, @username",
        "dialog.adspower": "ID профиля в AdsPower",
        "dialog.adspower.hint": "колонка «ID» в списке профилей",
        "dialog.name": "Имя (необязательно)",
        "dialog.name.hint": "подтянется автоматически",
        "dialog.save": "Сохранить",
        "dialog.cancel": "Отмена",
        "dialog.required": "Обязательное поле",
        "dialog.duplicate": "Такой аккаунт уже добавлен",
        "dialog.delete.title": "Удалить {handle}?",
        "dialog.delete.body": "Аккаунт пропадёт из списка. Посты в очереди и профиль AdsPower не трогаются.",
        "dialog.delete.confirm": "Удалить",
        "toast.saved": "Аккаунт {handle} сохранён",
        "toast.deleted": "Аккаунт {handle} удалён",
        "toast.synced": "Профили обновлены",
        "lang.switch": "EN",
    },
    "en": {
        "app.subtitle": "Post planning for X",
        "home.accounts": "Accounts",
        "home.add": "Add account",
        "home.refresh": "Refresh",
        "home.empty.title": "No accounts yet",
        "home.empty.hint": "Add an X account and enter the id of its AdsPower profile.",
        "stats.accounts": "accounts",
        "stats.queued": "posts queued",
        "stats.refill": "need refill",
        "stats.adspower.on": "AdsPower connected",
        "stats.adspower.off": "AdsPower not found",
        "card.queue.empty": "Queue is empty",
        "card.queue.until": "Posts until {date}",
        "card.queue.days": "{days} days left",
        "card.queue.today": "ends today",
        "card.queue.over": "ran out {days} days ago",
        "card.posts": "{count} queued",
        "card.open": "Open in AdsPower",
        "card.edit": "Edit",
        "card.delete": "Delete",
        "card.opening": "Opening {handle}…",
        "card.opened": "{handle} is open",
        "dialog.add.title": "New account",
        "dialog.edit.title": "Account {handle}",
        "dialog.handle": "X username",
        "dialog.handle.hint": "e.g. @username",
        "dialog.adspower": "AdsPower profile ID",
        "dialog.adspower.hint": "the “ID” column in AdsPower",
        "dialog.name": "Display name (optional)",
        "dialog.name.hint": "fetched automatically",
        "dialog.save": "Save",
        "dialog.cancel": "Cancel",
        "dialog.required": "Required",
        "dialog.duplicate": "This account is already added",
        "dialog.delete.title": "Delete {handle}?",
        "dialog.delete.body": "The account is removed from the list. Queued posts and the AdsPower profile stay untouched.",
        "dialog.delete.confirm": "Delete",
        "toast.saved": "{handle} saved",
        "toast.deleted": "{handle} deleted",
        "toast.synced": "Profiles refreshed",
        "lang.switch": "RU",
    },
}

_language = "ru"


def set_language(code: str) -> None:
    global _language
    _language = code if code in _STRINGS else "ru"


def get_language() -> str:
    return _language


def t(key: str, **kwargs: object) -> str:
    """Translate ``key``; falls back to English, then to the key itself."""
    template = _STRINGS[_language].get(key) or _STRINGS["en"].get(key) or key
    return template.format(**kwargs) if kwargs else template
