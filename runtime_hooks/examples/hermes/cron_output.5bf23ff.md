[Governance Contract]
LANG = Python
LEVEL = L1
SCOPE = review
PLAN = Real Hermes integration contract / Tranche 1A cron artifact fixture
LOADED = SYSTEM_PROMPT, HUMAN-OVERSIGHT, HERMES_RUNTIME_INTERFACE, HERMES_CRON_ARTIFACT_SPEC
CONTEXT = audited Hermes HEAD 5bf23ff -> cron output artifact; NOT: interactive or ACP output
PRESSURE = SAFE (20/200)
RULES = common,python
RISK = medium
OVERSIGHT = review-required
MEMORY_MODE = candidate

[Fixture Annotation]
This fixture intentionally contains a synthetic [Governance Contract] block so
the existing Hermes post_task adapter contract path can be exercised. Live
Hermes no_agent cron output observed at HEAD 5bf23ff did not emit this block.
Therefore this fixture is adapter-contract evidence, not live-output evidence
that raw Hermes cron artifacts are governance-contract compliant.

[Hermes Cron Artifact]
audited_external_head = 5bf23ff251ed54961f5560d2d2f95474dcc09386
source_type = cron_output_file
capture_boundary = native_file_artifact
session_id = hermes-session-5bf23ff-cron-01
cron_job_id = hermes-cron-job-01
cron_job_name = governance-attestation-smoke
cron_output_path = ~/.hermes/cron/output/hermes-cron-job-01/2026-06-22T00-00-00Z.md
run_timestamp_utc = 2026-06-22T00:00:00Z

[Final Response]
This fixture represents the natural Hermes cron markdown output artifact shape
observed during read-only audit. It is not live Hermes execution output and
does not prove cron delivery, runtime governance, tool execution
non-bypassability, or semantic correctness.
