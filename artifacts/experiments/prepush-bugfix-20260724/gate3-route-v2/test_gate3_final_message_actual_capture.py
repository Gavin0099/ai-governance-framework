from __future__ import annotations

import copy
import json

import pytest

import gate3_final_message_actual_capture as capture


RAW_COMPLETE_AGENT = (
    b'{"thread_id":"private-thread","type":"thread.started"}\n'
    b'{"private":"ignored","type":"turn.started"}\n'
    b'{"item":{"id":"private-item","text":"SECRET_CANARY","type":"agent_message"},"type":"item.started"}\n'
    b'{"item":{"message":"SECRET_CANARY","type":"agent_message"},"type":"item.completed"}\n'
    b'{"type":"turn.completed","usage":{"tokens":999}}\n'
)

RAW_COMPLETE_NO_ITEMS = (
    b'{"type":"thread.started"}\n'
    b'{"type":"turn.started"}\n'
    b'{"type":"turn.completed"}\n'
)

RAW_COMPLETE_OTHER = (
    b'{"type":"thread.started"}\n'
    b'{"type":"turn.started"}\n'
    b'{"item":{"output":"SECRET_CANARY","type":"tool_result"},"type":"item.completed"}\n'
    b'{"type":"turn.completed"}\n'
)

IGNORED_FIELD_NAMES = (
    "text",
    "message",
    "reasoning",
    "command",
    "arguments",
    "output",
    "result",
    "diff",
    "path",
    "thread_id",
    "id",
    "usage",
    "model",
    "url",
    "mcp",
    "environment",
    "credential",
)

IGNORED_EVENT_POSITIONS = (
    ("thread.started", "top"),
    ("turn.started", "top"),
    ("item.started", "top"),
    ("item.started", "item"),
    ("item.updated", "top"),
    ("item.updated", "item"),
    ("item.completed", "top"),
    ("item.completed", "item"),
    ("turn.completed", "top"),
    ("turn.failed", "top"),
    ("error", "top"),
)

EXPECTED_COMPLETE_AGENT_PROJECTION_BYTES = (
    b'{"action_sha256":"000e728a3555becf524dc2f9ef0d0b6338ccd024d5aebdc3d89ee74a0170feb2",'
    b'"adapter_contract_sha256":"be06661ba87ecdb3255524aedf6df775f27b96b9a57c8a1c005150a0755c1206",'
    b'"command_contract_sha256":"acf0a0e666cf976901a50f8e28d37f136c88852535559e2ae2bfde7e166d26da",'
    b'"entries":[{"item_marker":"none","marker":"thread_started","ordinal":0},'
    b'{"item_marker":"none","marker":"turn_started","ordinal":1},'
    b'{"item_marker":"agent_message","marker":"item_started","ordinal":2},'
    b'{"item_marker":"agent_message","marker":"item_completed","ordinal":3},'
    b'{"item_marker":"none","marker":"turn_completed","ordinal":4}],'
    b'"projector_sha256":"e60f346e182e8c146e3aaadda2aa3c659abf22a03ae641b1c45769a81b0e3965",'
    b'"raw_retention":"NONE","schema":"gate3-route-v2.actual-lifecycle-projection.v1"}\n'
)

EXPECTED_NO_ITEM_PROJECTION_BYTES = (
    b'{"action_sha256":"000e728a3555becf524dc2f9ef0d0b6338ccd024d5aebdc3d89ee74a0170feb2",'
    b'"adapter_contract_sha256":"be06661ba87ecdb3255524aedf6df775f27b96b9a57c8a1c005150a0755c1206",'
    b'"command_contract_sha256":"acf0a0e666cf976901a50f8e28d37f136c88852535559e2ae2bfde7e166d26da",'
    b'"entries":[{"item_marker":"none","marker":"thread_started","ordinal":0},'
    b'{"item_marker":"none","marker":"turn_started","ordinal":1},'
    b'{"item_marker":"none","marker":"turn_completed","ordinal":2}],'
    b'"projector_sha256":"e60f346e182e8c146e3aaadda2aa3c659abf22a03ae641b1c45769a81b0e3965",'
    b'"raw_retention":"NONE","schema":"gate3-route-v2.actual-lifecycle-projection.v1"}\n'
)


def bindings(*, arm: str = "A") -> capture.CaptureBindings:
    return capture.synthetic_bindings(arm=arm)


