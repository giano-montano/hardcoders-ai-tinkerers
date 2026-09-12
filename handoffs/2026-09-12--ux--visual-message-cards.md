# Handoff — UX visual message cards

**Date:** 2026-09-12  
**Owner:** UX  
**Status:** implemented in the UX renderer and tests only.

## Delivered

All user-facing UX states and result cards now use short English sentences,
blank-line grouping, and consistent Unicode icons. The first pharmacy card
connects the information a person needs to decide: medicine, pharmacy,
per-box and per-unit price, box size, and address. The detailed card keeps
secondary fields behind `More details` rather than showing a dense technical
list. Missing optional data is omitted instead of repeatedly saying `not
reported`.

Button labels now include visual cues: map, call, details, see all options,
and new prescription. Quantity safety notices have a visible warning heading
and preserve the pharmacist-confirmation and do-not-change-dose boundary.

## Sticker boundary

Emoji icons are rendered directly in every text message. Real Telegram
stickers are not files embedded in a text presentation: a delivery adapter
needs a vetted sticker file or Telegram `file_id`, then sends it through
`sendSticker`. No sticker ID was invented and no message delivery code was
changed.

## Verification

Run `python -m unittest discover -s tests/ux -v`.
