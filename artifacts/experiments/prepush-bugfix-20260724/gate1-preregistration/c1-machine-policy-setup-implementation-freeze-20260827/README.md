# C1 machine-policy setup implementation freeze

This directory freezes a future, separately owner-authorized setup executor for
one machine-wide file:

`%ProgramData%\OpenAI\Codex\requirements.toml`

The only admissible payload is the committed 58-byte `requirements.toml` in
this directory. Existing target bytes, including identical bytes, are drift and
must not be adopted as success.

Before publication, the executor requires exact freeze/plan authority, a fresh
bounded machine observation, and a separately produced elevated owner-shell
rollback precheck. The standalone rollback script has no dependency on Codex,
`CODEX_HOME`, the sandbox account, or the hosted model.

The owner shell and executor communicate only through the exact frozen
`publication.coordination_root`. The owner creates that directory, runs the
standalone script in `Precheck` mode, and keeps the shell open. The executor
derives request, receipt, and heartbeat paths from the manifest; callers cannot
substitute them.

This freeze does not authorize setup or rollback. It does not change accounts,
firewall rules, logon rights, ACLs, or any other policy. It does not execute
sandbox qualification, a hosted request, randomization, producer, scorer, or
arms.

`MACHINE_POLICY_SETUP_APPLIED` proves only that the exact managed-requirements
file was atomically installed and bounded pre-existing invariants did not drift.
It does not prove task-command network denial or hosted transport availability.