def process_result(**overrides: object) -> dict[str, object]:
    values: dict[str, object] = {
        "exit_code": 0,
        "process_disposition": "EXITED",
        "stdout_eof": True,
        "stdout_reader_complete": True,
        "stdout_read_failed": False,
    }
    values.update(overrides)
    return capture.build_process_result(**values)  # type: ignore[arg-type]


def publish_complete(
    raw: bytes = RAW_COMPLETE_AGENT,
) -> tuple[capture.CreateOnceStore, capture.CaptureBindings, dict[str, object]]:
    store = capture.CreateOnceStore()
    current = bindings()
    publisher = capture.CapturePublisher(store)
    publisher.authorize(current)
    result = publisher.capture(raw, process_result(), current)
    return store, current, result


def raw_with_position_canary(
    event_type: str, position: str, field_name: str, canary: str
) -> bytes:
    target: dict[str, object] = {"type": event_type}
    if event_type.startswith("item."):
        target["item"] = {"type": "agent_message"}
    destination = target if position == "top" else target["item"]
    assert isinstance(destination, dict)
    destination[field_name] = canary

    if event_type == "thread.started":
        events = [target, {"type": "turn.started"}, {"type": "turn.completed"}]
    elif event_type == "turn.started":
        events = [{"type": "thread.started"}, target, {"type": "turn.completed"}]
    elif event_type.startswith("item."):
        events = [
            {"type": "thread.started"},
            {"type": "turn.started"},
            target,
            {"type": "turn.completed"},
        ]
    else:
        events = [{"type": "thread.started"}, {"type": "turn.started"}, target]
    return b"".join(
        json.dumps(event, separators=(",", ":")).encode("utf-8") + b"\n"
        for event in events
    )


def test_complete_projection_matches_independent_retained_bytes() -> None:
    store, _, result = publish_complete()

    assert store.read(capture.PROJECTION_PATH) == EXPECTED_COMPLETE_AGENT_PROJECTION_BYTES
    assert result["status"] == "COMPLETE"
    assert result["failure_code"] == "NONE"


def test_private_canaries_and_raw_metadata_never_reach_public_store() -> None:
    store, _, _ = publish_complete()
    combined = b"".join(store.files.values())

    assert b"SECRET_CANARY" not in combined
    assert b"private-thread" not in combined
    assert b"private-item" not in combined
    assert b'"tokens"' not in combined
    assert b"raw_sha" not in combined
    assert b"raw_length" not in combined


def test_every_ignored_content_family_is_removed_from_public_store() -> None:
    private_fields = {
        "reasoning": "CANARY_REASONING",
        "command": "CANARY_COMMAND",
        "arguments": "CANARY_ARGUMENTS",
        "result": "CANARY_RESULT",
        "diff": "CANARY_DIFF",
        "path": "CANARY_PATH",
        "model": "CANARY_MODEL",
        "url": "CANARY_URL",
        "mcp": "CANARY_MCP",
        "environment": "CANARY_ENVIRONMENT",
        "credential": "CANARY_CREDENTIAL",
    }
    events = [
        {"type": "thread.started", **private_fields},
        {"type": "turn.started", **private_fields},
        {"type": "item.completed", "item": {"type": "agent_message", **private_fields}},
        {"type": "turn.completed", **private_fields},
    ]
    raw = b"".join(
        json.dumps(event, separators=(",", ":")).encode("utf-8") + b"\n"
        for event in events
    )

    store, _, _ = publish_complete(raw)
    combined = b"".join(store.files.values())

    for canary in private_fields.values():
        assert canary.encode("ascii") not in combined


@pytest.mark.parametrize(("event_type", "position"), IGNORED_EVENT_POSITIONS)
@pytest.mark.parametrize("field_name", IGNORED_FIELD_NAMES)
def test_privacy_canary_is_removed_from_every_ignored_position(
    event_type: str, position: str, field_name: str
) -> None:
    canary = f"CANARY_{event_type}_{position}_{field_name}"
    raw = raw_with_position_canary(event_type, position, field_name, canary)

    store, _, result = publish_complete(raw)

    assert result["status"] == "COMPLETE"
    assert canary.encode("ascii") not in b"".join(store.files.values())


def test_unknown_item_type_is_other_and_axis_is_indeterminate() -> None:
    store, _, _ = publish_complete(RAW_COMPLETE_OTHER)
    projection = json.loads(store.read(capture.PROJECTION_PATH))

    assert projection["entries"][2] == {
        "item_marker": "other",
        "marker": "item_completed",
        "ordinal": 2,
    }
    assert capture.agent_message_axis(projection, bindings()) == "INDETERMINATE"
    assert b"tool_result" not in store.read(capture.PROJECTION_PATH)


