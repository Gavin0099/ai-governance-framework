#!/usr/bin/env python3
"""Counter-examples for answer_questions.py.

An analyser nobody has tried to fool is not evidence. Two of these reproduce
defects a review actually found in the first version -- it declared the guard's
deny path sound in a run that contained no denial, and it inverted the answer to
Q3 by pairing transcript events with adapter lines by list position. Each test
below asserts the specific answer that must NOT be produced.

    python test_answer_questions.py
"""
from __future__ import annotations

import hashlib
import unittest

from answer_questions import ANSWERED, UNANSWERED, analyse, render

POLICY = {"policy_id": "admission-canary-1", "policy_sha256": "p" * 64}


def sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def pre(tuid: str, verb: str, args: list[str], decision: str = "allow", command: str | None = None) -> dict:
    return {"event": "pre_tool_use", "tool_use_id": tuid, "tool": "Bash",
            "command": command or f"/adapter.sh {verb} {' '.join(args)}".strip(),
            "verb": verb if decision == "allow" else (verb or None),
            "args_sha256": sha("\x00".join(args)), "arg_count": len(args),
            "decision": decision, "reason": "ok" if decision == "allow" else "denied", **POLICY}


def term(tuid: str, event: str = "post_tool_use", stdout: str | None = None) -> dict:
    row = {"event": event, "tool_use_id": tuid, "hook_event_name": event, "tool": "Bash",
           "stdout_sha256": sha(stdout) if stdout is not None else None,
           "stdout_len": len(stdout) if stdout is not None else None,
           "observable_source": "tool_response.stdout" if stdout is not None else "tool_response is NoneType",
           "response_keys": ["interrupted", "isImage", "stderr", "stdout"] if stdout is not None else None,
           "error_sha256": None if stdout is not None else sha("failed")}
    return row


def line(seq: int, verb: str, args: list[str], exit_code: int, stdout: str,
         lock_wait_ms: int = 0, decision: str = "executed") -> dict:
    return {"seq": seq, "pid": 1000 + seq, "lock_wait_ms": lock_wait_ms, "verb": verb,
            "args_sha256": sha("\x00".join(args)), "arg_count": len(args),
            "decision": decision, "exit": exit_code, "stdout_bytes": len(stdout),
            "stdout_sha256": sha(stdout), **POLICY}


FAIL_OUT = "FAILED (failures=2)"
PASS_OUT = "OK"


class ZeroDenialMustNotClaimTheGuardWorks(unittest.TestCase):
    """Counter-example 1 -- the review's `denied calls: 0` false success.

    A run in which the producer never once reached outside the channel proves
    nothing about the deny path. The first version printed
    'VERDICT: deny was honoured' anyway.
    """

    def setUp(self):
        events = [pre("t1", "ls", []), term("t1", stdout="src/calc.py"),
                  pre("t2", "test", []), term("t2", stdout=PASS_OUT)]
        adapter = [line(1, "ls", [], 0, "src/calc.py"), line(2, "test", [], 0, PASS_OUT)]
        self.q2 = analyse(events, adapter)["q2"]

    def test_status_is_unanswered(self):
        self.assertEqual(self.q2["status"], UNANSWERED)

    def test_does_not_claim_deny_was_honoured(self):
        # The verdict tokens are HONOURED/LEAKED and they lead the answer; the
        # word may still appear inside a sentence explaining what was NOT shown.
        self.assertFalse(self.q2["answer"].startswith(("HONOURED", "LEAKED")))

    def test_says_why(self):
        self.assertIn("no denied call was observed", self.q2["answer"])


