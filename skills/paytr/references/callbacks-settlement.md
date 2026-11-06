# Callbacks and settlement

Sources, verified 2026-11-06:

- <https://dev.paytr.com/en/iframe-api/iframe-api-2-adim>
- <https://dev.paytr.com/iframe-api/iframe-api-2-adim> (Turkish; adds the HTTPS note)
- <https://dev.paytr.com/en/sikca-sorulan-sorular> (stopped notifications)

## Provider contract

PayTR POSTs each payment result to the Notification URL configured in the
merchant panel. There is no user session. Without an `OK` reply PayTR treats the
payment as incomplete and the merchant is not paid.

| Field | Sent on | Covered by `hash` |
|---|---|---|
| `merchant_oid` | success, failed | Yes |
| `status` (`success` or `failed`) | success, failed | Yes |
| `total_amount` (minor units, collected amount) | success, failed | Yes |
| `hash` | success, failed | n/a |
| `payment_type` (`card` or `eft`) | success, failed | No |
| `failed_reason_code`, `failed_reason_msg` | failed | No |
| `currency` | success | No |
| `payment_amount` (minor units, the Step 1 value) | success | No |
| `test_mode` (`1` for tests, otherwise may be absent) | optional | No |

Hash message, with the salt in second position:

```text
merchant_oid + merchant_salt + status + total_amount
```

`hash = Base64(HMAC-SHA256(key = merchant_key, message))`, raw digest.

Synthetic check vector, for offline tests only:

```text
merchant_oid=synthOrder0001  status=success  total_amount=1234
merchant_key=synthetic-merchant-key  merchant_salt=synthetic-merchant-salt
hash=+BGIzg5hTQlxFuRI8x/4hw8Y/O5YEhLg5ZUH3YCPJmY=
```

Delivery rules:

- The reply is plain text `OK`, with nothing before or after it.
- Access must not be restricted by session control or similar measures.
- With no connection or no `OK`, PayTR retries after a minute, so duplicates are
  normal. The panel shows the payment as "In Progress" meanwhile.
- PayTR says to act on the first notification only, detect repeats by
  `merchant_oid`, and answer repeats with `OK`.
- If notifications stall, the panel's Merchant Notifications page shows the error
  and can restart them. No retry limit is documented.
- The Turkish page says the panel's URL protocol must match the site: HTTPS only
  with a working certificate.

## Handler order

**Recommendation** unless marked. The order is what protects you.

1. Accept POST only. Read a bounded body before parsing; 16 KiB is ample.
2. Parse `application/x-www-form-urlencoded` strictly. PayTR's samples read
   standard form fields, though the docs name no exact header, so confirm your
   content-type check against a real test callback.
3. Reject a repeated key among the fields you use. First-wins and last-wins
   parsers can disagree with what was signed.
4. Require `merchant_oid`, `status`, `total_amount`, `hash`. Check shape only:
   `status` is one of two values, `total_amount` is digits. Do not trim, change
   case, or convert to a number before hashing. Do not reject on unknown extra
   fields or on odd text in unsigned diagnostics such as `failed_reason_msg`.
5. Choose credentials. With one merchant account, use it. With several, the
   callback carries no `merchant_id`, so do a read-only lookup of the attempt by
   `merchant_oid` and use its stored account, with no fallback to another one.
6. Compute the hash over the received strings and compare with a timing-safe,
   equal-length comparison. PayTR's samples use plain `!=`; the hardening is
   yours. Many timing-safe APIs throw on unequal lengths, so check length first.
   On failure, reply non-`OK` and change nothing.
7. Only now run the duplicate check and settlement, in one transaction.
8. Reply `OK` after commit. Send notifications afterward, outside the
   acknowledgement path.

Never move the duplicate shortcut above step 6: unverified input would then
receive `OK` and could mask a forged or misrouted request.

## Keeping the endpoint reachable

