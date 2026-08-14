"""Independent expected-byte oracle for the runner integration package.

This module holds expected canonical bytes as literals and **imports neither
``gate3_final_message_runner_integration`` nor
``gate3_final_message_actual_capture``**.  An import guard in the test suite
asserts that, so the expectations cannot silently become a round-trip of the
code under test.

What this does and does not establish.  A literal derived by hand and one pasted
out of the production serializer are byte-identical, and nothing retained here
distinguishes them.  The achievable properties are that the fixture is
runtime-independent of production code, and that its values have been
re-derived independently by a reviewer following
``gate3-runner-integration-oracle-worksheet.md``.  Re-derivation is
corroboration; it is not detection of how a literal was originally produced.
"""

from __future__ import annotations


ORACLE_V1_CONTRACT_BYTES = (
    b'{"checkpoints":["before_authorization","before_invocation",'
    b'"before_private_parse","before_seal"],'
    b'"cleanup_protocol":"CREATE_ONCE_AUTHORIZATION_THEN_RESULT_NO_RETRY",'
    b'"launch_ordinal":1,'
    b'"observation_protocol":"CREATE_ONCE_CHAIN_AUTHORIZATION_BEFORE_LAUNCH",'
    b'"profiles":["RUNNER_CAPTURE_FINALIZED","RUNNER_CAPTURE_NEGATIVE",'
    b'"RUNNER_CAPTURE_RESULT_UNKNOWN","RUNNER_SEAL_UNAVAILABLE"],'
    b'"replacement":false,"retry":false,"runtime_subjects":['
    b'"adapter_contract","adapter_source","integration_source",'
    b'"projector_contract","public_schemas","raw_contract","runner_source"],'
    b'"schema":"gate3-route-v2.runner-integration-contract.v1",'
    b'"stdout_handoff_count":1}\n'
)

ORACLE_V2_CONTRACT_BYTES = (
    b'{"checkpoints":["before_authorization","before_invocation",'
    b'"before_private_parse","before_seal"],'
    b'"cleanup_protocol":"CREATE_ONCE_AUTHORIZATION_THEN_RESULT_NO_RETRY",'
    b'"evidence_classes":["SYNTHETIC"],'
    b'"launch_ordinal":1,'
    b'"observation_protocol":"CREATE_ONCE_CHAIN_AUTHORIZATION_BEFORE_LAUNCH",'
    b'"profiles":["RUNNER_CAPTURE_FINALIZED","RUNNER_CAPTURE_NEGATIVE",'
    b'"RUNNER_CAPTURE_RESULT_UNKNOWN","RUNNER_SEAL_UNAVAILABLE"],'
    b'"replacement":false,"retry":false,"runtime_subjects":['
    b'"adapter_contract","adapter_source","bridge_source","integration_source",'
    b'"projector_contract","public_schemas","raw_contract","runner_source"],'
    b'"schema":"gate3-route-v2.runner-integration-contract.v2",'
    b'"stdout_handoff_count":1}\n'
)

# Complete-path package emitted under contract v2 by the synthetic fixture
# described in the worksheet.

