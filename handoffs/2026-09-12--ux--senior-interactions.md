# Handoff — UX interactions for senior-friendly Telegram results

**Date:** 2026-09-12  
**Owner:** UX  
**Status:** implemented in `medisaving/ux/` and `tests/ux/`; no change to bot,
prescription analysis, ingestion, or ranking.

## Delivered

The initial result now keeps only the essential offer information: medicine,
pharmacy/district, box price, units, and address. Full price, presentation,
laboratory, phone, and report date are available through a `More details`
callback response.

The presentation contains declarative `keyboards` and `interaction_responses`
for a Telegram delivery adapter:

- `Open map` opens Google Maps with the reported pharmacy address. It does not
  request or retain user location.
- `More details`, `Call pharmacy`, `See all options`, and `New prescription`
  use callback data. The adapter must associate callbacks with a persisted
  `presentation_id`, enforce authorization/idempotency, and implement these
  actions.
- When upstream supplies an optional verified `prescription_checks` record,
  UX warns only if the stated quantity exceeds the reported box units or a
  pharmacist-verification flag exists. The copy directs the person to a
  pharmacist and explicitly says not to change the prescribed dose. It only
  mentions partial dispensing when upstream verifies that availability.

## Integration required from the bot owner

The current bot sends plain messages and waits only for text/photos. To make
these controls live, its delivery adapter needs to attach the keyboard markup,
handle callback queries, and request location explicitly only for optional
nearby/directions features. The analyzer/ranking owners must agree on and
provide verified `prescription_checks`; UX does not infer medical or legal
status from OCR.

## Verification

`python -m unittest discover -s tests/ux -v` passes with seven tests.
