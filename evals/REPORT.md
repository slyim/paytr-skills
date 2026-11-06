# Initial evaluation — 2026-11-06

The initial skill was authored with Opus 5.5. A separate Antigravity Gemini 4
Argon task researched official PayTR contracts. A fresh Gemini 4 Argon task then
used the completed skill for four implementation requests, without the assessment
notes in `scenarios.md` or the earlier research reports. The maintainer reviewed
the actual answers and pseudocode rather than accepting the evaluator's grade.

No merchant credentials, customer data, production databases, or payment APIs
were used. This was a bounded design/code-sketch evaluation, not an executed
merchant integration or an exhaustive agent benchmark.

## Behaviors observed

- Hosted checkout: correct integer minor units, UTF-8 basket encoding, token
  signature, per-attempt mapping, and installment-aware amount policy.
- Callback handling: verified the signed tuple before duplicate shortcuts,
  identified unsigned currency/mode fields, serialized settlement, and kept
  browser redirects informational. It also identified the direct notification
  URL, session exemption, exact `OK`, and privacy-safe diagnostic requirements.
- Refunds: converted 1197 minor units to `11.97`, used the correct signature,
  reserved refund capacity, blocked concurrent unresolved writes, and reconciled
  a timeout instead of repeating the refund. It did not assume the reference
  number guaranteed provider idempotency.
- Inquiry: treated a single error 004 as inconclusive, parsed decimal text
  strictly, and kept refund evidence out of automatic fulfillment.
- Product selection: distinguished hosted renewals from unattended recurring
  payments and did not require another application's merchant-account layout.

## Problems found and corrections

The evaluator described the skill positively, but its output still contained
two substantive mistakes:

1. It named `/odeme/capi/payment` as a recurring-charge endpoint. The official
   recurring examples use `https://www.paytr.com/odeme`. The product reference
   now states the endpoint explicitly and warns against inferring routes from
   product names.
2. Its settlement sketch handled paid/refunded/failed states but implicitly
   treated remaining states as pending, allowing review or cancelled states to
   fall through. The reference now requires an explicit eligible-state allowlist
   after locking, and explains how resource conflicts become durable review
   outcomes rather than partial settlement or endless retries.

The evaluator also attributed delayed refund visibility to a provider warning
that the reviewed documentation does not state. The refund reference now makes
the uncertainty explicit: immediate visibility is not guaranteed. This supports
conservative reconciliation without inventing a provider promise.

These corrections were checked by maintainer inspection, structural validation,
and offline examples; a second independent behavioral run was not performed.
Future substantial changes should rerun the scenarios with fresh context.

## Deterministic checks

- Skill-creator `quick_validate.py`: passed.
- Repository packaging and local Markdown links: passed.
- Four documented synthetic HMAC vectors and Unicode basket encoding: passed.
- Packaging checker fixtures: accepted a complete fixture and rejected missing
  references and links escaping the repository.
- Helper syntax: passed.

These checks establish packaging and example consistency. They do not establish
live payment correctness, merchant eligibility, or PCI compliance.
