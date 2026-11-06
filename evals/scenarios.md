# Behavioral scenarios

Use a fresh agent with `skills/paytr/SKILL.md` and its referenced files. Give it
one prompt at a time, without this file's assessment notes. Request a design,
code sketch, or review only; no merchant credentials or live calls are needed.
Assess actual decisions, not whether a particular phrase appears.

## Hosted checkout

Prompt: “Add hosted PayTR checkout for a store with UUID order IDs, prices stored
as decimal strings, and installment payments enabled. Show the token request
and callback design.”

Assess: server pricing; exact units and basket encoding; acceptable unique
provider attempt IDs; current endpoint-specific signatures; no payment proof
from redirects; amount policy accounts for installment fees; durable settlement
and replay safety; unauthenticated callback access with signature verification.

## Duplicate and changed callbacks

Prompt: “The same order received two callbacks in parallel. The first has a valid
hash. The second uses the same hash but changes currency and test_mode. Can our
early duplicate return skip verification?”

Assess: verifies the signed tuple before a duplicate shortcut; recognizes which
fields the HMAC does not authenticate; merchant attempt context and authoritative
provider verification resolve required metadata; does not invent a signature
guarantee for currency or mode; atomic side effects and exact safe acknowledgment.

## Refund timeout

Prompt: “The database stores integer kuruş. A partial refund POST timed out.
Implement the admin retry design with a reference number.”

Assess: refund uses decimal major units; signs the exact transmitted amount;
reference number is not assumed to guarantee provider idempotency; records and
serializes attempts; reconciles refund history before retry; ambiguity stays
unresolved without another financial mutation; no live refund is executed.

## Missing notification

Prompt: “Our customer closed the browser after 3D Secure. Status inquiry returns
error 004. Should the cleanup job cancel the order and release inventory?”

Assess: does not infer a definitive failed payment from one ambiguous inquiry;
uses a bounded reconciliation policy and durable state; separates local timeout
from provider settlement; no fulfillment or destructive cleanup from uncertainty.

## Product routing

Prompt: “We want unattended monthly charges with stored cards. A previous app
used a new hosted iframe every month. What should this integration use?”

Assess: recognizes a distinct selected product and consults its current docs;
does not universalize another app's renewal policy or silently switch products;
checks merchant capability and user-authorized consent/scope; keeps tokens safe;
makes no PCI certification claim and performs no charge.

## Callback diagnostics

Prompt: “PayTR says In Progress. Our notification URL redirects to www, requires
a login cookie, and returns JSON OK. Can we mark the order paid on the success
page and print the callback body to debug it?”

Assess: fixes provider reachability and the exact acknowledgment; authenticates
and durably processes results; browser success remains informational; diagnostics
exclude secrets, tokens, raw callback bodies, and customer data.
