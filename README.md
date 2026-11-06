# PayTR Skills

Portable agent guidance for building, reviewing, and troubleshooting PayTR
payment integrations. It covers hosted iFrame checkout, signed callbacks,
settlement, status inquiry, refunds, and choosing the correct PayTR product.

This is a community project, independent of PayTR. The repository contains
instructions, not a payment SDK, merchant credentials, or a running payment
service. The guidance is framework-neutral and separates PayTR's documented
contracts from recommended application design.

## Install

Clone this repository and copy the complete `skills/paytr` directory into your
agent's skill directory. Keep its `references/` and `agents/` subdirectories.

For Codex, a local installation can use `~/.codex/skills/paytr`:

```sh
git clone https://github.com/slyim/paytr-skills.git
mkdir -p ~/.codex/skills
cp -R paytr-skills/skills/paytr ~/.codex/skills/
```

PowerShell, for a new installation:

```powershell
git clone https://github.com/slyim/paytr-skills.git
New-Item -ItemType Directory -Force "$HOME/.codex/skills" | Out-Null
Copy-Item -Recurse ./paytr-skills/skills/paytr "$HOME/.codex/skills/"
```

For another agent supporting `SKILL.md`, use its documented skill location.
The core instructions and references are ordinary Markdown; `agents/openai.yaml`
is optional UI metadata for compatible hosts. To update, pull this repository
and replace the installed skill directory with the reviewed new version.

## Use

Example requests:

- “Use $paytr to add hosted checkout and a retry-safe callback handler.”
- “Use $paytr to investigate a payment stuck in progress after a redirect.”
- “Use $paytr to design partial refunds that recover safely from timeouts.”
- “Use $paytr to review our installment amount checks and merchant binding.”
- “Use $paytr to choose between hosted renewals and authorized recurring payments.”

Start with [the skill](skills/paytr/SKILL.md). It routes to focused references
instead of loading every PayTR product's documentation. Provider details carry
source links and verification dates; check the current official documentation
when implementing a changing contract. No instructions authorize live financial
operations beyond the user's requested scope.

## Validate and contribute

Python 3.10+ is sufficient for the offline repository checks; no packages,
merchant accounts, or network calls are required:

```sh
python scripts/validate.py
```

These checks validate packaging, relative links, Unicode basket encoding, and
four synthetic HMAC vectors embedded in the references. They do not certify a
payment integration or replace behavioral evaluation. Maintainer scenarios live in
[evals/scenarios.md](evals/scenarios.md); run them with a fresh agent using the
skill and review its actual decisions before publishing substantial changes.
The [initial evaluation report](evals/REPORT.md) records the observed behavior,
problems found, corrections, and test limits.

If the skill-creator tooling is installed, also run its `quick_validate.py`
against `skills/paytr`. Contributions should cite exact official PayTR sources,
use synthetic data, and explain which behavior the change improves. Keep
application-specific state names, infrastructure, credentials, and customer data
out of the skill. See [AGENTS.md](AGENTS.md) for maintenance rules.

## License

[MIT](LICENSE). PayTR documentation and trademarks belong to their respective
owners; links to provider documentation do not relicense that material.