def test_no_item_complete_lifecycle_reports_absent_without_final_answer_claim() -> None:
    store, _, _ = publish_complete(RAW_COMPLETE_NO_ITEMS)
    projection = json.loads(store.read(capture.PROJECTION_PATH))

    assert capture.agent_message_axis(projection, bindings()) == "ABSENT"
    assert b"FINAL_ANSWER" not in store.read(capture.PROJECTION_PATH)
    assert b"MODEL_COMPLETION" not in store.read(capture.PROJECTION_PATH)


def test_completed_agent_message_reports_present_only() -> None:
    store, _, _ = publish_complete()
    projection = json.loads(store.read(capture.PROJECTION_PATH))

    assert capture.agent_message_axis(projection, bindings()) == "PRESENT"


def test_started_but_not_completed_agent_message_is_indeterminate() -> None:
    raw = (
        b'{"type":"thread.started"}\n'
        b'{"type":"turn.started"}\n'
        b'{"item":{"type":"agent_message"},"type":"item.started"}\n'
        b'{"type":"turn.completed"}\n'
    )
    store, _, _ = publish_complete(raw)
    projection = json.loads(store.read(capture.PROJECTION_PATH))

    assert capture.agent_message_axis(projection, bindings()) == "INDETERMINATE"


@pytest.mark.parametrize(
    ("raw", "code"),
    [
        (b"", "FRAMING_INVALID"),
        (b'{"type":"thread.started"}', "FRAMING_INVALID"),
        (b'{"type":"thread.started"}\r\n', "FRAMING_INVALID"),
        (b'{"type":"thread.started"}\n\n', "FRAMING_INVALID"),
        (b'[{"type":"thread.started"}]\n', "JSON_INVALID"),
        (b'{"type":"thread.started"}{"type":"turn.started"}\n', "JSON_INVALID"),
        (b"\xff\n", "UTF8_INVALID"),
        (b"{not-json}\n", "JSON_INVALID"),
        (b'{"private":NaN,"type":"thread.started"}\n', "JSON_INVALID"),
        (b'{"private":Infinity,"type":"thread.started"}\n', "JSON_INVALID"),
    ],
)
def test_framing_and_decode_failures_are_closed(raw: bytes, code: str) -> None:
    with pytest.raises(capture.CaptureError) as caught:
        capture.parse_private_ndjson(raw)

    assert caught.value.code == code
    private_prefix = raw[:12].decode("latin1", errors="ignore")
    if private_prefix:
        assert private_prefix not in str(caught.value)


def test_unknown_top_level_event_fails_closed_without_publishing_value() -> None:
    raw = (
        b'{"type":"thread.started"}\n'
        b'{"type":"turn.started"}\n'
        b'{"type":"future.private.secret"}\n'
    )
    publisher = capture.CapturePublisher(capture.CreateOnceStore())
    current = bindings()
    publisher.authorize(current)

    result = publisher.capture(raw, process_result(), current)

    assert result["status"] == "INVALID"
    assert result["failure_code"] == "UNKNOWN_EVENT_TYPE"
    assert b"future.private.secret" not in b"".join(publisher.store.files.values())


def test_unknown_event_after_terminal_invalidates_entire_capture() -> None:
    raw = (
        b'{"type":"thread.started"}\n'
        b'{"type":"turn.started"}\n'
        b'{"type":"turn.completed"}\n'
        b'{"type":"future.private.secret"}\n'
    )
    publisher = capture.CapturePublisher(capture.CreateOnceStore())
    current = bindings()
    publisher.authorize(current)

    result = publisher.capture(raw, process_result(), current)

    assert result["status"] == "INVALID"
    assert result["failure_code"] == "UNKNOWN_EVENT_TYPE"
    assert capture.PROJECTION_PATH not in publisher.store.files


def test_duplicate_type_key_cannot_hide_unknown_event() -> None:
    raw = (
        b'{"type":"future.private.secret","type":"thread.started"}\n'
        b'{"type":"turn.started"}\n'
        b'{"type":"turn.completed"}\n'
    )
    publisher = capture.CapturePublisher(capture.CreateOnceStore())
    current = bindings()
    publisher.authorize(current)

    result = publisher.capture(raw, process_result(), current)

    assert result["status"] == "INVALID"
    assert result["failure_code"] == "JSON_INVALID"
    assert b"future.private.secret" not in b"".join(publisher.store.files.values())


