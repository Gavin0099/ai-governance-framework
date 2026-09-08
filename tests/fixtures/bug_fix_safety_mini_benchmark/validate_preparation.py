"""Validate only the three authored fixture tasks; never runs a model or scores.

This is a pack-local preparation check, not a Lite runner entrypoint.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
TASKS = ('easy_queue_range', 'medium_interval_merge', 'hard_dependency_cycle')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def check_case(function, case, result_kind):
    args = copy.deepcopy(case['args'])
    before = copy.deepcopy(args)
    try:
        actual = function(*args)
        issues = []
        expected_type = bool if result_kind == 'bool' else list
        if type(actual) is not expected_type:
            issues.append('wrong_result_type')
        if actual != case['expected'] or json.dumps(actual) != json.dumps(case['expected']):
            issues.append('wrong_value')
        if args != before:
            issues.append('input_mutated')
        if result_kind != 'bool' and actual is args[0]:
            issues.append('outer_list_alias')
        if result_kind == 'fresh_nested_list' and type(actual) is list:
            if any(type(row) is not list or len(row) != 2 for row in actual):
                issues.append('wrong_interval_shape')
            if any(row is source for row in actual for source in args[0]):
                issues.append('inner_list_alias')
        return dict(id=case['id'], passed=not issues, expected=case['expected'],
                    actual=actual, issues=issues)
    except Exception as exc:
        return dict(id=case['id'], passed=False, expected=case['expected'],
                    issues=['exception'], diagnostic=f'{type(exc).__name__}: {exc}')


def load_functions(path):
    namespace = {'__name__': 'authored_fixture_validation'}
    exec(compile(path.read_bytes(), str(path), 'exec'), namespace)
    return namespace


def validate():
    manifest_raw = (ROOT/'manifest.json').read_bytes()
    manifest = json.loads(manifest_raw)
    paths = {p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*')
             if p.is_file() and p.name != 'manifest.json'}
    if paths != set(manifest['files']):
        raise ValueError('Fixture inventory differs from fixed review snapshot')
    for name, expected in manifest['files'].items():
        path = ROOT/name
        if path.is_symlink():
            raise ValueError('Fixture symlink is not admissible')
        raw = path.read_bytes()
        if len(raw) != expected['bytes'] or sha(raw) != expected['sha256']:
            raise ValueError(f'Fixture identity mismatch: {name}')
    results = {}
    failures = []
    for task in TASKS:
        folder = ROOT/task
        spec = json.loads((folder/'cases.json').read_bytes())
        cases = spec['oracle_cases']
        ids = [c['id'] for c in cases]
        if len(set(ids)) != len(ids):
            raise ValueError('Duplicate oracle case id')
        regression = set(spec['regression_case_ids'])
        if not regression or not regression <= set(ids):
            raise ValueError('Invalid regression preservation panel')
        panel_categories = {category for c in cases if c['id'] in regression
                            for category in c['categories']}
        if panel_categories != set(spec['required_categories']):
            raise ValueError('Regression panel does not cover declared categories')
        baseline = load_functions(folder/'baseline.py')[spec['function']]
        variants = load_functions(folder/'validation_variants.py')
        functions = dict(baseline=baseline, correct=variants['correct'],
                         superficial=variants['superficial'])
        records = {}
        for name, function in functions.items():
            forward = [check_case(function, case, spec['result_kind']) for case in cases]
            # Reuse the same callable and reverse the sequence: expose state carryover.
            reverse = [check_case(function, case, spec['result_kind']) for case in reversed(cases)]
            stable = forward == list(reversed(reverse))
            records[name] = dict(passed=sum(c['passed'] for c in forward),
                                 total=len(cases), repeat_order_stable=stable,
                                 cases=forward, repeated_cases=reverse)
        by_id = {name: {c['id']: c for c in row['cases']}
                 for name, row in records.items()}
        defect = spec['defect_case']
        counterexample = spec['superficial_counterexample']
        checks = {
            'baseline_reproduces_named_defect':
                by_id['baseline'][defect]['issues'] == ['wrong_value'],
            'reference_passes_all_cases_and_invariants':
                records['correct']['passed'] == len(cases),
            'reference_repeat_calls_stable': records['correct']['repeat_order_stable'],
            'superficial_fixes_public_symptom': by_id['superficial'][defect]['passed'],
            'superficial_fails_predeclared_counterexample':
                by_id['superficial'][counterexample]['issues'] == ['wrong_value'],
            'baseline_already_passes_counterexample': by_id['baseline'][counterexample]['passed'],
            'reference_passes_regression_panel': all(by_id['correct'][i]['passed'] for i in regression),
        }
        # Easy's upper boundary is also broken in baseline; the required distinction
        # is lower-only vs fully inclusive repair, not preservation of that boundary.
        if task == 'easy_queue_range':
            del checks['baseline_already_passes_counterexample']
        for name, passed in checks.items():
            if not passed:
                failures.append(task+':'+name)
        results[task] = dict(checks=checks, variants=records,
                             regression_case_ids=spec['regression_case_ids'],
                             coverage_categories=sorted(panel_categories),
                             required_scorer_evidence='Shared RUBRIC.md admission + task RUBRIC.md categories',
                             baseline_sha256=sha((folder/'baseline.py').read_bytes()),
                             cases_sha256=sha((folder/'cases.json').read_bytes()))
    return dict(result='THREE_TASK_BENCHMARK_READY_FOR_REVIEW' if not failures else 'PREPARATION_BLOCKED',
                failures=failures, tasks=results, manifest_sha256=sha(manifest_raw),
                authority='Prospective fixture review snapshot; owner adoption NOT CLAIMED',
                model_executions=0, scoring_performed=False,
                runner_integration='NOT_IMPLEMENTED',
                not_claimed=['Calibrated difficulty', 'Real Skill efficacy',
                             'Future scorer evidence delivery', 'Formal/counted evidence'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    memory_root = ROOT.parents[2]/'memory'
    if not output.is_relative_to(memory_root.resolve()):
        parser.error('Preparation evidence must be stored under this repository memory/')
    if output.exists():
        parser.error('Preserve existing validation evidence; choose a new output path')
    result = validate()
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(result['result'])
    for task, row in result['tasks'].items():
        print(task, {variant: f"{data['passed']}/{data['total']}"
                     for variant, data in row['variants'].items()})
    return 1 if result['failures'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
