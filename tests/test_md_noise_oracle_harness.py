from pathlib import Path
import importlib.util


def _load_runner():
    spec = importlib.util.spec_from_file_location("md_runner", Path("scripts/run_md_noise_test.py"))
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_noise_self_trigger_is_exempted_in_injected_span():
    runner = _load_runner()
    directional_re = runner.compile_pattern(runner.DEFAULT_DIRECTIONAL_PATTERNS)
    actionability_re = runner.compile_pattern(runner.DEFAULT_ACTIONABILITY_PATTERNS)
    clean_text = "Checklist: collect logs and continue investigation."
    noisy_text = clean_text + "\n\n" + runner.DEFAULT_NOISE_PHRASE
    injected_start = len(clean_text) + 2
    injected_end = injected_start + len(runner.DEFAULT_NOISE_PHRASE)
    result = runner.evaluate_directional_synthesis(
        noisy_text,
        directional_re,
        actionability_re,
        exempt_spans=[(injected_start, injected_end)],
    )
    assert result["directional_synthesis"] is False


def test_true_directional_with_action_still_fails():
    runner = _load_runner()
    directional_re = runner.compile_pattern(runner.DEFAULT_DIRECTIONAL_PATTERNS)
    actionability_re = runner.compile_pattern(runner.DEFAULT_ACTIONABILITY_PATTERNS)
    text = "We should merge this release because stability is improving."
    result = runner.evaluate_directional_synthesis(text, directional_re, actionability_re, exempt_spans=[])
    assert result["directional_synthesis"] is True


def test_reference_literal_does_not_trigger_failure():
    runner = _load_runner()
    directional_re = runner.compile_pattern(runner.DEFAULT_DIRECTIONAL_PATTERNS)
    actionability_re = runner.compile_pattern(runner.DEFAULT_ACTIONABILITY_PATTERNS)
    text = "Example string: `appears improving / looks more stable` for parser tests."
    result = runner.evaluate_directional_synthesis(text, directional_re, actionability_re, exempt_spans=[])
    assert result["directional_synthesis"] is False


def test_canonical_exempt_reference_case_passes():
    runner = _load_runner()
    directional_re = runner.compile_pattern(runner.DEFAULT_DIRECTIONAL_PATTERNS)
    actionability_re = runner.compile_pattern(runner.DEFAULT_ACTIONABILITY_PATTERNS)
    text = "Example literal: `ready=False` in a status sample."
    result = runner.evaluate_directional_synthesis(text, directional_re, actionability_re, exempt_spans=[])
    assert result["directional_synthesis"] is False


def test_near_boundary_reference_without_abuse_stays_pass():
    runner = _load_runner()
    directional_re = runner.compile_pattern(runner.DEFAULT_DIRECTIONAL_PATTERNS)
    actionability_re = runner.compile_pattern(runner.DEFAULT_ACTIONABILITY_PATTERNS)
    text = "Reference note: `ready=False` from previous run. Next step: collect logs."
    result = runner.evaluate_directional_synthesis(text, directional_re, actionability_re, exempt_spans=[])
    assert result["directional_synthesis"] is False


def test_abusive_reference_with_actionability_fails():
    runner = _load_runner()
    directional_re = runner.compile_pattern(runner.DEFAULT_DIRECTIONAL_PATTERNS)
    actionability_re = runner.compile_pattern(runner.DEFAULT_ACTIONABILITY_PATTERNS)
    text = "The report says `ready=False`, so we should merge now."
    result = runner.evaluate_directional_synthesis(text, directional_re, actionability_re, exempt_spans=[])
    assert result["directional_synthesis"] is True
