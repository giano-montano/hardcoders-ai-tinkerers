---
name: medisaving-ux
description: Render and interpret Medisaving CLI presentation results for Telegram without sending messages or recalculating rankings.
---

# Medisaving UX

Use this skill when preparing Telegram-facing prescription-search messages from Medisaving Ranking v1 artifacts.

- Run `python -m medisaving ux telegram RESULT_ID` for a concise, plain-text result. Add `--expand` only when the user asks to see every ranked option.
- Interpret a partial source as limited to its stated scope. Never claim country-wide coverage, current stock, substitution safety, or a confirmed price.
- Use `python -m medisaving ux status STATE` for a known conversation state (`unreadable_photo`, `missing_district`, `ambiguous_query`, `no_results`, `error`, or `recover`). Ask for the missing information rather than inventing a medicine, district, or response.
- Rendered messages are delivery artifacts only: they do not send Telegram messages. A bot-owned delivery adapter must require an authorized destination, preserve the `presentation_id` for idempotency, and avoid real sends in tests.
- If an image or PDF is requested, keep the text result available immediately. Do not introduce a rendering dependency or generate a file merely because a ranking was produced.
- In the Telegram runtime, `med show RESULT_ID` invokes this renderer and `med status STATE` renders a state. Run `med enrich RANKING_ID` first to join official presentation/manufacturer details without recalculating prices, then pass its new result_id to show. Basket IDs are not supported by this renderer.