def test_unexpected_private_parser_exception_is_sanitized(monkeypatch: pytest.MonkeyPatch) -> None:
    def explode(*args: object, **kwargs: object) -> object:
        raise RuntimeError("SECRET_CANARY_FROM_PARSER")

    monkeypatch.setattr(capture.json, "loads", explode)

    with pytest.raises(capture.CaptureError) as caught:
        capture.parse_private_ndjson(RAW_COMPLETE_NO_ITEMS)

    assert caught.value.code == "JSON_INVALID"
    assert "SECRET_CANARY_FROM_PARSER" not in str(caught.value)


@pytest.mark.parametrize(
    "event",
    [
        b'{"type":"item.started"}',
        b'{"item":null,"type":"item.started"}',
        b'{"item":{"type":""},"type":"item.completed"}',
        b'{"item":{"type":7},"type":"item.updated"}',
    ],
)
def test_invalid_item_discriminants_fail_closed(event: bytes) -> None:
    raw = b'{"type":"thread.started"}\n{"type":"turn.started"}\n' + event + b"\n"
    publisher = capture.CapturePublisher(capture.CreateOnceStore())
    current = bindings()
    publisher.authorize(current)

    result = publisher.capture(raw, process_result(), current)

    assert result["status"] == "INVALID"
    assert result["failure_code"] == "ITEM_DISCRIMINANT_INVALID"


@pytest.mark.parametrize(
    "raw",
    [
        b'{"type":"turn.started"}\n{"type":"turn.completed"}\n',
        b'{"type":"thread.started"}\n{"type":"turn.completed"}\n',
        b'{"type":"thread.started"}\n{"type":"turn.started"}\n',
        b'{"type":"thread.started"}\n{"type":"turn.started"}\n{"type":"turn.completed"}\n{"type":"error"}\n',
        b'{"type":"thread.started"}\n{"type":"turn.started"}\n{"type":"thread.started"}\n{"type":"turn.completed"}\n',
    ],
)
def test_incomplete_or_contradictory_lifecycle_is_not_normalized(raw: bytes) -> None:
    publisher = capture.CapturePublisher(capture.CreateOnceStore())
    current = bindings()
    publisher.authorize(current)

    result = publisher.capture(raw, process_result(), current)

    assert result["status"] == "INCOMPLETE"
    assert result["failure_code"] == "LIFECYCLE_INCOMPLETE"
    assert capture.PROJECTION_PATH not in publisher.store.files


def test_turn_failure_and_stream_error_are_complete_closed_terminals() -> None:
    for terminal in (b'{"reason":"SECRET","type":"turn.failed"}\n', b'{"message":"SECRET","type":"error"}\n'):
        raw = b'{"type":"thread.started"}\n{"type":"turn.started"}\n' + terminal
        store, _, result = publish_complete(raw)
        projection = json.loads(store.read(capture.PROJECTION_PATH))
        assert result["status"] == "COMPLETE"
        assert projection["entries"][-1]["marker"] in {"turn_failed", "stream_error"}
        assert b"SECRET" not in store.read(capture.PROJECTION_PATH)


def test_missing_eof_or_reader_completion_is_incomplete() -> None:
    for overrides in (
        {"stdout_eof": False},
        {"stdout_reader_complete": False},
    ):
        publisher = capture.CapturePublisher(capture.CreateOnceStore())
        current = bindings()
        publisher.authorize(current)
        result = publisher.capture(RAW_COMPLETE_NO_ITEMS, process_result(**overrides), current)
        assert result["status"] == "INCOMPLETE"
        assert result["failure_code"] == "LIFECYCLE_INCOMPLETE"


def test_stdout_read_failure_is_unavailable() -> None:
    publisher = capture.CapturePublisher(capture.CreateOnceStore())
    current = bindings()
    publisher.authorize(current)
    result = publisher.capture(
        b"private bytes never parsed",
        process_result(
            stdout_eof=False,
            stdout_reader_complete=False,
            stdout_read_failed=True,
        ),
        current,
    )

    assert result["status"] == "UNAVAILABLE"
    assert result["failure_code"] == "STDOUT_READ_FAILED"
    assert capture.PROJECTION_PATH not in publisher.store.files


