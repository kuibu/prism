# Telegram Bridge Research Notes

This project now includes a lightweight real Telegram bridge path in gateway API.

## Upstream references reviewed

- Matrix Telegram bridge (legacy appservice):
  - https://github.com/matrix-org/matrix-appservice-telegram
- Mautrix Telegram bridge (actively used Matrix bridge implementation):
  - https://github.com/mautrix/telegram
- Telegram Bot API (official):
  - https://core.telegram.org/bots/api

## Design choice in this repo

Instead of embedding a full Matrix AppService bridge runtime, the MVP implements:
- `POST /api/v1/bridges/telegram/poll` (Bot API `getUpdates` -> Matrix relay)
- `POST /api/v1/bridges/telegram/send` (Matrix text -> Bot API `sendMessage`)

Why:
- Fast integration with existing policy/audit gateway.
- Keeps all bridge allow/deny and execution records in immudb audit chain.
- Allows immediate manual end-to-end validation from the existing web bridge test tab.

## Scope note

This is a pragmatic MVP bridge path, not a replacement for full appservice-grade Telegram bridging.
Future production hardening can migrate to dedicated bridge workers/webhook ingestion and stronger secret management.
