# M1a gate report — INCONCLUSIVE / BLOCKED

Observed 2026-10-17T21:07:10.670204+02:00. Allowed mode: MOCK / OFFLINE_TESTED. This is NOT GO, LIMITED_GO, a freeze or production acceptance.

## Real source
Private xSuice/Claude, baseline `72e1607977fe1f8a78767bed7da3fe516d532f0a`, isolated branch `dev/hermes-m1a-20261017`, worktree `jarvis-m1a`. Source main remains clean. SSH is blocked, so deployed V16 revision is UNKNOWN.

## Completed offline work
- Copied only approved public M1a specification, tools and generator files; 130 source files match supplied bytes. YAML v7 remains PROPOSED_FREEZE_BEFORE_M1B; v7.1 not applied.
- Added host_adapter with RED->GREEN regressions for unhashable/doubled claim IDs and boolean counters. No V16 production module modified.
- Actual final tests: 4 new adapter, 31 selected reference, 3 separate synthetic lead smoke: 38 tests passed across these distinct suites, zero final failures/errors.
- Four freeze/HMAC reference methods deliberately not run. No freeze receipt or private HMAC generated.
- Public S1-S10 fixture generation/audit: 500 cases, not 500 runtime test passes. Checks include supplied schema/proof-set/budget/fair-fork consistency. They do not establish actual worker safety, causal utility or a fair fully implemented D baseline.

| Suite | Partition | Cases | Errors | Warnings | Manifest exact |
|---|---|---:|---:|---:|---|
| core | dev | 144 | 0 | 0 | True |
| core | dummy_holdout | 240 | 0 | 0 | True |
| safety | dev | 48 | 0 | 0 | True |
| safety | dummy_holdout | 68 | 0 | 0 | True |

PyYAML is absent; public audit used an explicit ruamel.yaml safe-loader binding in audit.prereg only. No fake data, no reference-source modification; hashes and generated manifests independently match. Audit INFO records are retained in MOCK-*.json. Selection pressure proxy is NOT the predeclared real-D budgeted/unbounded test.

## Remaining acceptance blockers
1. Full fair deterministic D and its read-selection/V16 diagnostic integration are not implemented or qualified by this checkpoint. Supplied D callbacks are mocks; do not call the actual D-quality gate passed.
2. Independent reviewer from a different model family is BLOCKED. Lead self-check and local tests are not an independent review.
3. Real Linux read-only isolation, recovery and cross-user behavior not exercised on Windows. S7-S10 above are fixture audits only.
4. Real server revision/resources/status unavailable due publickey auth failure.
5. No private evaluator custody, real Holdout, model benchmark, freeze or preregistration. None was attempted.

## Hard stop
STOP before Freeze, M1b, private tests, model/driver downloads, Patch4/E1-E5, productive portal changes or deployment. Continue only authorized local M1a after review/tool/auth blockers are resolved; freeze itself requires a new explicit user decision.