def test_size_limits_accept_boundary_and_reject_one_byte_over() -> None:
    prefix = b'{"pad":"'
    suffix = b'","type":"thread.started"}'
    exact_line = prefix + b"x" * (
        capture.MAX_LINE_BYTES - len(prefix) - len(suffix)
    ) + suffix
    over_line = prefix + b"x" * (
        capture.MAX_LINE_BYTES + 1 - len(prefix) - len(suffix)
    ) + suffix

    assert len(exact_line) == capture.MAX_LINE_BYTES
    assert capture.parse_private_ndjson(exact_line + b"\n")[0].marker == "thread_started"
    with pytest.raises(capture.CaptureError, match="SIZE_LIMIT_EXCEEDED"):
        capture.parse_private_ndjson(over_line + b"\n")

    total_line = prefix + b"x" * (
        (1 << 20) - 1 - len(prefix) - len(suffix)
    ) + suffix + b"\n"
    exact_total = total_line * 32
    assert len(exact_total) == capture.MAX_TOTAL_BYTES
    assert len(capture.parse_private_ndjson(exact_total)) == 32
    with pytest.raises(capture.CaptureError, match="SIZE_LIMIT_EXCEEDED"):
        capture.parse_private_ndjson(exact_total + b"x")


def test_authorization_binds_exact_source_contract_schema_action_and_arm() -> None:
    current = bindings()
    authorization = current.authorization()

    assert authorization["adapter_source_sha256"] == capture.module_source_sha256()
    assert authorization["public_schema_sha256"] == capture.public_schema_sha256()
    assert authorization["action_sha256"] == current.action_sha256
    assert authorization["arm"] == "A"
    assert authorization["capture_ordinal"] == 1
    assert authorization["retry"] is False
    assert authorization["replacement"] is False


@pytest.mark.parametrize(
    "contract_name",
    [
        "ADAPTER_CONTRACT_BYTES",
        "RAW_ENVELOPE_CONTRACT_BYTES",
        "PROJECTOR_CONTRACT_BYTES",
    ],
)
def test_contract_byte_replacement_after_authorization_blocks_capture(
    monkeypatch: pytest.MonkeyPatch, contract_name: str
) -> None:
    store = capture.CreateOnceStore()
    publisher = capture.CapturePublisher(store)
    current = bindings()
    publisher.authorize(current)
    monkeypatch.setattr(
        capture, contract_name, getattr(capture, contract_name) + b"mutation"
    )

    with pytest.raises(capture.CaptureError, match="CAPTURE_CONTRACT_MISMATCH"):
        publisher.capture(RAW_COMPLETE_NO_ITEMS, process_result(), current)

    assert set(store.files) == {capture.AUTHORIZATION_PATH}


def test_source_replacement_after_authorization_blocks_capture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = capture.CreateOnceStore()
    publisher = capture.CapturePublisher(store)
    current = bindings()
    publisher.authorize(current)
    monkeypatch.setattr(capture, "module_source_sha256", lambda: "0" * 64)

    with pytest.raises(capture.CaptureError, match="CAPTURE_CONTRACT_MISMATCH"):
        publisher.capture(RAW_COMPLETE_NO_ITEMS, process_result(), current)


def test_schema_replacement_after_authorization_blocks_capture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = capture.CreateOnceStore()
    publisher = capture.CapturePublisher(store)
    current = bindings()
    publisher.authorize(current)
    monkeypatch.setitem(capture.PUBLIC_SCHEMA_BYTES, "projection", b"mutation\n")

    with pytest.raises(capture.CaptureError, match="CAPTURE_CONTRACT_MISMATCH"):
        publisher.capture(RAW_COMPLETE_NO_ITEMS, process_result(), current)


def test_contract_replacement_between_process_result_and_parse_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = capture.CreateOnceStore()
    publisher = capture.CapturePublisher(store)
    current = bindings()
    publisher.authorize(current)
    original_publish = store.publish

    def mutate_after_process(path: str, payload: bytes) -> str:
        digest = original_publish(path, payload)
        if path == capture.PROCESS_RESULT_PATH:
            monkeypatch.setattr(
                capture,
                "RAW_ENVELOPE_CONTRACT_BYTES",
                capture.RAW_ENVELOPE_CONTRACT_BYTES + b"mutation",
            )
        return digest

    monkeypatch.setattr(store, "publish", mutate_after_process)

    result = publisher.capture(RAW_COMPLETE_NO_ITEMS, process_result(), current)

    assert result["status"] == "UNAVAILABLE"
    assert result["failure_code"] == "CAPTURE_CONTRACT_MISMATCH"
    assert capture.PROJECTION_PATH not in store.files