ORACLE_V2_CAPTURE_BYTES = {
    "capture-authorization.json": (
        b'{"action_sha256":"000e728a3555becf524dc2f9ef0d0b6338ccd024d5aebd'
        b'c3d89ee74a0170feb2","adapter_contract_sha256":"be06661ba87ecdb32'
        b'55524aedf6df775f27b96b9a57c8a1c005150a0755c1206","adapter_source'
        b'_sha256":"67d098138d2442f1c68aae462d350a7a461e191d831b8bea8799d3'
        b'498ee1d99d","arm":"A","capture_ordinal":1,"command_contract_sha2'
        b'56":"acf0a0e666cf976901a50f8e28d37f136c88852535559e2ae2bfde7e166'
        b'd26da","executable_sha256":"8c9f2714c265887feeebfd9039ca9cf1fea4'
        b'6da886cf6b632cf55da4f8e0a331","lifecycle_projector_sha256":"e60f'
        b'346e182e8c146e3aaadda2aa3c659abf22a03ae641b1c45769a81b0e3965","p'
        b'ublic_schema_sha256":{"authorization":"9657d0a48f23b4497347bb279'
        b'd8a8e7561163ec925c3bbd2b6fbb78b78c3c05b","capture_result":"eb6c0'
        b'92660e95c4e51806b1f964335b176cb9e40220e2d5d78eb0c111c55c2ea","pr'
        b'ocess_result":"ea99de4bcadfe412d2e6796234836fa6c23208b255da3fe6a'
        b'7750c1e805e17bb","projection":"7492ca749c71175269920015efda288f6'
        b'646eec5216e9fa09ca5d872737e2784"},"raw_envelope_contract_sha256"'
        b':"6d04e7371b740435ad5aa2e10986e003d7157e7c0aef68de5f476f76afbc57'
        b'eb","replacement":false,"retry":false,"schema":"gate3-route-v2.c'
        b'apture-authorization.v1"}\n'
    ),
    "capture-result.json": (
        b'{"authorization_sha256":"77f62cdbd95ed6ab1314ed760c61c0b4e6fd6d9'
        b'b676dc7e1d20b9bc0a23b5edf","failure_code":"NONE","process_result'
        b'_sha256":"e762121801d1561ce157df9de85c06060854e988176314e9875c66'
        b'3703f8a050","projection_sha256":"2f5675e7b589a5af94fe253d8a3a930'
        b'1d807391e73c4449641d7de2cd46d5396","schema":"gate3-route-v2.capt'
        b'ure-result.v1","status":"COMPLETE"}\n'
    ),
    "lifecycle-projection.json": (
        b'{"action_sha256":"000e728a3555becf524dc2f9ef0d0b6338ccd024d5aebd'
        b'c3d89ee74a0170feb2","adapter_contract_sha256":"be06661ba87ecdb32'
        b'55524aedf6df775f27b96b9a57c8a1c005150a0755c1206","command_contra'
        b'ct_sha256":"acf0a0e666cf976901a50f8e28d37f136c88852535559e2ae2bf'
        b'de7e166d26da","entries":[{"item_marker":"none","marker":"thread_'
        b'started","ordinal":0},{"item_marker":"none","marker":"turn_start'
        b'ed","ordinal":1},{"item_marker":"agent_message","marker":"item_c'
        b'ompleted","ordinal":2},{"item_marker":"none","marker":"turn_comp'
        b'leted","ordinal":3}],"projector_sha256":"e60f346e182e8c146e3aaad'
        b'da2aa3c659abf22a03ae641b1c45769a81b0e3965","raw_retention":"NONE'
        b'","schema":"gate3-route-v2.actual-lifecycle-projection.v1"}\n'
    ),
    "process-result.json": (
        b'{"exit_code":0,"process_disposition":"EXITED","schema":"gate3-ro'
        b'ute-v2.content-free-process-result.v1","stdout_eof":true,"stdout'
        b'_read_failed":false,"stdout_reader_complete":true}\n'
    ),
}