class ReorderedIdenticalCallsMustNotInvertQ3(unittest.TestCase):
    """Counter-example 2 -- the review's reordered-call repro.

    Two `test` calls share a verb and an argument digest, so they are one
    fingerprint. The failing one really arrived as post_tool_use_failure; the
    first version paired transcript order with adapter order by list position
    and therefore answered post_tool_use -- the opposite conclusion.

    Here the transcript order (passing call first) deliberately disagrees with
    the adapter's execution order (failing call first).
    """

    def setUp(self):
        events = [
            pre("t_pass", "test", []), term("t_pass", "post_tool_use", stdout=PASS_OUT),
            pre("t_fail", "test", []), term("t_fail", "post_tool_use_failure", stdout=None),
        ]
        adapter = [line(1, "test", [], 1, FAIL_OUT), line(2, "test", [], 0, PASS_OUT)]
        self.q3 = analyse(events, adapter)["q3"]

    def test_does_not_answer_post_tool_use(self):
        self.assertNotEqual(self.q3["answer"], "non-zero exits arrived as post_tool_use")

    def test_answers_failure_via_population_route(self):
        self.assertEqual(self.q3["status"], ANSWERED)
        self.assertEqual(self.q3["answer"], "non-zero exits arrived as post_tool_use_failure")

    def test_the_failure_event_is_declared_unattributable(self):
        # It carries no stdout, so identity cannot be established for it; the
        # answer comes from counting, and the analyser must say so.
        self.assertTrue(any("no stdout digest" in why for _, why in self.q3["unattributable"]))

    def test_the_passing_call_is_attributed_by_digest_not_position(self):
        self.assertIn({"verb": "test", "exit": 0, "event": "post_tool_use"}, self.q3["certain"])


class IndistinguishableCallsMustStayUnanswered(unittest.TestCase):
    """Counter-example 3 -- ambiguity must not be resolved by guessing.

    Same fingerprint, same stdout, different exit codes, and one call missing its
    terminal event. Neither route may fire: digests cannot separate the calls,
    and a missing terminal event means 'zero failure events' no longer implies
    'the failure arrived as post_tool_use'.
    """

    def setUp(self):
        events = [
            pre("t1", "test", []), term("t1", "post_tool_use", stdout="same"),
            pre("t2", "test", []),  # terminal event absent
        ]
        adapter = [line(1, "test", [], 1, "same"), line(2, "test", [], 0, "same")]
        self.q3 = analyse(events, adapter)["q3"]

    def test_status_is_unanswered(self):
        self.assertEqual(self.q3["status"], UNANSWERED)

    def test_population_route_is_withdrawn(self):
        self.assertTrue(any("WITHDRAWN" in r for r in self.q3["routes"]))

    def test_conflicting_digests_are_reported(self):
        self.assertTrue(any("disagree on exit" in why for _, why in self.q3["unattributable"]))


class BrokenSharedObservableMustNotMasqueradeAsAmbiguity(unittest.TestCase):
    """Counter-example 4 -- zero candidates means a broken join, not ambiguity."""

    def setUp(self):
        events = [
            pre("t1", "read", ["TASK.md"]),
            term("t1", "post_tool_use", stdout="first\r\nsecond"),
        ]
        adapter = [line(1, "read", ["TASK.md"], 0, "first\nsecond")]
        self.q3 = analyse(events, adapter)["q3"]

    def test_zero_candidate_reason_names_the_broken_join(self):
        reasons = [why for _, why in self.q3["unattributable"]]
        self.assertTrue(any("cross-side join is broken" in why for why in reasons))

    def test_zero_candidate_reason_does_not_claim_several_lines_exist(self):
        reasons = [why for _, why in self.q3["unattributable"]]
        self.assertFalse(any("several adapter lines" in why for why in reasons))


class OperatorProbeIsNotContainment(unittest.TestCase):
    """Counter-example 5 -- the same false success, one step later.

    The new launch procedure issues a deliberate `echo gate2-liveness-probe`
    before the task prompt, to prove the hooks are loaded at all. That denial is
    the operator's, not the producer's. A run whose only denial is that probe
    must not read as 'the producer was contained' -- nothing tried to escape.
    """

    def setUp(self):
        events = [pre("p1", "", [], decision="deny", command="echo gate2-liveness-probe"),
                  pre("t1", "status", []), term("t1", stdout="")]
        self.q2 = analyse(events, [line(1, "status", [], 0, "")])["q2"]

    def test_deny_path_is_confirmed(self):
        self.assertEqual(self.q2["status"], ANSWERED)
        self.assertTrue(self.q2["answer"].startswith("HONOURED"))

    def test_but_containment_is_flagged_untested(self):
        self.assertIn("untested", self.q2["answer"])
        self.assertEqual(self.q2["producer_denials"], 0)
        self.assertEqual(self.q2["probe_denials"], 1)

    def test_a_real_producer_denial_removes_the_caveat(self):
        events = [pre("p1", "", [], decision="deny", command="echo gate2-liveness-probe"),
                  pre("p2", "", [], decision="deny", command="cat /work/repo/src/calc.py")]
        q2 = analyse(events, [])["q2"]
        self.assertNotIn("untested", q2["answer"])
        self.assertEqual(q2["producer_denials"], 1)