def test_capture_limits_cannot_be_overridden() -> None:
    store = capture.CreateOnceStore()
    publisher = capture.CapturePublisher(store)
    current = bindings()
    publisher.authorize(current)

    with pytest.raises(TypeError):
        publisher.capture(  # type: ignore[call-arg]
            RAW_COMPLETE_NO_ITEMS,
            process_result(),
            current,
            max_line_bytes=capture.MAX_LINE_BYTES + 1,
        )


@pytest.mark.parametrize("limit_name", ["MAX_LINE_BYTES", "MAX_TOTAL_BYTES"])
def test_runtime_limit_mutation_after_authorization_blocks_before_parse(
    monkeypatch: pytest.MonkeyPatch, limit_name: str
) -> None:
    store = capture.CreateOnceStore()
    publisher = capture.CapturePublisher(store)
    current = bindings()
    publisher.authorize(current)
    monkeypatch.setattr(capture, limit_name, getattr(capture, limit_name) + 100)

    with pytest.raises(capture.CaptureError, match="CAPTURE_CONTRACT_MISMATCH"):
        publisher.capture(RAW_COMPLETE_NO_ITEMS, process_result(), current)

    assert set(store.files) == {capture.AUTHORIZATION_PATH}


def test_contract_mismatch_fails_before_process_result_and_cannot_retry() -> None:
    store = capture.CreateOnceStore()
    publisher = capture.CapturePublisher(store)
    publisher.authorize(bindings(arm="A"))

    with pytest.raises(capture.CaptureError, match="CAPTURE_CONTRACT_MISMATCH"):
        publisher.capture(RAW_COMPLETE_NO_ITEMS, process_result(), bindings(arm="B"))

    assert set(store.files) == {capture.AUTHORIZATION_PATH}
    with pytest.raises(capture.CaptureError, match="CAPTURE_RESULT_UNKNOWN"):
        publisher.capture(RAW_COMPLETE_NO_ITEMS, process_result(), bindings(arm="A"))


def test_duplicate_authorization_cannot_create_retry_authority() -> None:
    store = capture.CreateOnceStore()
    publisher = capture.CapturePublisher(store)
    publisher.authorize(bindings())

    with pytest.raises(capture.CaptureError, match="CAPTURE_ALREADY_AUTHORIZED"):
        publisher.authorize(bindings())


def test_crash_before_authorization_leaves_no_authority() -> None:
    store = capture.CreateOnceStore()
    store.arm_crash(capture.AUTHORIZATION_PATH, "before")
    publisher = capture.CapturePublisher(store)

    with pytest.raises(capture.SyntheticCrash, match="BEFORE_DURABILITY"):
        publisher.authorize(bindings())

    assert capture.reconstruct_state(store) == "NOT_AUTHORIZED"


def test_crash_after_authorization_is_permanently_unknown_after_restart() -> None:
    store = capture.CreateOnceStore()
    store.arm_crash(capture.AUTHORIZATION_PATH, "after")
    publisher = capture.CapturePublisher(store)

    with pytest.raises(capture.SyntheticCrash, match="AFTER_DURABILITY"):
        publisher.authorize(bindings())

    reopened = capture.CapturePublisher(store.clone())
    assert capture.reconstruct_state(reopened.store) == "CAPTURE_RESULT_UNKNOWN"
    with pytest.raises(capture.CaptureError, match="CAPTURE_RESULT_UNKNOWN"):
        reopened.capture(RAW_COMPLETE_NO_ITEMS, process_result(), bindings())


def test_orphan_projection_after_crash_is_not_adopted_on_restart() -> None:
    store = capture.CreateOnceStore()
    publisher = capture.CapturePublisher(store)
    current = bindings()
    publisher.authorize(current)
    store.arm_crash(capture.PROJECTION_PATH, "after")

    with pytest.raises(capture.SyntheticCrash, match="AFTER_DURABILITY"):
        publisher.capture(RAW_COMPLETE_NO_ITEMS, process_result(), current)

    reopened = capture.CapturePublisher(store.clone())
    assert capture.PROJECTION_PATH in reopened.store.files
    assert capture.CAPTURE_RESULT_PATH not in reopened.store.files
    assert capture.verify_public(reopened.store, current).code == "CAPTURE_RESULT_UNKNOWN"
    with pytest.raises(capture.CaptureError, match="CAPTURE_RESULT_UNKNOWN"):
        reopened.capture(RAW_COMPLETE_NO_ITEMS, process_result(), current)


