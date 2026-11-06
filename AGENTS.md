# Maintaining PayTR Skills

This repository contains portable agent guidance, not a payment SDK or a live
merchant integration. Keep the skill independent of any framework, database,
merchant account, or application's order-state names.

- Read `skills/paytr/SKILL.md` and the relevant references before editing.
- Verify changing provider contracts against `https://dev.paytr.com/`; cite the
  exact source and verification date. Separate provider requirements from
  application design recommendations. Do not copy provider manuals or samples.
- Never add merchant credentials, tokens, production identifiers, customer data,
  private infrastructure details, or scripts that make live payment calls.
  Examples and tests must use visibly synthetic fixtures.
- Keep `SKILL.md` concise and route conditional details to references. A user's
  existing authorization remains authoritative; the skill does not grant new
  permission for charges, refunds, credential changes, or publication.
- Validate skill frontmatter, relative links, any executable helpers, and
  realistic agent behavior before publishing. Behavioral cases must test
  financial invariants and routing, not only match document wording.
- Use the repository's documented check command once it exists. Keep checks
  offline and avoid third-party runtime dependencies unless justified.
- Do not commit, push, or publish unless the user authorizes it. Do not modify
  the application repository from which the reusable lessons were learned.
