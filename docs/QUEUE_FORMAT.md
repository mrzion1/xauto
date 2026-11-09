# Queue format (`data/queue.json`)

The queue is a single JSON file. Xauto watches it and re-renders as soon as
it changes, so it can be filled by hand, by a script or by an AI assistant
while the app is open.

See [`examples/queue.example.json`](../examples/queue.example.json) for a full file.

## Top level

| Field            | Type   | Notes                         |
|------------------|--------|-------------------------------|
| `schema_version` | int    | Currently `1`.                |
| `posts`          | array  | Any order, the app sorts by time. |

## Post

| Field          | Type            | Required | Notes |
|----------------|-----------------|----------|-------|
| `id`           | string          | no       | Any unique string. Generated when missing. |
| `account`      | string          | yes      | Handle of an added account, with or without `@`. |
| `scheduled_at` | ISO 8601 string | yes      | `2026-11-10T14:00+03:00`. Without an offset the PC's local time is assumed. |
| `text`         | string          | yes      | Post body exactly as it should appear on X. |
| `media`        | array of string | no       | File names inside `data/media/` (up to 4 images or 1 video). |
| `status`       | enum            | no       | `draft` (default) → `approved` → `scheduled` → `published`, or `failed`. |
| `telegram`     | enum            | no       | `pending` (default), `sent`, `missed`, `skipped`, `off`. |
| `tweet_url`    | string          | no       | Filled by the app once the post is live. |
| `error`        | string          | no       | Last error, filled by the app. |

## Rules of thumb for whoever fills the queue

- Only `draft` posts should be written from outside the app. Everything after
  `approved` is owned by the app.
- Keep at least a couple of hours between posts of the same account.
- The account card shows the date of the **latest** planned post, so filling
  the queue a few days ahead keeps the card green.