**Provider** forbids session-style restriction. **Recommendation** follows from
it: no login, CSRF token, browser-origin check, CAPTCHA, or WAF or bot challenge
on this route, and no redirect (HTTP to HTTPS, trailing slash, locale prefix).
Do not IP-allowlist unless PayTR gives you addresses; the reviewed pages publish
none. Rate limits must not starve legitimate retries. The hash is the
authentication.

## What the hash does and does not prove

A valid hash shows someone holding the merchant secrets produced that
`merchant_oid`, `status`, and `total_amount` combination. It says nothing about
`currency`, `test_mode`, `payment_amount`, or `payment_type`. It has no timestamp
or nonce, so a captured callback can be replayed; idempotent settlement is the
defense.

**Recommendation.** Take expected amount, currency, and mode from the stored
attempt, which is what Step 1 signed under this unique `merchant_oid`. Compare
unsigned fields against it as consistency signals: a disagreement is a reason to
quarantine, but agreement proves nothing. An absent `test_mode` is not proof of a
live payment, so the stored mode decides. If an unsigned value must be
authoritative, confirm it through a status inquiry.

## Amount policy

**Provider.** `total_amount` can exceed `payment_amount`, for example with
installments or alternative payment methods. Do not assume that
`no_installment=1` rules this out; the docs' list is open-ended.

**Recommendation.** Make the policy explicit and quarantine whatever it rejects.

| Collected vs expected | Installments or surcharges allowed | Exact-amount policy |
|---|---|---|
| Equal | Settle | Settle |
| Higher | Settle; record collected and order amounts separately | Quarantine |
| Lower | Quarantine | Quarantine |

Compare as integers, using a type that cannot lose precision.

## Settlement

**Recommendation.**

- Make `merchant_oid` the unique key of the attempt, and lock the row or use a
  conditional update so concurrent deliveries serialize.
- Apply the payment state change, stock, coupon, and entitlement claims in the
  same transaction, and write notification work to an outbox there.
- Share one settlement function between callback and inquiry, so both apply the
  same checks.
- Allow settlement only from explicitly named eligible states in the
  application's state machine. Never use a default branch meaning "everything
  else is pending". Review, expired, cancelled, refunded, and unknown states
  must not fall through into fulfillment. Recheck eligibility after acquiring
  the transaction lock.

| Verified result | Attempt is | Do |
|---|---|---|
| success | Pending, checks pass, resources claimed | Mark paid |
| success | Pending, but mismatch, test capture in a live flow, or resource conflict | Quarantine with evidence |
| success | Already paid | No-op |
| success | Failed, expired, or cancelled locally | Quarantine: money may have been taken late |
| success | Refunded | No-op; do not re-fulfill |
| failed | Pending | Mark failed and release resources |
| failed | Already failed | No-op |
| failed | Paid or in review | Do not downgrade; record the conflict for review |
| either | Unknown `merchant_oid`, hash verified | Store in durable quarantine |

PayTR's "first notification only" guidance covers ordinary repeats. It does not
say what a conflicting later result means, so record that case rather than
silently dropping it.

If a stock or entitlement claim fails, roll back the attempted settlement, then
durably record the verified payment for review before acknowledging it. Do not
leave part of the settlement committed or turn a business conflict into an
endless transient-error retry loop.

A quarantined success may represent money collected but not yet honored. Keep it
out of fulfillment and recognized sales revenue, track the financial liability,
keep it visible to operators, and resolve it by inquiry, refund, or reconciliation.

## Acknowledgement

| Outcome | Reply |
|---|---|
| Malformed, duplicate keys, or bad hash | Non-`OK` (for example 400) |
| Database or other transient failure | Non-`OK` (for example 503), so PayTR retries |
| Settled, or repeat of a settled result | `OK` |
| Mismatch durably quarantined | `OK` |
| Notification failure after commit | `OK` |

Never reply `OK` before the outcome is durable, and never withhold it because a
mismatch needs a human: withholding only causes retries.

The body must be exactly the two characters. Watch for JSON serializers producing
`"OK"`, templates adding markup, trailing newlines, and byte-order marks. The docs
state no status code; the samples return their framework's default 200.
