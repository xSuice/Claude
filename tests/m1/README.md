# M1a public offline development checkpoint

Mode: MOCK / OFFLINE_TESTED. No Freeze, M1b or production qualification.

## Run (from this development worktree)

```text
python -m unittest discover -s tests/m1 -p test_host_adapter.py -v
python tests/m1/run_reference.py
```

`run_reference.py` executes 31 unchanged public reference test methods. It explicitly excludes four freeze/HMAC tests and removes their two unused import-time loaders via AST. The original reference files remain byte-identical to the supplied ZIP. It does NOT execute a private evaluator, freeze a branch or create private HMAC material.

## Added behavior

`host_adapter.py` wraps the supplied oracle-free proposal gate with strict integer counters (reject Python booleans), rejection of unhashable claim IDs and duplicate claim IDs. The reference gate itself is unchanged. The wrapper only returns a suggestion/rejection and never executes a tool. Regression tests observed RED before the wrapper/fixes, followed by GREEN; logs are in the external workspace reports.

## Limits

- This is a standalone offline test adapter, not wired into the V16 runtime.
- The reference tests exercise mocked D callbacks; a complete independently qualified real D baseline and read-selection implementation is NOT delivered or frozen.
- Public S1-S10 fixture generator/auditor results in the workspace are MOCK consistency checks, not OS isolation or actual recovery tests.
- PyYAML is absent. The separate public-audit runner uses installed ruamel.yaml's safe loader for the supplied audit.prereg function, explicitly recorded as a runtime adaptation. The 31 core reference tests require jsonschema and are not affected by this adaptation.
- Different-family reviewer is BLOCKED. No private evaluation, family generation, seeds or evaluator receipts were used.
- Windows is not a substitute for the required Linux sandbox or the unavailable G4560 worker.

## Stop

Do not call freeze tools, launch models, enable workers, deploy, publish or push this checkpoint. Next: obtain a qualified different-family reviewer and separately restore authorized SSH credentials, then finish the D/V16 integration and remaining M1a gates. Freeze remains a separate user decision.
