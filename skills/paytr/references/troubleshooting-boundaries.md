# Troubleshooting and product boundaries

Sources, verified 2026-11-06:

- <https://dev.paytr.com/en/sikca-sorulan-sorular>
- <https://dev.paytr.com/en/hata-kodlari>
- <https://dev.paytr.com/en/servis-test-araclari/hash-hesaplama>
- <https://dev.paytr.com/en/direkt-api/direkt-api-1-adim>
- <https://dev.paytr.com/en/direkt-api/kart-saklama-api/yeni-kart-ekleme>
- <https://dev.paytr.com/en/direkt-api/kart-saklama-api/kayitli-kart-tekrarlayan-odeme>
- <https://dev.paytr.com/en/on-provizyon>

## Symptoms

| Symptom | Check |
|---|---|
| Token request rejected as a bad `paytr_token` | Field order; omitted `test_mode` or `currency`; signing URL-encoded values; hex instead of Base64 of raw digest; `payment_amount` not plain integer text; basket re-serialized after signing; email or names changed after signing |
| `payment_amount` must be at least 100 | Amount sent in major units, or below the documented minimum |
| iFrame blank or blocked | CSP for `www.paytr.com`; expired token; token mangled by encoding; resizer script blocked |
| "Missing/incorrect notification URL" alert | Set the Notification URL in the panel |
| Panel stays "In Progress" | PayTR did not get exact `OK`. Open the transaction's Detail view to see what it received; check for redirects, auth, WAF challenges, a failing hash, or extra body content |
| Payments on the Merchant Notifications page | Delivery failed. Read Error Detail, fix the cause, then use Restart Stopped Notifications if authorized |
| Callback hash never matches | Salt belongs second; wrong merchant account; values trimmed or converted before hashing; `key`/`salt` swapped or carrying stray whitespace |
| Hash fails only sometimes | Compare the received `hash` for spaces where `+` belongs, which would mean a body-decoding problem. This is an inference, so confirm in test mode; do not repair hashes in production |
| Valid success callback quarantined | Exact-amount policy on a payment where `total_amount` exceeds `payment_amount`. Review the amount policy |
| Customer redirected to success, order still pending | Normal until the callback lands. Display pending and poll your own state; do not settle from the redirect |
| Duplicate fulfillment | Missing atomic state transition, or side effects run before commit |
| Test payments treated as live | Mode not stored on the attempt, or relying on the unsigned callback field alone |
| Inquiry `004` right after payment | Possibly too early. Not proof of failure |
| Refund `007` | The notification flow has not completed for that payment. Fix the callback first |
| Refund call timed out | Do not resend. Follow the lifecycle in [inquiry-refunds.md](inquiry-refunds.md) |

`failed_reason_code` is customer or bank outcome data, unsigned and diagnostic.
Code `99` signals a technical integration error when `debug_on` is `0`. Code `6`
means the customer abandoned or timed out. Do not drive settlement from it.

## Privacy-safe diagnostics

**Recommendation.** Log an allow-list, not a redaction of raw data.

- **Fine to log:** stage name, outcome category, HTTP status, `err_no`,
  `failed_reason_code`, internal attempt ID or a truncated digest of
  `merchant_oid`, and whether a signature check passed.
- **Never log:** `merchant_key`, `merchant_salt`, `paytr_token`, callback `hash`
  values (received or expected), iFrame tokens, raw callback or response bodies,
  card data, `masked_pan`, `utoken`, `ctoken`, email, phone, address, name, or IP.
- Treat `reason`, `err_msg`, and `failed_reason_msg` as untrusted text that may
  echo submitted values. Keep them out of customer messages, and sanitize them
  before storing.
- Alerts need to be actionable without personal data, such as "quarantined:
  amount mismatch on attempt X".

To debug a signature, reproduce it offline with synthetic values and the check
vectors in the references. PayTR's hash calculation page is a web form, so never
enter live credentials there.

## Product boundaries

**Hosted iFrame.** The customer enters card details in PayTR's form, so the
application never handles card data. That reduces exposure but is not a PCI DSS
certification or a statement of your compliance scope; confirm that with your
acquirer or assessor.

The recipes in this skill cover iFrame checkout, its callbacks, inquiry, and
refunds. The products below use different contracts; read their pages before
reusing any recipe here.

| Product | What differs | Notes |
|---|---|---|
| Direct API | The merchant's own form collects `card_number`, `cvv`, and related fields | Choose it only deliberately, with the card-data compliance obligations it brings. Do not migrate to it to solve an iFrame styling problem |
| Card Storage (CAPI) | `store_card`, `utoken`, and `ctoken` built on Direct API | Tokens are sensitive; store them encrypted, and plan deletion |
| Recurring with saved card | Server-initiated `recurring_payment=1`, `non_3d=1` | See below |
| Link API | Separate create, delete, and callback contracts | Needs merchant authorization |
| Transfer/EFT iFrame | Its own Step 1 and Step 2 | Do not assume card flow fields |
| Marketplace and platform transfer | Own inquiry variant, transfer requests, and error tables | Merchant-type gated |
| Pre-provision | Separate document, linked from the page | Do not infer behavior from this skill |

### Recurring with a saved card

**Provider.** PayTR offers this. It needs Non3D permission on the store, and
`recurring_payment` needs a separately approved authorization. There is no
customer interaction. Differences from the iFrame:

- The recurring charge is submitted to `https://www.paytr.com/odeme`, as shown
  in the linked recurring-payment examples. Do not invent a `/odeme/capi/payment`
  endpoint from the CAPI product name. Consult the selected product's current
  field table before implementing a request.
- `payment_amount` is a major-unit decimal, such as `100.99`.
- The token message is different:

  ```text
  merchant_id + user_ip + merchant_oid + email + payment_amount + payment_type
    + installment_count + currency + test_mode + non_3d + merchant_salt
  ```

- The request returns JSON directly: `success`, `failed`, or `wait_callback`, with
  `try_again` on failures. Transaction details also go to the Notification URL.

**Recommendation.** Route the result through the same settlement function, and
treat `wait_callback` as pending. If `try_again` reports an ongoing transaction,
inquire before charging again. Keep an idempotency guard per billing period. A
charge-retry loop is a live money-moving workflow, so stop on any ambiguity.

Whether to charge automatically is a product and legal decision. An application
may require the customer to pay each period through the hosted form instead;
that is a valid design choice, not a PayTR rule. Separate merchant accounts per
business line are likewise optional. If an application has them, resolve
credentials from the attempt as [callbacks-settlement.md](callbacks-settlement.md)
describes.
