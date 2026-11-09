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
        "stats.accounts": "аккаунт|аккаунта|аккаунтов",
        "stats.queued": "пост в очереди|поста в очереди|постов в очереди",
        "stats.refill": "нужно заполнить",
        "stats.adspower.on": "AdsPower подключен",
        "stats.adspower.off": "AdsPower не найден",
        "card.queue.empty": "Очередь пуста",
        "card.queue.until": "Посты до {date}",
        "card.queue.days": "ещё {days} дн.",
        "card.queue.today": "заканчиваются сегодня",
        "card.queue.over": "закончились {days} дн. назад",
        "card.posts": "{count} в очереди",
        "card.open": "AdsPower",
        "card.open.tooltip": "Открыть аккаунт в его профиле AdsPower",
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
        "card.posts.open": "Посты",
        "status.draft": "Черновик",
        "status.approved": "Одобрен",
        "status.scheduled": "В отложке",
        "status.published": "Опубликован",
        "status.failed": "Ошибка",
        "count.draft": "черновик|черновика|черновиков",
        "count.approved": "одобрен|одобрено|одобрено",
        "count.scheduled": "в отложке|в отложке|в отложке",
        "count.published": "опубликован|опубликовано|опубликовано",
        "count.failed": "ошибка|ошибки|ошибок",
        "posts.title": "посты",
        "posts.back": "Назад",
        "posts.total": "постов",
        "posts.approve_all": "Одобрить все черновики",
        "posts.empty.title": "Постов пока нет",
        "posts.empty.hint": "Как только Claude добавит посты в очередь, они появятся здесь.",
        "posts.gone": "Пост уже удалён из очереди",
        "posts.toast.approved": "Пост одобрен",
        "posts.toast.draft": "Пост возвращён в черновики",
        "posts.toast.approved_all": "Одобрено постов: {count}",
        "preview.when": "Выйдет {date}",
        "preview.length": "{count} симв.",
        "preview.premium": "длиннее 280, нужен Premium",
        "preview.folder": "Папка поста",
        "preview.no_folder": "У поста нет папки с файлами",
        "preview.open_file": "Открыть файл",
        "preview.missing": "Файл не найден: {name}",
        "preview.close": "Закрыть",
        "preview.approve": "Одобрить",
        "preview.unapprove": "Вернуть в черновик",
        "preview.retry": "Повторить",
        "preview.open_on_x": "Открыть в X",
        "preview.tg.pending": "Ссылка придёт в Telegram после выхода",
        "preview.tg.sent": "Ссылка отправлена в Telegram",
        "preview.tg.missed": "Пост не найден, отправлена ссылка на профиль",
        "preview.tg.skipped": "Рассылка пропущена",
        "posts.schedule": "В отложку X",
        "posts.schedule.nothing": "Нет одобренных постов на будущее",
        "posts.schedule.started": "Ставлю в отложку X: {count}. Не закрывай AdsPower.",
        "posts.schedule.failed": "Не удалось: {error}",
        "posts.schedule.done": "В отложке: {done} из {total}",
    },
    "en": {
        "app.subtitle": "Post planning for X",
        "home.accounts": "Accounts",
        "home.add": "Add account",
        "home.refresh": "Refresh",
        "home.empty.title": "No accounts yet",
        "home.empty.hint": "Add an X account and enter the id of its AdsPower profile.",
        "stats.accounts": "account|accounts",
        "stats.queued": "post queued|posts queued",
        "stats.refill": "need refill",
        "stats.adspower.on": "AdsPower connected",
        "stats.adspower.off": "AdsPower not found",
        "card.queue.empty": "Queue is empty",
        "card.queue.until": "Posts until {date}",
        "card.queue.days": "{days} days left",
        "card.queue.today": "ends today",
        "card.queue.over": "ran out {days} days ago",
        "card.posts": "{count} queued",
        "card.open": "AdsPower",
        "card.open.tooltip": "Open the account in its AdsPower profile",
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
        "card.posts.open": "Posts",
        "status.draft": "Draft",
        "status.approved": "Approved",
        "status.scheduled": "Scheduled",
        "status.published": "Published",
        "status.failed": "Failed",
        "count.draft": "draft|drafts",
        "count.approved": "approved|approved",
        "count.scheduled": "scheduled|scheduled",
        "count.published": "published|published",
        "count.failed": "failed|failed",
        "posts.title": "posts",
        "posts.back": "Back",
        "posts.total": "posts",
        "posts.approve_all": "Approve all drafts",
        "posts.empty.title": "No posts yet",
        "posts.empty.hint": "Posts appear here as soon as they are added to the queue.",
        "posts.gone": "This post is no longer in the queue",
        "posts.toast.approved": "Post approved",
        "posts.toast.draft": "Post moved back to drafts",
        "posts.toast.approved_all": "Approved: {count}",
        "preview.when": "Goes out {date}",
        "preview.length": "{count} chars",
        "preview.premium": "over 280, needs Premium",
        "preview.folder": "Post folder",
        "preview.no_folder": "This post has no media folder",
        "preview.open_file": "Open file",
        "preview.missing": "File not found: {name}",
        "preview.close": "Close",
        "preview.approve": "Approve",
        "preview.unapprove": "Back to draft",
        "preview.retry": "Retry",
        "preview.open_on_x": "Open on X",
        "preview.tg.pending": "Link goes to Telegram once it is live",
        "preview.tg.sent": "Link sent to Telegram",
        "preview.tg.missed": "Post not found, profile link sent",
        "preview.tg.skipped": "Sharing skipped",
        "posts.schedule": "Schedule on X",
        "posts.schedule.nothing": "No approved future posts",
        "posts.schedule.started": "Scheduling {count} on X. Keep AdsPower open.",
        "posts.schedule.failed": "Failed: {error}",
        "posts.schedule.done": "Scheduled: {done} of {total}",
    },
}

_language = "ru"


def set_language(code: str) -> None:
    global _language
    _language = code if code in _STRINGS else "ru"


def get_language() -> str:
    return _language


def plural(key: str, count: int) -> str:
    """Pick the right word form for ``count``.

    Forms are stored in one string separated by '|':
    ru = "one|few|many" (1 пост, 2 поста, 5 постов), en = "one|other".
    """
    forms = t(key).split("|")
    if _language == "ru" and len(forms) == 3:
        tail10, tail100 = count % 10, count % 100
        if tail10 == 1 and tail100 != 11:
            return forms[0]
        if 2 <= tail10 <= 4 and not 12 <= tail100 <= 14:
            return forms[1]
        return forms[2]
    return forms[0] if count == 1 else forms[-1]


def t(key: str, **kwargs: object) -> str:
    """Translate ``key``; falls back to English, then to the key itself."""
    template = _STRINGS[_language].get(key) or _STRINGS["en"].get(key) or key
    return template.format(**kwargs) if kwargs else template
