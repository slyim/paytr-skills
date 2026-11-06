# iFrame integration

Sources, verified 2026-11-06:

- <https://dev.paytr.com/en/iframe-api/iframe-api-1-adim>
- <https://dev.paytr.com/en/home/iframe-api-entegrasyon-sureci> (test and go-live)
- <https://dev.paytr.com/en/sikca-sorulan-sorular> (minimum amount)

## Flow

1. Compute the payable amount on the server from authoritative data.
2. Persist a pending attempt: `merchant_oid`, amount in minor units, currency,
   test/live mode, installment policy, merchant account reference.
3. POST the token request server-side to
   `https://www.paytr.com/odeme/api/get-token`.
4. Render `https://www.paytr.com/odeme/guvenli/<token>` in an iframe, with
   `https://www.paytr.com/js/iframeResizer.min.js` applied to it as PayTR's
   sample does.
5. The customer pays inside PayTR's form. The browser then lands on
   `merchant_ok_url` or `merchant_fail_url`, which only display current state.
   PayTR warns the payment may not be approved yet at that point.
6. Settlement happens in the callback. See
   [callbacks-settlement.md](callbacks-settlement.md).

## Token signature

**Provider.** Concatenate with no separators, in this order, ending with the
salt:

```text
merchant_id + user_ip + merchant_oid + email + payment_amount + user_basket
  + no_installment + max_installment + currency + test_mode + merchant_salt
```

`paytr_token = Base64(HMAC-SHA256(key = merchant_key, message))`, using the raw
digest. `user_basket` here is the Base64 text, not the JSON.

Also required but outside the signature: `user_name` (max 60), `user_address`
(max 400), `user_phone` (max 20), `merchant_ok_url` and `merchant_fail_url` (max
400). Optional and unsigned: `debug_on`, `timeout_limit` (minutes, 30 if
omitted), `lang` (`tr` or `en`, `tr` if omitted).

Synthetic check vector, for offline tests only:

```text
merchant_id=100000  user_ip=203.0.113.10  merchant_oid=synthOrder0001
email=buyer@example.test  payment_amount=1234  no_installment=1
max_installment=0  currency=TL  test_mode=1
merchant_key=synthetic-merchant-key  merchant_salt=synthetic-merchant-salt
basket JSON (UTF-8, unescaped, no spaces between items):
  [["Test ürünü","12.34",1]]
user_basket=W1siVGVzdCDDvHLDvG7DvCIsIjEyLjM0IiwxXV0=
paytr_token=U05ebnvxWNgoC/pAWHK8LGKT2900WhHoC5WyzB1lyrY=
```

## Field rules that break integrations

- **`user_basket`** (Provider): a JSON list of `[name, unit price text,
  quantity]` entries, per the samples. Encode as UTF-8 JSON, then Base64. Keep
  that Base64 string and use it for both signing and sending, because
  re-serializing can change the bytes. Base64 contains `+`, `/`, and `=`, so
  form-encode it on the wire while signing the unencoded text. The same applies
  to `paytr_token`.
  - **Ambiguous:** the docs do not say whether basket lines must sum to
    `payment_amount`. **Recommendation:** make them agree, or send one summary
    line with the server total so rounding cannot disagree.
- **`payment_amount`**: integer minor units as text. Convert with decimal or
  integer arithmetic; `1234.0` or a float artifact breaks the signature. The FAQ
  shows a rejection below `100`, described as 1 TL.
- **`merchant_oid`** (Provider): unique, at most 64 characters, alphanumeric.
  Strip hyphens from UUIDs and keep a lossless mapping. **Recommendation:** use
  a new value for every attempt whose amount, currency, mode, or installment
  terms differ.
  - **Ambiguous:** whether one `merchant_oid` can request a second token is
    undocumented. Reuse the existing token on reload, and use a new
    `merchant_oid` for a new attempt.
- **`user_ip`** (Provider): the customer's IP; use the external address when
  testing locally. PayTR's sample reads client-supplied forwarding headers.
  **Recommendation:** derive it through your trusted proxy hops instead, because
  those headers can be spoofed.
  - **Ambiguous:** the limit reads "up to 39 characters (ipv4)", yet 39 is the
    IPv6 text length. Test IPv6 clients before relying on them.
- **`email`** (Provider): at most 100 characters, no Turkish characters. Validate
  it before signing, and sign exactly what you send.
- **`no_installment`, `max_installment`** (Provider): `no_installment=1` hides
  installments. `max_installment` is `0` or `2` through `12`, and `0` means the
  maximum available. Choosing these is a product decision. Installments can make
  the callback amount exceed `payment_amount`.
- **`currency`** (Provider): `TL` (or `TRY`), `EUR`, `USD`, `GBP`, `RUB`.
  **Ambiguous:** marked mandatory, yet also defaults to TL. Send it explicitly,
  sign the same value, and store it on the attempt.
- **`test_mode`** (Provider): `1` runs a test while the store is live. Optional
  on the wire but part of the signature. **Recommendation:** always send `0` or
  `1` explicitly and store it on the attempt.
- **`debug_on`** (Provider): advises `1` during integration so errors are shown.
  **Recommendation:** disable it for live traffic.
- **`timeout_limit`**: **Recommendation:** make local expiry longer than this
  plus a margin, so a late payment is not treated as abandoned.

## Token response

**Provider.** JSON. Success carries `status: "success"` and `token`. Samples read
`reason` on failure; the page's failure example is a duplicated success example.

**Recommendation.** Timeouts and non-JSON bodies mean no usable token, so do not
render a form. Keep `reason` out of customer-facing text, since it can echo
submitted values. Requesting a token is not itself a charge, so closing the
attempt and letting the customer start again is acceptable.

## Rendering

**Recommendation:**

- Allow `https://www.paytr.com` in CSP for frames and for the resizer script.
- Build the iframe URL from a fixed origin, never from browser input, and encode
  the token as a path segment.
- Treat the token as a short-lived credential: keep it out of logs, analytics,
  and application URLs.
- Keep third-party analytics and session replay off the payment page.
- A reload should resume the same attempt rather than start a new one. Authorize
  resumption with the owner's session or an HttpOnly capability, not with an ID
  in a URL.
- Render no card inputs in the application. See
  [troubleshooting-boundaries.md](troubleshooting-boundaries.md) for how Direct
  API differs.

## Test and go-live

**Provider.** Credentials come from the merchant panel. Test card details are
prefilled in the iFrame. A test payment showing "Successful" on the panel's
Transactions page means the callback worked. Going live is requested from the
panel after test transactions are reviewed. The Notification URL is configured in
the panel, not in the token request.

**Recommendation.** Cover with synthetic data: the check vector, a non-ASCII
basket, reload during payment, a failure callback, a repeated callback, a
test-mode capture, and a browser return that arrives before the callback.