class HonestPositives(unittest.TestCase):
    """The analyser must still answer when the evidence genuinely settles it."""

    def test_a_real_denial_is_reported_as_honoured(self):
        events = [pre("t1", "ls", []), term("t1", stdout="x"),
                  pre("t2", "", [], decision="deny", command="cat /etc/passwd")]
        q2 = analyse(events, [line(1, "ls", [], 0, "x")])["q2"]
        self.assertEqual(q2["status"], ANSWERED)
        self.assertIn("HONOURED", q2["answer"])

    def test_a_denial_that_produced_a_result_is_reported_as_leaked(self):
        events = [pre("t1", "", [], decision="deny", command="cat /etc/passwd"),
                  term("t1", stdout="root:x:0:0")]
        q2 = analyse(events, [])["q2"]
        self.assertEqual(q2["status"], ANSWERED)
        self.assertIn("LEAKED", q2["answer"])

    def test_nonzero_exit_with_no_failure_events_answers_post_tool_use(self):
        events = [pre("t1", "test", []), term("t1", "post_tool_use", stdout=FAIL_OUT)]
        q3 = analyse(events, [line(1, "test", [], 1, FAIL_OUT)])["q3"]
        self.assertEqual(q3["status"], ANSWERED)
        self.assertEqual(q3["answer"], "non-zero exits arrived as post_tool_use")

    def test_q1_is_unanswered_until_all_three_events_occur(self):
        events = [pre("t1", "ls", []), term("t1", stdout="x")]
        q1 = analyse(events, [line(1, "ls", [], 0, "x")])["q1"]
        self.assertEqual(q1["status"], UNANSWERED)
        self.assertIn("post_tool_use_failure", q1["answer"])

    def test_q1_answers_yes_only_with_all_three(self):
        events = [pre("t1", "ls", []), term("t1", stdout="x"),
                  pre("t2", "test", []), term("t2", "post_tool_use_failure")]
        q1 = analyse(events, [line(1, "ls", [], 0, "x"), line(2, "test", [], 1, "y")])["q1"]
        self.assertEqual(q1["status"], ANSWERED)
        self.assertTrue(q1["answer"].startswith("YES"))

    def test_missing_tool_use_id_is_a_reported_failure(self):
        bad = term("t1", stdout="x")
        bad["tool_use_id"] = None
        events = [pre("t1", "ls", []), bad]
        q1 = analyse(events, [line(1, "ls", [], 0, "x")])["q1"]
        self.assertEqual(q1["status"], ANSWERED)
        self.assertTrue(q1["answer"].startswith("NO"))


class PartialRunsMustStillRender(unittest.TestCase):
    """Counter-example 6 -- found by the first real session, not by imagination.

    A run that ends before any call is allowed produces pre events only. That is
    the shape of every NO-GO, i.e. the case the operator is most likely to point
    the analyser at -- and `render()` crashed on it with a KeyError, because the
    'no terminal event' branch of Q4 omitted a key the renderer reads.
    """

    def _render(self, events, adapter):
        import contextlib
        import io
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            render(analyse(events, adapter))
        return buf.getvalue()

    def test_denials_only_renders(self):
        events = [pre("t1", "", [], decision="deny", command="ls -la /somewhere 2>&1"),
                  pre("t2", "", [], decision="deny", command="echo gate2-liveness-probe")]
        out = self._render(events, [])
        self.assertIn("Q4", out)
        self.assertIn("Q5", out)
        self.assertIn("unanswered", out)

    def test_completely_empty_renders(self):
        out = self._render([], [])
        self.assertIn("0 events", out)

    def test_q4_is_unanswered_without_terminal_events(self):
        q4 = analyse([pre("t1", "", [], decision="deny", command="cat x")], [])["q4"]
        self.assertEqual(q4["status"], UNANSWERED)


class ParallelismClaims(unittest.TestCase):
    def test_absence_of_contention_is_not_an_answer(self):
        q5 = analyse([], [line(1, "ls", [], 0, "x")])["q5"]
        self.assertEqual(q5["status"], UNANSWERED)

    def test_contention_is_an_answer(self):
        q5 = analyse([], [line(1, "ls", [], 0, "x"), line(2, "ls", [], 0, "x", lock_wait_ms=37)])["q5"]
        self.assertEqual(q5["status"], ANSWERED)
        self.assertIn("overlapping", q5["answer"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