def test_identical_orphan_projection_is_not_adopted() -> None:
    store = capture.CreateOnceStore()
    publisher = capture.CapturePublisher(store)
    current = bindings()
    publisher.authorize(current)
    store.publish(capture.PROJECTION_PATH, EXPECTED_NO_ITEM_PROJECTION_BYTES)

    result = publisher.capture(RAW_COMPLETE_NO_ITEMS, process_result(), current)

    assert result["failure_code"] == "PUBLICATION_FAILED"
    assert result["projection_sha256"] == "NONE"
    assert capture.verify_public(store, current).verified is False


@pytest.mark.parametrize("path", [capture.PROCESS_RESULT_PATH, capture.PROJECTION_PATH])
def test_crash_after_intermediate_durability_remains_unknown(path: str) -> None:
    store = capture.CreateOnceStore()
    publisher = capture.CapturePublisher(store)
    current = bindings()
    publisher.authorize(current)
    store.arm_crash(path, "after")

    with pytest.raises(capture.SyntheticCrash, match="AFTER_DURABILITY"):
        publisher.capture(RAW_COMPLETE_NO_ITEMS, process_result(), current)

    reopened = capture.CapturePublisher(store.clone())
    assert capture.reconstruct_state(reopened.store) == "CAPTURE_RESULT_UNKNOWN"
    assert capture.verify_public(reopened.store, current).verified is False
    with pytest.raises(capture.CaptureError, match="CAPTURE_RESULT_UNKNOWN"):
        reopened.capture(RAW_COMPLETE_NO_ITEMS, process_result(), current)


def test_crash_after_result_durability_reopens_as_complete_attestation() -> None:
    store = capture.CreateOnceStore()
    publisher = capture.CapturePublisher(store)
    current = bindings()
    publisher.authorize(current)
    store.arm_crash(capture.CAPTURE_RESULT_PATH, "after")

    with pytest.raises(capture.SyntheticCrash, match="AFTER_DURABILITY"):
        publisher.capture(RAW_COMPLETE_NO_ITEMS, process_result(), current)

    reopened = store.clone()
    assert capture.reconstruct_state(reopened) == "RESULT_RETAINED"
    assert capture.verify_public(reopened, current).verified is True


def test_create_once_collision_never_overwrites_existing_bytes() -> None:
    store = capture.CreateOnceStore()
    first = b'{"first":true}\n'
    store.publish("x.json", first)

    with pytest.raises(capture.CaptureError, match="CREATE_ONCE_COLLISION"):
        store.publish("x.json", b'{"second":true}\n')

    assert store.read("x.json") == first


def test_projection_collision_becomes_publication_failure_and_tree_fails_closed() -> None:
    store = capture.CreateOnceStore()
    publisher = capture.CapturePublisher(store)
    current = bindings()
    publisher.authorize(current)
    store.publish(capture.PROJECTION_PATH, b'{"orphan":true}\n')

    result = publisher.capture(RAW_COMPLETE_NO_ITEMS, process_result(), current)

    assert result["status"] == "UNAVAILABLE"
    assert result["failure_code"] == "PUBLICATION_FAILED"
    assert capture.verify_public(store, current).verified is False
    assert store.read(capture.PROJECTION_PATH) == b'{"orphan":true}\n'


def test_complete_public_chain_verifies_only_internal_attestation_claim() -> None:
    store, current, _ = publish_complete()

    verdict = capture.verify_public(store, current)

    assert verdict == capture.Verification(
        True, "VERIFIED", "PUBLIC_CAPTURE_ATTESTATION_CHAIN_RECONSTRUCTED"
    )


def test_agent_message_axis_rejects_unvalidated_or_unknown_projection() -> None:
    current = bindings()
    with pytest.raises(capture.CaptureError, match="PRIVACY_VALIDATION_FAILED"):
        capture.agent_message_axis({"entries": []}, current)

    store, _, _ = publish_complete()
    projection = json.loads(store.read(capture.PROJECTION_PATH))
    projection["entries"][2]["item_marker"] = "future_message"
    with pytest.raises(capture.CaptureError, match="PRIVACY_VALIDATION_FAILED"):
        capture.agent_message_axis(projection, current)


