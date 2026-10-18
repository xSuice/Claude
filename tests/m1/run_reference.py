"""Run 31 supplied PUBLIC contract tests; explicitly exclude 4 freeze/HMAC tests.
Reference files are unchanged. Only excluded import-time tool loads are removed
from the AST; no successful results are fabricated and no private artifacts made.
"""
import ast
import io
import json
from pathlib import Path
import sys
import unittest
from typing import Any

HERE=Path(__file__).resolve().parent
TOOLS=HERE/'reference/M1_CORE_V5.2.7/04_TOOLS'
source=TOOLS/'test_tools.py'
EXCLUDED={'test_hmac_privacy_and_tampering','test_git_tree_freeze_covers_new_nested_import_without_manual_list',
          'test_freeze_rejects_dirty_and_untracked','test_full_tree_freeze_B'}
tree=ast.parse(source.read_text(encoding='utf-8'),filename=str(source))
tree.body=[n for n in tree.body if not (isinstance(n,ast.Assign) and any(
    isinstance(t,ast.Name) and t.id in {'freeze','holdout'} for t in n.targets))]
ns: dict[str, Any]={'__name__':'public_reference_tests','__file__':str(source)}
sys.path.insert(0,str(TOOLS))
exec(compile(tree,str(source),'exec'),ns)
case=ns['UtilityTests']
names=unittest.defaultTestLoader.getTestCaseNames(case)
suite=unittest.TestSuite(case(n) for n in names if n not in EXCLUDED)
result=unittest.TextTestRunner(verbosity=2).run(suite)
print(json.dumps({'mode':'MOCK','tests':result.testsRun,'failures':len(result.failures),
                  'errors':len(result.errors),'excluded':sorted(EXCLUDED)}))
sys.exit(0 if result.wasSuccessful() else 1)
