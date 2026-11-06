# Status inquiry and refunds

Sources, verified 2026-11-06:

- <https://dev.paytr.com/en/durum-sorgu>
- <https://dev.paytr.com/durum-sorgu> (Turkish; lists extra response fields)
- <https://dev.paytr.com/en/iade-api>
- <https://dev.paytr.com/en/hata-kodlari> (error codes, Turkish only)

Both APIs take a form POST and return JSON. Neither documents a signature on the
response. **Recommendation:** rely on TLS to the fixed `www.paytr.com` host,
refuse redirects, use the merchant account stored on the attempt, and set a
generous timeout (PayTR's samples use 90 seconds).

## Status inquiry

**Provider.** POST `https://www.paytr.com/odeme/durum-sorgu` with `merchant_id`,
`merchant_oid`, `paytr_token`.

```text
merchant_id + merchant_oid + merchant_salt
```

`paytr_token = Base64(HMAC-SHA256(key = merchant_key, message))`, raw digest.

Synthetic check vector, for offline tests only:

```text
merchant_id=100000  merchant_oid=synthOrder0001
merchant_key=synthetic-merchant-key  merchant_salt=synthetic-merchant-salt
paytr_token=cWd3A6KNaKdPErPR21RKuU3QLmcXAh7QXRLTMf1jtSE=
```

**Ambiguous:** the field table lists `merchant_key` and `merchant_salt` as sent
values, but every sample uses them only to sign. Never transmit them.

Success returns `status: "success"` with `payment_amount`, `payment_total`,
`currency`, `payment_date`, `net_tutar`, `kesinti_tutari`, `taksit`, `kart_marka`,
`masked_pan`, `odeme_tipi`, `test_mode`, and `returns`. The Turkish page adds
`auth_code` and `auth_date`. Errors return `status: "error"` with `err_no` and
`err_msg`.

### Reading the result

- **There is no explicit payment-state field. Ambiguous:** `status: "success"`
  describes the query. Error `004` reading "no successful payment" implies that
  success means one exists, but the docs do not say so. Confirm this against a
  failed test payment before settling from inquiries.
- **Error `004` has two documented messages:** no transaction found, and no
  successful payment found. Neither proves the payment will never succeed.
- **Amount format. Ambiguous:** the sample value is `10,8`, and the unit is not
  stated. The net and deduction examples are decimals with a period, so major
  units are the likely reading. Parse strictly, accepting one explicit `.` or `,`
  separator and at most two fraction digits. Treat anything else as unknown,
  never as zero. Confirm with a real test-mode response.
- **`payment_amount` vs `payment_total`:** the order amount and what the customer
  paid. They mirror the callback's `payment_amount` and `total_amount`, so apply
  the same amount policy.
- **`currency`:** may be `TL` or `TRY`; treat them as equal when comparing.
- **`odeme_tipi`:** the Turkish page says `KART`/`EFT`, the English page
  `CART`/`EFT`, and the callback uses `card`/`eft`. Normalize before comparing.
- **`test_mode`:** `0` or `1`. **Recommendation:** treat a missing or other value
  as unknown, not live.
- **`returns`:** non-empty means refund activity exists. **Recommendation:** never
  settle a payment as fulfillable while it shows refunds.
- **`masked_pan`:** card-related data. Do not log or store it without a reason.

The Marketplace Status Inquiry on the same page is a separate variant.

### Recovering missed callbacks

**Recommendation.** Run an idempotent job over attempts past `timeout_limit` plus
a margin, with a bounded rate, and feed results into the same settlement function
as the callback.

| Inquiry result | Do |
|---|---|
| Paid, all checks pass | Settle |
| Paid, any mismatch, refund evidence, or unknown mode | Quarantine |
| `004` while the payment window may be open | Wait |
| `004` repeatedly, spaced apart, after the window | Close as failed and release resources |
| Timeout, malformed body, other errors | Unknown; change nothing and try later |

One miss is not enough to release resources, and a late signed success still has
to be handled as the settlement table in
[callbacks-settlement.md](callbacks-settlement.md) describes.

**Ambiguous:** settling locally from an inquiry may not clear PayTR's own "In
Progress" state, which depends on `OK` reaching PayTR. Fix the callback too.

## Refunds

**Provider.** PayTR warns that a wrong integration can cause incorrect refunds and
financial loss. POST `https://www.paytr.com/odeme/iade` with `merchant_id`,
`merchant_oid`, `return_amount`, `paytr_token`, and optionally `reference_no` (up
to 64 alphanumeric characters).

```text
merchant_id + merchant_oid + return_amount + merchant_salt
```

`paytr_token = Base64(HMAC-SHA256(key = merchant_key, message))`, raw digest.

`return_amount` is major-unit decimal text using a period. Format it from minor
units with integer arithmetic, and sign the identical string you send. Prefer a
fixed two decimals, such as `12.34` or `10.00`. `reference_no` is not signed.

Synthetic check vector, for offline tests only:

```text
merchant_id=100000  merchant_oid=synthOrder0001  return_amount=12.34
merchant_key=synthetic-merchant-key  merchant_salt=synthetic-merchant-salt
paytr_token=LRG0dz4A6RTMd5WzIjFkcRmm0LSdJT1K6ya6+jtuqr4=
```

Success returns `status: "success"`, `is_test`, `merchant_oid`, `return_amount`,
and `reference_no` if one was sent. The page also describes `failed` for an
unknown order and `error` with `err_no` and `err_msg`.

### Refund ambiguities

- `return_amount` is typed `integer`, but the text and samples use decimals. Use
  decimals.
- The Python sample omits `merchant_oid` from the POST, and no sample posts
  `reference_no` despite defining it. Follow the field tables, not the samples.
- **`reference_no` is not documented as an idempotency key.** Nothing says PayTR
  rejects a repeat. It is documented only as appearing in Status Inquiry results.
  Do not assume resending is safe.
- **The `returns` item schema is undocumented.** The .NET sample prints amount,
  date, type, completion date, auth code, and a reference field from a model
  absent from the sample bundle. Capture a real test-mode refund before writing
  matching code, and tolerate field-name variation by quarantining, not guessing.
- Over-refund is `009` in the error table but `006` in a sample comment.
- Whether the cap is the order amount or the higher collected total on
  installment payments is not stated. Test it, or treat the order amount as the
  limit.

### Error codes

| `err_no` | Meaning | Handling |
|---|---|---|
| `000` | Refund service locked during a payout; try later | Provider invites a later retry; reconcile first |
| `001`-`004` | Inactive store or missing/invalid fields or token | Fix the request |
| `005` | No successful payment for this `merchant_oid` | Investigate; do not record a refund |
| `007` | Payment found but notification not completed | Fix or await the callback, then retry |
| `008` | Payment type does not support refunds | Handle outside this API |
| `009` | Total refunds would exceed the payment | Check the refund ledger |
| `010` | Insufficient net balance | Operational; retry after funding |
| `011` | Transaction older than one year | Handle outside this API |

An explicit error response is a rejection. A timeout, connection reset, non-JSON
body, or HTTP failure is not: it means unknown.

### Safe refund lifecycle

**Recommendation.**

1. Under a lock, confirm the payment is settled and that confirmed refunds plus
   unresolved refund intents plus this request stay within the limit, in integer
   minor units. Block overlapping writes while an earlier outcome is unknown.
2. In that same critical section, reserve the refund budget and durably record
   the intent: `merchant_oid`, amount, unique alphanumeric reference, and state
   "processing". Release the database lock before calling PayTR.
3. Send once. On success, confirm that echoed `merchant_oid`, `return_amount`, and
   `reference_no` match the request; a mismatch is unknown, not success.
4. On an explicit rejection, record it and stop. A later attempt is a new,
   deliberate decision.
5. On an unknown outcome, do not resend. Query status inquiry and look in
   `returns` for this reference and amount. A match confirms it. The docs do not
   guarantee immediate refund visibility, so absence alone is inconclusive.
   Otherwise hold the refund for review and check the merchant panel.
6. Reverse local fulfillment and resources only after confirmation, and keep the
   financial history. `is_test: 1` is not a live refund.

Partial refunds use the same flow with one reference per refund. A replayed
success callback must not revive a refunded payment.