def test_literal_fixture_detects_canonicalization_mutation() -> None:
    value = json.loads(EXPECTED_COMPLETE_AGENT_PROJECTION_BYTES)
    mutated = json.dumps(value, sort_keys=True, indent=2).encode("ascii") + b"\n"

    with pytest.raises(AssertionError):
        assert mutated == EXPECTED_COMPLETE_AGENT_PROJECTION_BYTES


@pytest.mark.parametrize(
    "mutation",
    ["ordinal", "action", "extra", "terminal_not_last", "item_none"],
)
def test_projection_mutations_fail_closed(mutation: str) -> None:
    store, current, _ = publish_complete()
    projection = json.loads(store.read(capture.PROJECTION_PATH))
    if mutation == "ordinal":
        projection["entries"][1]["ordinal"] = 9
    elif mutation == "action":
        projection["action_sha256"] = "0" * 64
    elif mutation == "extra":
        projection["raw_length"] = 7
    elif mutation == "terminal_not_last":
        projection["entries"].append(
            {"item_marker": "other", "marker": "item_completed", "ordinal": 5}
        )
    else:
        projection["entries"][2]["item_marker"] = "none"
    store.files[capture.PROJECTION_PATH] = capture.canonical_bytes(projection)

    verdict = capture.verify_public(store, current)

    assert verdict.verified is False


@pytest.mark.parametrize("mutation", ["status", "projection", "authorization", "process"])
def test_capture_result_link_and_row_mutations_fail_closed(mutation: str) -> None:
    store, current, _ = publish_complete()
    result = json.loads(store.read(capture.CAPTURE_RESULT_PATH))
    if mutation == "status":
        result["status"] = "INVALID"
    elif mutation == "projection":
        result["projection_sha256"] = "0" * 64
    elif mutation == "authorization":
        result["authorization_sha256"] = "0" * 64
    else:
        result["process_result_sha256"] = "0" * 64
    store.files[capture.CAPTURE_RESULT_PATH] = capture.canonical_bytes(result)

    verdict = capture.verify_public(store, current)

    assert verdict.verified is False


@pytest.mark.parametrize(
    "missing",
    [capture.AUTHORIZATION_PATH, capture.PROCESS_RESULT_PATH, capture.CAPTURE_RESULT_PATH, capture.PROJECTION_PATH],
)
def test_missing_public_link_fails_closed(missing: str) -> None:
    store, current, _ = publish_complete()
    del store.files[missing]

    verdict = capture.verify_public(store, current)

    assert verdict.verified is False


def test_noncanonical_public_bytes_fail_closed() -> None:
    store, current, _ = publish_complete()
    value = json.loads(store.read(capture.PROJECTION_PATH))
    store.files[capture.PROJECTION_PATH] = json.dumps(value, indent=2).encode() + b"\n"

    assert capture.verify_public(store, current).verified is False


def test_hostile_public_integer_returns_closed_verification() -> None:
    store, current, _ = publish_complete()
    store.files[capture.CAPTURE_RESULT_PATH] = (
        b'{"hostile_integer":' + b"9" * 5000 + b"}\n"
    )

    verdict = capture.verify_public(store, current)

    assert verdict == capture.Verification(False, "PUBLIC_ARTIFACT_INVALID", None)


def test_process_result_rejects_non_boolean_and_contradictory_reader_state() -> None:
    valid = process_result()
    for mutation in (
        {"stdout_eof": 1},
        {"stdout_read_failed": True},
        {"process_disposition": "BOGUS"},
    ):
        value = copy.deepcopy(valid)
        value.update(mutation)
        with pytest.raises(capture.CaptureError, match="PRIVACY_VALIDATION_FAILED"):
            capture.validate_process_result(value)


def test_authorization_without_result_verifier_never_infers_success() -> None:
    store = capture.CreateOnceStore()
    current = bindings()
    capture.CapturePublisher(store).authorize(current)

    assert capture.verify_public(store, current) == capture.Verification(
        False, "CAPTURE_RESULT_UNKNOWN", None
    )


def test_invalid_capture_can_verify_as_closed_negative_attestation() -> None:
    store = capture.CreateOnceStore()
    current = bindings()
    publisher = capture.CapturePublisher(store)
    publisher.authorize(current)
    result = publisher.capture(b"{bad}\n", process_result(), current)

    verdict = capture.verify_public(store, current)

    assert result["failure_code"] == "JSON_INVALID"
    assert verdict.verified is True
    assert verdict.claim == capture.PUBLIC_CLAIM
