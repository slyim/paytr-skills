---
name: paytr
description: Implement, review, or debug PayTR payment integrations, including hosted iFrame checkout, paytr_token and callback-hash signing, Notification URL settlement, status inquiry, refunds, and reconciliation. Use when work touches PayTR APIs or payment state driven by them; not for other payment providers.
---

# PayTR

Portable guidance for building and auditing PayTR integrations in any stack. It
is not an SDK. The provider contract was verified against `dev.paytr.com` on
2026-11-06; when observed behavior or newer docs disagree, re-check the source
cited in the relevant reference instead of trusting this summary.

## How to read this skill

- **Provider**: stated by PayTR's documentation.
- **Recommendation**: design advice, not a PayTR rule. Adapt it to the system.
- **Ambiguous**: the docs are unclear or contradict themselves. Confirm in test
  mode or with PayTR support before depending on it.

Existing product decisions win over recommendations: installments, merchant
account layout, saved cards, and recurring billing are the application's choice.
Fit the existing architecture and use its own state names.

## Route to a reference

Read only what the task needs.

| Task | Read |
|---|---|
| Token request, basket, signing, rendering the iFrame, going live | [references/iframe-integration.md](references/iframe-integration.md) |
| Notification URL handler, hash check, idempotent settlement, the `OK` response | [references/callbacks-settlement.md](references/callbacks-settlement.md) |
| Status inquiry, missed-callback recovery, refunds | [references/inquiry-refunds.md](references/inquiry-refunds.md) |
| Diagnosing a failure, safe logging, or questions about Direct API, saved cards, recurring, Link, EFT, marketplace, or pre-provision | [references/troubleshooting-boundaries.md](references/troubleshooting-boundaries.md) |

## Amount units differ by API

Mixing these up causes wrong charges and wrong refunds. Convert with integer or
decimal arithmetic, never binary floats.

| Field | Unit |
|---|---|
| iFrame Step 1 `payment_amount` | Integer minor units: 34.56 is `3456` |
| Callback `total_amount`, `payment_amount` | Integer minor units |
| Status inquiry `payment_amount`, `payment_total` | Decimal text, apparently major units; separator is ambiguous |
| Refund `return_amount` | Decimal text in major units with a period: `12.34` |
| Saved-card recurring `payment_amount` | Decimal in major units, unlike the iFrame |

## Invariants

These guide hosted checkout and settlement. The iFrame signature below is
product-specific; other products need their own contract from the references.

1. **The server owns the money.** Compute price, discount, shipping, currency,
   installment policy, and test/live mode on the server. Never accept them from
   the browser.
2. **Sign exactly what goes on the wire.** For outgoing requests, format first,
   then sign and send the same strings. Verify incoming callbacks using the
   unchanged decoded strings before business normalization. HMAC input is text
   before URL encoding; the digest is Base64 of the raw bytes, not hex.
3. **One unique `merchant_oid` per payment attempt.** Persist the attempt first
   with its amount, currency, mode, and merchant account context, and resolve
   later operations through that record.
4. **A browser redirect never proves payment.** Only a verified callback, or a
   confirmed server-to-server inquiry, may establish that money was collected.
5. **Verify before acting.** No duplicate shortcut, state change, or `OK` before
   the callback hash passes a timing-safe comparison.
6. **The iFrame callback hash covers only `merchant_oid`, `status`, and `total_amount`.**
   Other callback fields, including `currency`, `test_mode`, and
   `payment_amount`, are not authenticated by it.
7. **Never treat `total_amount` equal to the order amount as a universal rule.**
   PayTR says it can exceed `payment_amount`. Exact equality is valid only as an
   explicit application policy.
8. **Settle atomically and idempotently.** Retries and concurrent deliveries
   must not repeat financial, stock, or entitlement effects. Enqueue notification
   work transactionally and deduplicate delivery where supported.
9. **Reply exactly `OK` only after a durable outcome**, including a durable
   quarantine of a mismatch. On a transient failure reply anything else, so
   PayTR retries.
10. **Never fulfill from a review or uncertain state.** Keep the evidence and
    resolve it deliberately.
11. **Reconcile before repeating an ambiguous write.** A timed-out refund may
    have succeeded; query first and retry only with proof it did not.
12. **Keep secrets and personal data out of logs**, errors, URLs, and analytics.

## Authority

This skill grants no permission of its own. Live charges, refunds, credential or
merchant-panel changes, and going live happen only within the scope the user has
already authorized, and it adds no approval step beyond that scope. Do not call
merchant APIs just to learn something; prefer offline tests with synthetic
fixtures, then test mode. Never ask for merchant secrets in chat.
