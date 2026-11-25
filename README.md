# Fact-Check Gate

A pre-publication fact-checking gate for factual videos and articles, built for an AI-assisted medical-education content workflow.

No factual script ships — to rendering or to publication — until every factual claim in it traces back to an evidence card with a real, opened source. The generator and the checker are always different agents.

## How it works

1. **Split the script into claims.** Each factual sentence maps to claim IDs (`[S01 -> C01,C02]`); opinion/transition lines are explicitly exempted as `NONFACT`.
2. **Build evidence cards.** Every claim gets a card with a verdict (verified / inconclusive / refuted / not found), backed by opened primary or secondary sources — never by model memory. Search results are leads, not evidence.
3. **Reconcile every number.** All figures go into a reconciliation table (script value vs. source value); any mismatch fails the gate.
4. **Register every image.** Each image records its source type; generated images must be labelled as illustrations.
5. **Independent review (L2).** A different model/agent re-checks claim + evidence cards only (not the generator's reasoning, to avoid anchoring). Disputed claims escalate to a human decision (L3).
6. **Deterministic check.** `scripts/gate_check.py` validates the whole package. Exit code 0 = PASS, 1 = FAIL. FAIL locks rendering/publication — the standard is never lowered to force a pass.

Medical content runs a stricter profile on top of this baseline.

## Quick start

```sh
# a trial directory contains: script.md, claims.json, numbers.csv, images.json
python3 scripts/gate_check.py examples/pass-example          # PASS, exit 0
python3 scripts/gate_check.py examples/fail-example-ipo     # FAIL, exit 1 (fabricated IPO)
sh tests/run_tests.sh
```

Pure Python 3 standard library — no dependencies.

## Layout

- `SKILL.md` — the full gate protocol (L0 pre-checks, L1 dual-source cross-check, L2 independent review, escalation rules)
- `scripts/gate_check.py` — deterministic validator
- `templates/evidence-card.yaml` — evidence card template
- `examples/` — one passing package and one failing package (fabricated-IPO script)
- `SELFTEST.md` — recorded self-test output

## Author

Maintained by Dr. Jipang Zhan (dermatologic surgery, Southern Medical University) as part of a first-principles, systems-thinking clinical content workflow. No patient data is involved in this project.