ORACLE_V2_EVIDENCE_BYTES = {
    "final-output-observation.json": (
        b'{"schema":"gate3-route-v2.final-output-observation.v1","state":"'
        b'CAPTURED"}\n'
    ),
    "runner-cleanup-authorization.json": (
        b'{"attempt_ordinal":1,"profile":"RUNNER_CAPTURE_FINALIZED","retry'
        b'":false,"schema":"gate3-route-v2.runner-cleanup-authorization.v1'
        b'","seal_sha256":"fb2f2b7df95a5a6ea8882ed321e80feaa9086589ea8171f'
        b'446ab2c55574a6462"}\n'
    ),
    "runner-cleanup-result.json": (
        b'{"result":"PASS","schema":"gate3-route-v2.runner-cleanup-result.'
        b'v1","seal_sha256":"fb2f2b7df95a5a6ea8882ed321e80feaa9086589ea817'
        b'1f446ab2c55574a6462"}\n'
    ),
    "runner-finalization.json": (
        b'{"disposition":"FINALIZED_DIAGNOSTIC","profile":"RUNNER_CAPTURE_'
        b'FINALIZED","receipt_sha256":"4ab24fdadd079ccf4e0b7f238ec193450a6'
        b'5f35a894fa26319ec4be3a3b10dd1","schema":"gate3-route-v2.runner-f'
        b'inalization.v1"}\n'
    ),
    "runner-integration-authority.json": (
        b'{"action_sha256":"000e728a3555becf524dc2f9ef0d0b6338ccd024d5aebd'
        b'c3d89ee74a0170feb2","arm":"A","bridge_blob":"9ec1ba63e3a58e3bca4'
        b'eab9570871e9d2584f4c7742cc6ec660f418fbd708c33","capture_bindings'
        b'_sha256":"77f62cdbd95ed6ab1314ed760c61c0b4e6fd6d9b676dc7e1d20b9b'
        b'c0a23b5edf","capture_ordinal":1,"evidence_class":"SYNTHETIC","gi'
        b't_commit":"e7410b3469d4e3112904b4f822180e51d5c1a3ea","integratio'
        b'n_blob":"d0d1609bc111bb8cef28f8442f80beddeb6ad87744be9e74723d3e1'
        b'1126a19fd","integration_contract_sha256":"0c0fe789ff3046677b97ae'
        b'b93e90cd1fc4d2dbde63f5c3557d1f4aa5c11e7bb2","launch_ordinal":1,"'
        b'replacement":false,"retry":false,"runner_blob":"d308331cc59cfce5'
        b'0604488a2ab9121727338fd7886c61a7f2e6fa6b5b2af7e8","runtime_sha25'
        b'6":{"adapter_contract":"be06661ba87ecdb3255524aedf6df775f27b96b9'
        b'a57c8a1c005150a0755c1206","adapter_source":"67d098138d2442f1c68a'
        b'ae462d350a7a461e191d831b8bea8799d3498ee1d99d","bridge_source":"d'
        b'0217f85f36176902a1b9ad53963fd2b3b33f493e52b9fedff07cc13ef3dd080"'
        b',"integration_source":"4785aa2413b1bcc4cd1cc5112c9520e53691fb14c'
        b'07ab9cc0636f39f0af2510b","projector_contract":"e60f346e182e8c146'
        b'e3aaadda2aa3c659abf22a03ae641b1c45769a81b0e3965","public_schemas'
        b'":"eb47a6ce92326ab68a05f177c169cf99b93b971a0e39a77a96a797f497f1b'
        b'26d","raw_contract":"6d04e7371b740435ad5aa2e10986e003d7157e7c0ae'
        b'f68de5f476f76afbc57eb","runner_source":"e9be4d2adae79c99a314d1b7'
        b'9f15339b41b2dacdeed1424e23724ed136c481ff"},"schema":"gate3-route'
        b'-v2.runner-integration-authority.v2","workspace_baseline_sha256"'
        b':"c1d48ae4b34e1b5c878307b476e8d02ea188912ff5a977c782376fc536f2c8'
        b'a5"}\n'
    ),
    "runner-integration-contract.json": (
        b'{"checkpoints":["before_authorization","before_invocation","befo'
        b're_private_parse","before_seal"],"cleanup_protocol":"CREATE_ONCE'
        b'_AUTHORIZATION_THEN_RESULT_NO_RETRY","evidence_classes":["SYNTHE'
        b'TIC"],"launch_ordinal":1,"observation_protocol":"CREATE_ONCE_CHA'
        b'IN_AUTHORIZATION_BEFORE_LAUNCH","profiles":["RUNNER_CAPTURE_FINA'
        b'LIZED","RUNNER_CAPTURE_NEGATIVE","RUNNER_CAPTURE_RESULT_UNKNOWN"'
        b',"RUNNER_SEAL_UNAVAILABLE"],"replacement":false,"retry":false,"r'
        b'untime_subjects":["adapter_contract","adapter_source","bridge_so'
        b'urce","integration_source","projector_contract","public_schemas"'
        b',"raw_contract","runner_source"],"schema":"gate3-route-v2.runner'
        b'-integration-contract.v2","stdout_handoff_count":1}\n'
    ),
    "runner-observation-seal.json": (
        b'{"authority_sha256":"3dc98f9463af2a737cf40d5adaa071d06d93aa22174'
        b'd1503cc72ee7d4f168675","capture_artifact_sha256":{"capture-autho'
        b'rization.json":"77f62cdbd95ed6ab1314ed760c61c0b4e6fd6d9b676dc7e1'
        b'd20b9bc0a23b5edf","capture-result.json":"d0f3610664cc28d1f528514'
        b'e4377afe976b02407659f7c0fce67903ea21757d9","lifecycle-projection'
        b'.json":"2f5675e7b589a5af94fe253d8a3a9301d807391e73c4449641d7de2c'
        b'd46d5396","process-result.json":"e762121801d1561ce157df9de85c060'
        b'60854e988176314e9875c663703f8a050"},"capture_status":"COMPLETE",'
        b'"final_observation_sha256":"f052c4cdd94713533a6a7c3ff5d749681902'
        b'24ca176f5867864acf026216d1b4","integration_contract_sha256":"0c0'
        b'fe789ff3046677b97aeb93e90cd1fc4d2dbde63f5c3557d1f4aa5c11e7bb2","'
        b'observation_stage_sha256":"4b4bb2de9115282219fbef7c721413a35382c'
        b'35a1cafec8fe0e521a0b551be07","profile":"RUNNER_CAPTURE_FINALIZED'
        b'","schema":"gate3-route-v2.runner-observation-seal.v1","workspac'
        b'e_observation_sha256":"b1dd83d698aece172fbc8b6507161926c4535d696'
        b'4dd81ae9b2d4722853f4ccf"}\n'
    ),
    "runner-observation-stage.json": (
        b'{"capture_authorization_sha256":"77f62cdbd95ed6ab1314ed760c61c0b'
        b'4e6fd6d9b676dc7e1d20b9bc0a23b5edf","schema":"gate3-route-v2.obse'
        b'rvation-stage.v1","stage":"OBSERVATION_CHAIN_AUTHORIZED"}\n'
    ),
    "runner-receipt.json": (
        b'{"cleanup_sha256":"7caf22943ee3e4f8028c9d991e775eb26d269e3cf928b'
        b'e80fc96020e3d55ffa0","disposition":"DIAGNOSTIC_RECEIPT","profile'
        b'":"RUNNER_CAPTURE_FINALIZED","schema":"gate3-route-v2.runner-rec'
        b'eipt.v1","seal_sha256":"fb2f2b7df95a5a6ea8882ed321e80feaa9086589'
        b'ea8171f446ab2c55574a6462"}\n'
    ),
    "workspace-observation.json": (
        b'{"schema":"gate3-route-v2.workspace-observation.v1","state":"CHA'
        b'NGED"}\n'
    ),
}
