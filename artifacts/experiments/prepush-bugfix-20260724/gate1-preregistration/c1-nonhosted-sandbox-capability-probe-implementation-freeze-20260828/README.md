# C1 non-hosted sandbox capability probe implementation freeze

This directory freezes one create-once, non-hosted probe that asks only whether
the pinned absolute Python executable can be launched through the exact Codex
Windows sandbox task-command filesystem/exec plane.

The only authorized future entrypoint is an owner-authorized commit blob streamed
to the exact Python interpreter with `-I -`. The bootstrap verifies the manifest,
the complete frozen inventory, every Git blob binding, and the interpreter before
streaming the verified executor.

The probe has two controls:

1. bare `python` must fail and must not create its marker;
2. the pinned absolute Python path may create the exact positive marker.

An unexpectedly successful negative control is invalid, never PASS. A positive
result is published only after private workspace and staged CLI cleanup complete.

This freeze does not execute the probe, read auth, make a hosted request, create
qualification-03, modify machine policy, create randomization, run producer,
scorer, or arms, release mapping, or POST to Rekor.
