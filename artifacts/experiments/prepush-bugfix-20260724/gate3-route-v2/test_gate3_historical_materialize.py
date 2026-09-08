"""Focused tests for M2, now that materialization is handle-bound.

Every test supplies its own `base` and lets pytest remove it. The module never
creates or deletes a base — it borrows one — so a test that did not make its own
would be asking the module to do the one thing the design forbids.

The tree holds kernel handles while it exists, which changes what a test can
observe. A created file is held with `FILE_SHARE_READ` alone against a handle
carrying write and delete access, so an ordinary opener — including CPython's
`open()` — is refused and reading the bytes back through the path raises
`PermissionError`. That is the boundary working, and it is asserted here rather
than worked around. It is **not** total exclusion: a native reader that shares
read, write and delete does get in, which the boundary's own suite measures.

The bytes are still verified. `verify` reads each file back through the handle
that created it, which is what `read_all` exists for.
"""

from __future__ import annotations

import ast
import dataclasses
import hashlib
import os
import stat
import subprocess
from pathlib import Path

import pytest

import gate3_historical_materialize as materialize
import gate3_native_boundary as boundary


COMMIT = "204965c94bd843d599986d9f9d0fd552ea053dff"
BLOBS = {
    "a/one.py": b"print('one')\n",
    "a/b/two.py": b"print('two')\n",
    "three.md": b"# three\n",
}
INVENTORY = {
    path: hashlib.sha256(payload).hexdigest() for path, payload in BLOBS.items()
}


def reader(blobs=None):
    source = BLOBS if blobs is None else blobs

    def read_blob(commit: str, path: str) -> bytes:
        assert commit == COMMIT
        return source[path]

    return read_blob


@pytest.fixture
def base(tmp_path: Path) -> Path:
    """A base the test creates, and the module may only borrow."""

    directory = tmp_path / "borrowed-base"
    directory.mkdir()
    return directory


def build(base: Path, **overrides) -> materialize.MaterializedTree:
    kwargs = {
        "commit": COMMIT,
        "inventory": INVENTORY,
        "read_blob": reader(),
        "base": base,
    }
    kwargs.update(overrides)
    return materialize._materialize_bound(**kwargs)


def discard(tree) -> None:
    """Release a tree a test built, through the module's own cleanup."""

    materialize._cleanup_bound(tree)


# --- materialization --------------------------------------------------------


def test_materializes_exactly_the_inventory(base: Path) -> None:
    tree = build(base)
    try:
        assert set(tree.files) == set(INVENTORY)
        assert tree.commit == COMMIT
        present = {
            path.relative_to(tree.root).as_posix()
            for path in materialize._files_under(tree.root)
        }
        assert present == set(INVENTORY)
        materialize.verify(tree)
    finally:
        discard(tree)


def test_the_bytes_are_not_readable_while_the_tree_is_held(base: Path) -> None:
    """The share mask, observed.

    This is why `verify` reads through the creating handle rather than through
    the path — not why it stopped reading. An interim revision drew the second
    conclusion and lost the byte check for two revisions.

    A control file in the same directory opens without complaint, so the
    refusal belongs to the held handle rather than to the directory.
    """

    tree = build(base)
    try:
        control = base / "control.bin"
        control.write_bytes(b"readable")
        for relative in INVENTORY:
            with pytest.raises(PermissionError):
                (tree.root / relative).read_bytes()
        assert control.read_bytes() == b"readable"
        control.unlink()
    finally:
        discard(tree)


def test_materialized_files_are_read_only(base: Path) -> None:
    tree = build(base)
    try:
        for relative in INVENTORY:
            mode = os.lstat(tree.root / relative).st_mode
            assert not mode & stat.S_IWRITE
    finally:
        discard(tree)


def test_root_identity_comes_from_the_held_anchor(base: Path) -> None:
    """Identity is the boundary's, not an `lstat` on a path.

    A path-derived identity answers about whatever currently occupies the name;
    this one answers about the object the handle is holding.
    """

    tree = build(base)
    try:
        assert len(tree.root_identity) == 64
        assert str(tree.root) not in tree.root_identity
        root_anchor = dict(tree.created)[""]
        assert root_anchor.identity == tree.root_identity
    finally:
        discard(tree)


def test_directories_we_created_are_recorded(base: Path) -> None:
    tree = build(base)
    try:
        assert set(tree.directories) == {"a", "a/b"}
    finally:
        discard(tree)


def test_every_created_object_is_held(base: Path) -> None:
    """Nothing is created and then let go: cleanup needs the handle it made."""

    tree = build(base)
    try:
        assert {relative for relative, _ in tree.leaves} == set(INVENTORY)
        assert {relative for relative, _ in tree.created} == {"", "a", "a/b"}
        assert all(not held.closed for _relative, held in tree.leaves)
        assert all(not held.closed for _relative, held in tree.created)
    finally:
        discard(tree)


def test_base_is_required(base: Path) -> None:
    with pytest.raises(TypeError):
        materialize._materialize_bound(
            commit=COMMIT, inventory=INVENTORY, read_blob=reader()
        )


def test_a_base_that_does_not_exist_is_refused_not_created(tmp_path: Path) -> None:
    """The owner ruling, as a test: the module never creates its base."""

    absent = tmp_path / "no-such-base"
    before = sorted(tmp_path.iterdir())
    with pytest.raises(materialize.MaterializationError) as caught:
        build(absent)
    assert caught.value.code == "BASE_NOT_FOUND"
    assert sorted(tmp_path.iterdir()) == before
    assert not absent.exists()


def test_the_base_survives_a_complete_cycle(base: Path) -> None:
    before = base.stat().st_ino
    tree = build(base)
    discard(tree)
    assert base.is_dir()
    assert base.stat().st_ino == before
    assert sorted(base.iterdir()) == []


def test_root_replacement_is_detected(base: Path) -> None:
    """The identity check, reached deliberately.

    Cleanup spends the authority, so the record has to be re-minted for
    `verify` to get past `_record_of` and reach the check this test is named
    for. That the setup is this awkward is itself informative: while the tree
    is held nothing can replace the root.
    """

    tree = build(base)
    discard(tree)
    authority = tree._authority
    tree = materialize.MaterializedTree(
        materialize._Authority(
            materialize._MINT,
            authority.root,
            authority.root_identity,
            authority.commit,
            authority.files,
            authority.directories,
            authority.chain,
            authority.created,
            authority.leaves,
        )
    )
    tree.root.mkdir(parents=True)
    for relative, payload in BLOBS.items():
        target = tree.root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
    with pytest.raises(materialize.MaterializationError) as caught:
        materialize.verify(tree)
    assert caught.value.code == "ROOT_IDENTITY_CHANGED"


# --- containment ------------------------------------------------------------


@pytest.mark.parametrize(
    "relative",
    ["../escape.py", "/absolute.py", "a/../../escape.py", "C:/x.py", "a\\b.py", ""],
)
def test_paths_that_could_escape_fail_closed(base: Path, relative: str) -> None:
    payload = b"x\n"
    inventory = {relative: hashlib.sha256(payload).hexdigest()}
    before = sorted(base.iterdir())
    with pytest.raises(materialize.MaterializationError) as caught:
        materialize._materialize_bound(
            commit=COMMIT,
            inventory=inventory,
            read_blob=lambda c, p: payload,
            base=base,
        )
    assert caught.value.code in {"PATH_ESCAPES_ROOT", "PATH_INVALID"}
    assert sorted(base.iterdir()) == before


def test_reparse_point_inside_the_tree_fails_closed(base: Path) -> None:
    """`_files_under` refuses to descend through one, so `verify` refuses."""

    tree = build(base)
    try:
        planted = tree.root / "a" / "link"
        # A junction, not a symlink: `mklink /J` needs no privilege, so this
        # test runs on an ordinary account instead of skipping. It is also the
        # shape the design actually worries about — `S_ISLNK` is false for a
        # junction and only the attribute word gives it away.
        made = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(planted), str(base)],
            capture_output=True,
        )
        if made.returncode != 0:
            pytest.skip("this account cannot create a junction")
        with pytest.raises(materialize.MaterializationError) as caught:
            materialize.verify(tree)
        assert caught.value.code == "PATH_IS_REPARSE_POINT"
        planted.rmdir()  # detaches the junction; the target is untouched
        assert base.is_dir()
    finally:
        discard(tree)


# --- the injected reader ----------------------------------------------------


def test_untrusted_code_runs_before_anything_exists_on_disk(base: Path) -> None:
    """Phase one, asserted from inside the reader itself."""

    seen: list[list[str]] = []

    def watching(commit: str, path: str) -> bytes:
        seen.append(sorted(item.name for item in base.iterdir()))
        return BLOBS[path]

    tree = build(base, read_blob=watching)
    try:
        assert seen and all(listing == [] for listing in seen)
    finally:
        discard(tree)


def test_a_reader_that_plants_the_root_fails_closed(base: Path) -> None:
    """The stale-root check reports residue; it never removes it."""

    name = materialize._root_name(COMMIT, INVENTORY)

    def planting(commit: str, path: str) -> bytes:
        (base / name).mkdir(exist_ok=True)
        return BLOBS[path]

    with pytest.raises(materialize.MaterializationError) as caught:
        build(base, read_blob=planting)
    assert caught.value.code == "STALE_ROOT_LOCAL_RECOVERY_REQUIRED"
    assert (base / name).is_dir()  # reported, not deleted
    (base / name).rmdir()


def test_blob_not_matching_its_digest_fails_closed(base: Path) -> None:
    wrong = dict(BLOBS)
    wrong["three.md"] = b"# tampered\n"
    with pytest.raises(materialize.MaterializationError) as caught:
        build(base, read_blob=reader(wrong))
    assert caught.value.code == "BLOB_DIGEST_MISMATCH"
    assert sorted(base.iterdir()) == []


def test_non_bytes_blob_fails_closed(base: Path) -> None:
    with pytest.raises(materialize.MaterializationError) as caught:
        build(base, read_blob=lambda c, p: "not bytes")
    assert caught.value.code == "BLOB_NOT_BYTES"
    assert sorted(base.iterdir()) == []


def test_an_occupied_path_inside_the_root_fails_closed(base: Path) -> None:
    """`FILE_CREATE` refuses an occupied name rather than opening it.

    The stale-root check covers the root itself, so the occupied name has to be
    planted deeper — by a reader that runs before the tree is built.
    """

    name = materialize._root_name(COMMIT, INVENTORY)
    planted = base / name / "a"

    def planting(commit: str, path: str) -> bytes:
        if not planted.exists():
            planted.parent.mkdir(exist_ok=True)
            planted.write_bytes(b"in the way")
        return BLOBS[path]

    with pytest.raises(materialize.MaterializationError) as caught:
        build(base, read_blob=planting)
    assert caught.value.code == "STALE_ROOT_LOCAL_RECOVERY_REQUIRED"
    planted.unlink()
    planted.parent.rmdir()


# --- verification -----------------------------------------------------------


def test_extra_file_in_the_tree_fails_closed(base: Path) -> None:
    tree = build(base)
    try:
        extra = tree.root / "a" / "extra.py"
        extra.write_bytes(b"x\n")
        with pytest.raises(materialize.MaterializationError) as caught:
            materialize.verify(tree)
        assert caught.value.code == "MATERIALIZED_SET_MISMATCH"
        extra.unlink()
    finally:
        discard(tree)


def test_missing_file_fails_closed(base: Path) -> None:
    """A recorded file that is no longer on disk.

    The enumeration is what notices: the observed set no longer equals the
    record. Removing it takes deleting through the boundary, since the handle
    holds the name otherwise.
    """

    tree = build(base)
    try:
        label, leaf = tree.leaves[0]
        boundary.remove(boundary.load_bindings(), leaf)
        leaf.close()
        with pytest.raises(materialize.MaterializationError) as caught:
            materialize.verify(tree)
        assert caught.value.code == "MATERIALIZED_SET_MISMATCH"
    finally:
        try:
            discard(tree)
        except materialize.MaterializationError:
            pass


def test_verify_validates_the_record_before_reading_anything(
    base: Path, monkeypatch
) -> None:
    """A spent or forged authority is refused before a byte is fetched.

    Reading first and checking afterwards would mean a record that had no right
    to name these objects had already been used to reach them.
    """

    reads: list = []
    real_read = boundary.read_all
    monkeypatch.setattr(
        boundary,
        "read_all",
        lambda bindings, leaf: reads.append(leaf) or real_read(bindings, leaf),
    )

    tree = build(base)
    discard(tree)  # consumes the authority
    reads.clear()
    with pytest.raises(materialize.MaterializationError) as caught:
        materialize.verify(tree)
    assert caught.value.code == "RECORD_INVALID"
    assert reads == []
    monkeypatch.undo()


def test_the_path_based_read_back_is_gone(base: Path) -> None:
    """`_contained` retired with the read it guarded, and stays retired.

    An earlier report claimed a guard for this that existed only in a patch
    script, not in the repository. This is the guard.
    """

    source = Path(materialize.__file__).read_text(encoding="utf-8")
    assert "_contained" not in source
    assert "read_bytes()" not in source
    assert "boundary.read_all" in source


def test_verify_reads_every_file_back_through_its_own_handle(
    base: Path, monkeypatch
) -> None:
    """Every recorded file is read, and read through the leaf that created it.

    Counting the calls is not enough on its own — a `verify` that read one file
    three times would count the same. The leaves seen are compared against the
    leaves recorded.
    """

    seen: list = []
    real_read = boundary.read_all

    def watching(bindings, leaf):
        seen.append(leaf)
        return real_read(bindings, leaf)

    monkeypatch.setattr(boundary, "read_all", watching)
    tree = build(base)
    try:
        seen.clear()
        materialize.verify(tree)
        assert {id(leaf) for leaf in seen} == {
            id(leaf) for _label, leaf in tree.leaves
        }
        assert len(seen) == len(tree.leaves)
    finally:
        monkeypatch.undo()
        discard(tree)


def test_verify_rejects_bytes_that_do_not_match_the_record(
    base: Path, monkeypatch
) -> None:
    """The check the interim revision removed, and what it costs to lose.

    Reaching this state needs an injected read, because the share mask and the
    call census together stop a real materialized file changing underneath us.
    That is why the read is evidence rather than redundant: without it, a file
    whose bytes differed would pass every remaining check.
    """

    tree = build(base)
    try:
        monkeypatch.setattr(
            boundary, "read_all", lambda _bindings, _leaf: b"different bytes"
        )
        with pytest.raises(materialize.MaterializationError) as caught:
            materialize.verify(tree)
        assert caught.value.code == "MATERIALIZED_BYTES_CHANGED"
        monkeypatch.undo()
    finally:
        discard(tree)


def test_verify_accepts_only_the_exact_bytes(base: Path, monkeypatch) -> None:
    """One byte is enough. A digest that tolerated a near miss would not be one."""

    tree = build(base)
    try:
        real_read = boundary.read_all

        def one_byte_off(bindings, leaf):
            payload = bytearray(real_read(bindings, leaf))
            payload[0] ^= 0x01
            return bytes(payload)

        monkeypatch.setattr(boundary, "read_all", one_byte_off)
        with pytest.raises(materialize.MaterializationError) as caught:
            materialize.verify(tree)
        assert caught.value.code == "MATERIALIZED_BYTES_CHANGED"
        monkeypatch.undo()
    finally:
        discard(tree)


@pytest.mark.parametrize(
    "code", ["MATERIALIZE_READ_FAILED", "MATERIALIZED_BYTES_CHANGED"]
)
def test_a_read_failure_is_carried_across_as_its_own_code(
    base: Path, monkeypatch, code
) -> None:
    """A boundary code keeps its name; it is not flattened into one refusal.

    "the read call failed" and "the file is not what was written" send a caller
    to different places.
    """

    tree = build(base)
    try:
        def failing(_bindings, _leaf):
            raise boundary.NativeError(code)

        monkeypatch.setattr(boundary, "read_all", failing)
        with pytest.raises(materialize.MaterializationError) as caught:
            materialize.verify(tree)
        assert caught.value.code == code
        monkeypatch.undo()
    finally:
        discard(tree)


def test_the_module_does_not_claim_verification_is_entirely_handle_bound(
    base: Path,
) -> None:
    """The limit the reviewer asked to be kept visible, asserted structurally.

    `verify` still enumerates by path. A later revision that quietly deleted
    this caveat while leaving the walk in place would be overclaiming again,
    and this is what would stop it.
    """

    source = Path(materialize.__file__).read_text(encoding="utf-8")
    assert "handle-bound directory enumeration" in source
    assert "not a claim this module may make" in source
    # And the walk is still there, so the caveat is not describing a past state.
    assert "_files_under(tree.root)" in source


# --- cleanup ----------------------------------------------------------------


def test_cleanup_removes_the_root(base: Path) -> None:
    tree = build(base)
    discard(tree)
    assert not tree.root.exists()
    assert sorted(base.iterdir()) == []


def test_cleanup_closes_every_handle_it_held(base: Path) -> None:
    tree = build(base)
    discard(tree)
    assert all(held.closed for _relative, held in tree.leaves)
    assert all(held.closed for _relative, held in tree.created)
    assert all(anchor.closed for anchor in tree.chain.anchors)


def test_the_record_has_no_separately_replaceable_fields(base: Path) -> None:
    """Forgery is refused by construction rather than detected afterwards.

    The tree has exactly one field — its authority — and every public attribute
    is read from it. There is nothing left to recombine, so `dataclasses.replace`
    cannot produce a record that keeps one tree's paths beside another tree's
    handles: the paths and the handles are the same object's fields.
    """

    tree = build(base)
    try:
        for field in ("root", "files", "directories", "chain", "created", "leaves"):
            with pytest.raises(TypeError):
                dataclasses.replace(tree, **{field: None})
        with pytest.raises(dataclasses.FrozenInstanceError):
            tree._authority = None
        with pytest.raises(TypeError):
            tree.files["a/one.py"] = "0" * 64
    finally:
        discard(tree)


def test_an_authority_cannot_be_built_without_the_mint_token(base: Path) -> None:
    """The only way to obtain one is to materialize a tree.

    This does not defend against a caller reaching into module internals —
    nothing here does — but an authority cannot be assembled by editing a
    record, which is the case it guards.
    """

    tree = build(base)
    try:
        authority = tree._authority
        with pytest.raises(materialize.MaterializationError) as caught:
            materialize._Authority(
                object(),
                authority.root,
                authority.root_identity,
                authority.commit,
                authority.files,
                authority.directories,
                authority.chain,
                authority.created,
                authority.leaves,
            )
        assert caught.value.code == "RECORD_INVALID"
    finally:
        discard(tree)


def test_swapping_the_authority_yields_that_tree_not_a_mixture(
    tmp_path: Path,
) -> None:
    """The substitution that used to delete the wrong tree.

    Two trees from the same commit and inventory under different bases produce
    records with identical labels, identical digests and correctly-typed
    handles. Mixing them is now impossible: a record carrying the second tree's
    authority *is* the second tree, root and files included, so there is no
    combination in which the paths describe one tree and the deletion reaches
    another.
    """

    first = tmp_path / "base-one"
    second = tmp_path / "base-two"
    first.mkdir()
    second.mkdir()

    one = build(first)
    two = build(second)
    try:
        swapped = dataclasses.replace(one, _authority=two._authority)
        assert swapped.root == two.root  # wholly the second tree
        assert swapped.root != one.root
        assert swapped.chain is two.chain
        assert one.root.is_dir() and two.root.is_dir()
    finally:
        discard(one)
        discard(two)


def test_a_forged_file_record_deletes_nothing(base: Path) -> None:
    """A hand-built authority still has to be internally consistent."""

    tree = build(base)
    try:
        authority = tree._authority
        aimed = materialize.MaterializedTree(
            materialize._Authority(
                materialize._MINT,
                authority.root,
                authority.root_identity,
                authority.commit,
                {"../outside.py": "0" * 64},
                authority.directories,
                authority.chain,
                authority.created,
                authority.leaves,
            )
        )
        with pytest.raises(materialize.MaterializationError) as caught:
            materialize._cleanup_bound(aimed)
        assert caught.value.code == "RECORD_INVALID"
        assert tree.root.is_dir()
    finally:
        discard(tree)


def test_a_directory_record_beyond_what_the_files_imply_is_refused(
    base: Path,
) -> None:
    tree = build(base)
    try:
        authority = tree._authority
        aimed = materialize.MaterializedTree(
            materialize._Authority(
                materialize._MINT,
                authority.root,
                authority.root_identity,
                authority.commit,
                authority.files,
                authority.directories + ("extra",),
                authority.chain,
                authority.created,
                authority.leaves,
            )
        )
        with pytest.raises(materialize.MaterializationError) as caught:
            materialize._cleanup_bound(aimed)
        assert caught.value.code == "RECORD_INVALID"
        assert tree.root.is_dir()
    finally:
        discard(tree)


def test_a_record_whose_root_identity_disagrees_with_its_anchor_is_refused(
    base: Path,
) -> None:
    tree = build(base)
    try:
        authority = tree._authority
        aimed = materialize.MaterializedTree(
            materialize._Authority(
                materialize._MINT,
                authority.root,
                "f" * 64,
                authority.commit,
                authority.files,
                authority.directories,
                authority.chain,
                authority.created,
                authority.leaves,
            )
        )
        with pytest.raises(materialize.MaterializationError) as caught:
            materialize._cleanup_bound(aimed)
        assert caught.value.code == "RECORD_INVALID"
    finally:
        discard(tree)


def test_an_authority_is_spent_once(base: Path) -> None:
    tree = build(base)
    discard(tree)
    with pytest.raises(materialize.MaterializationError) as caught:
        materialize._cleanup_bound(tree)
    assert caught.value.code == "RECORD_INVALID"


def test_a_tree_dropped_without_cleanup_releases_its_handles(base: Path) -> None:
    """The lifetime property the global registry destroyed.

    The registry held the handles by strong reference, so a caller who lost the
    tree without cleaning up left every handle open with no way to reach them
    again. With the authority owned solely by the tree, dropping the tree drops
    the handles, and their finalizers run.
    """

    import gc

    closed: list[int] = []
    real_close = boundary._close_handle

    def watching(bindings, handle):
        closed.append(handle)
        return real_close(bindings, handle)

    boundary._close_handle = watching
    try:
        expected = {"count": 0}

        def leak():
            tree = build(base)
            # Counted, not retained: holding the handle objects here would keep
            # them alive and the test would disprove itself.
            expected["count"] = (
                len(tree.leaves) + len(tree.created) + len(tree.chain.anchors)
            )

        leak()
        gc.collect()
        assert len(closed) == expected["count"]
    finally:
        boundary._close_handle = real_close


def test_a_replaced_root_deletes_nothing(base: Path) -> None:
    """Cleanup refuses when the held root is no longer the object it recorded.

    Reaching this state takes deliberate setup, and that is itself the finding:
    while the tree is held, nothing can replace the root, so the identity check
    is a backstop rather than a routine outcome. The authority is re-minted from
    the spent one because cleanup consumes it, and without that the record
    would be refused for the earlier reason and this check would never run.
    """

    tree = build(base)
    discard(tree)
    authority = tree._authority
    revived = materialize.MaterializedTree(
        materialize._Authority(
            materialize._MINT,
            authority.root,
            authority.root_identity,
            authority.commit,
            authority.files,
            authority.directories,
            authority.chain,
            authority.created,
            authority.leaves,
        )
    )
    tree.root.mkdir()
    try:
        with pytest.raises(materialize.MaterializationError) as caught:
            materialize._cleanup_bound(revived)
        assert caught.value.code == "ROOT_IDENTITY_CHANGED"
        assert tree.root.is_dir()  # not ours any more, so not ours to remove
    finally:
        tree.root.rmdir()


# --- the stale-root policy --------------------------------------------------


def test_stale_root_is_reported_not_deleted(base: Path) -> None:
    tree = build(base)
    discard(tree)
    residue = base / materialize._root_name(COMMIT, INVENTORY)
    residue.mkdir()
    (residue / "left-behind.py").write_bytes(b"x\n")

    with pytest.raises(materialize.MaterializationError) as caught:
        build(base)
    assert caught.value.code == "STALE_ROOT_LOCAL_RECOVERY_REQUIRED"
    assert (residue / "left-behind.py").read_bytes() == b"x\n"
    (residue / "left-behind.py").unlink()
    residue.rmdir()


def test_root_name_is_deterministic_so_residue_is_findable() -> None:
    first = materialize._root_name(COMMIT, INVENTORY)
    second = materialize._root_name(COMMIT, dict(reversed(list(INVENTORY.items()))))
    assert first == second
    assert first.startswith(materialize.ROOT_PREFIX)


# --- the inventory snapshot -------------------------------------------------


def test_a_reader_that_mutates_the_inventory_changes_nothing(base: Path) -> None:
    """The caller's object is read once, before any untrusted code runs.

    Without the snapshot, the paths, the digests, the root name and the final
    verification could each have seen a different inventory.
    """

    live = dict(INVENTORY)

    def mutating(commit: str, path: str) -> bytes:
        live["injected.py"] = "0" * 64
        live.pop("three.md", None)
        return BLOBS[path]

    tree = materialize._materialize_bound(
        commit=COMMIT, inventory=live, read_blob=mutating, base=base
    )
    try:
        assert set(tree.files) == set(INVENTORY)
        assert "injected.py" not in tree.files
        materialize.verify(tree)
    finally:
        discard(tree)


def test_the_inventory_is_read_exactly_once(base: Path) -> None:
    """A custom Mapping runs Python on every lookup; it gets one chance.

    Anything later would be a callback inside the phase that must have none.
    """

    from collections.abc import Mapping as AbstractMapping

    class Counting(AbstractMapping):
        def __init__(self, source):
            self.source = dict(source)
            self.reads = 0

        def __getitem__(self, key):
            self.reads += 1
            return self.source[key]

        def __iter__(self):
            self.reads += 1
            return iter(self.source)

        def __len__(self):
            return len(self.source)

    counting = Counting(INVENTORY)
    tree = materialize._materialize_bound(
        commit=COMMIT, inventory=counting, read_blob=reader(), base=base
    )
    try:
        before = counting.reads
        materialize.verify(tree)
        discard(tree)
        assert counting.reads == before  # nothing touched it after the snapshot
    finally:
        pass


@pytest.mark.parametrize(
    "bad",
    [
        {"a.py": "not a digest"},
        {"a.py": "0" * 63},
        {"a.py": "G" * 64},
        {"a.py": 12345},
        {12345: "0" * 64},
        {},
    ],
)
def test_an_inventory_that_is_not_a_digest_map_is_refused(base: Path, bad) -> None:
    before = sorted(base.iterdir())
    with pytest.raises(materialize.MaterializationError) as caught:
        materialize._materialize_bound(
            commit=COMMIT, inventory=bad, read_blob=reader(), base=base
        )
    assert caught.value.code == "INVENTORY_INVALID"
    assert sorted(base.iterdir()) == before


# --- verification compares digests, not just names --------------------------


def test_verify_takes_no_caller_inventory(base: Path) -> None:
    """The parameter is gone, and its absence is the point.

    Snapshotting a caller-supplied `Mapping` inside `verify` meant a custom one
    could run arbitrary Python while every handle in the tree was open — a
    callback in the phase that is supposed to have none. Two earlier tests
    exercised the cross-check that parameter enabled; the check they stood in
    for is now done directly, by reading the bytes.
    """

    import inspect

    signature = inspect.signature(materialize.verify)
    assert list(signature.parameters) == ["tree", "bindings"]
    assert (
        signature.parameters["bindings"].kind
        is inspect.Parameter.KEYWORD_ONLY
    ), "a positional bindings would silently absorb a stale inventory argument"

    tree = build(base)
    try:
        with pytest.raises(TypeError):
            # The call a stale caller would make. It must fail here, at the
            # signature, not somewhere inside the boundary.
            materialize.verify(tree, INVENTORY)
    finally:
        discard(tree)


def test_verify_reads_no_caller_mapping_while_handles_are_held(
    base: Path,
) -> None:
    """A hostile Mapping gets no execution window during verification."""

    from collections.abc import Mapping as AbstractMapping

    class Exploding(AbstractMapping):
        def __getitem__(self, key):
            pytest.fail("verify consulted a caller-supplied mapping")

        def __iter__(self):
            pytest.fail("verify consulted a caller-supplied mapping")

        def __len__(self):
            return 0

    tree = build(base)
    try:
        # Not passable at all now; the tree's own inventory is what is read.
        with pytest.raises(TypeError):
            materialize.verify(tree, Exploding())
        materialize.verify(tree)
    finally:
        discard(tree)


# --- cleanup is a per-object transaction ------------------------------------


def test_every_removal_is_confirmed_absent_before_the_parent_is_touched(
    base: Path, monkeypatch
) -> None:
    """The ordering, observed rather than assumed.

    Batching the confirmations would only discover a child's failure after its
    parent had already been attempted.
    """

    order: list[str] = []
    real_remove = boundary.remove
    real_confirm = boundary.confirm_absent

    def watched_remove(bindings, held):
        order.append("remove")
        return real_remove(bindings, held)

    def watched_confirm(bindings, parent, name):
        order.append(f"confirm:{name}")
        return real_confirm(bindings, parent, name)

    monkeypatch.setattr(boundary, "remove", watched_remove)
    monkeypatch.setattr(boundary, "confirm_absent", watched_confirm)

    tree = build(base)
    order.clear()
    discard(tree)
    monkeypatch.undo()

    # Every remove is followed by its own confirmation, never two removes in a
    # row, and the root's confirmation is last.
    assert order[0] == "remove"
    for first, second in zip(order, order[1:]):
        assert not (first == "remove" and second == "remove")
    assert order[-1].startswith("confirm:") and materialize.ROOT_PREFIX in order[-1]


def test_deletion_stops_at_a_failure_while_release_continues(
    base: Path, monkeypatch
) -> None:
    """Two sequences, opposite rules.

    A parent must not be attempted while its child may still exist; a handle
    the deletion never reached must still be closed, or it leaks.
    """

    real_confirm = boundary.confirm_absent
    refused = {"name": None}

    def refusing(bindings, parent, name):
        if name == refused["name"]:
            raise boundary.NativeError("CLEANUP_INCOMPLETE")
        return real_confirm(bindings, parent, name)

    tree = build(base)
    refused["name"] = "two.py"  # the deepest leaf
    monkeypatch.setattr(boundary, "confirm_absent", refusing)

    with pytest.raises(materialize.MaterializationError) as caught:
        materialize._cleanup_bound(tree)
    assert caught.value.code == "CLEANUP_INCOMPLETE"
    assert any("CLEANUP_INCOMPLETE" in note for note in caught.value.__notes__)

    monkeypatch.undo()
    # Deletion stopped, so the root survives — but nothing is still held.
    assert tree.root.is_dir()
    assert all(held.closed for _label, held in tree.leaves)
    assert all(held.closed for _label, held in tree.created)
    assert all(anchor.closed for anchor in tree.chain.anchors)


def test_a_cleanup_failure_while_unwinding_never_replaces_the_original(
    base: Path, monkeypatch
) -> None:
    """The reason for the unwind is what the caller needs to see.

    A create fails after earlier objects already exist, and the unwind's own
    confirmations then fail too. The create failure must be what propagates,
    with the cleanup trouble attached to it rather than raised over it.
    """

    real_create_file = boundary.create_file
    real_confirm = boundary.confirm_absent
    created_count = {"n": 0}
    building = {"done": False}

    def failing_create(bindings, parent, name, payload):
        created_count["n"] += 1
        if created_count["n"] == 2:
            raise boundary.NativeError("MATERIALIZE_WRITE_FAILED")
        return real_create_file(bindings, parent, name, payload)

    def confirm(bindings, parent, name):
        if building["done"]:
            raise boundary.NativeError("CLEANUP_INCOMPLETE")
        return real_confirm(bindings, parent, name)

    def watching(commit: str, path: str) -> bytes:
        return BLOBS[path]

    monkeypatch.setattr(boundary, "create_file", failing_create)
    monkeypatch.setattr(boundary, "confirm_absent", confirm)
    # The stale-root probe runs before any create, so it must still work.
    building["done"] = False

    original_create = failing_create

    def arming_create(bindings, parent, name, payload):
        building["done"] = True
        return original_create(bindings, parent, name, payload)

    monkeypatch.setattr(boundary, "create_file", arming_create)

    with pytest.raises(materialize.MaterializationError) as caught:
        materialize._materialize_bound(
            commit=COMMIT, inventory=INVENTORY, read_blob=watching, base=base
        )
    assert caught.value.code == "MATERIALIZE_WRITE_FAILED"
    assert any(
        "cleanup after this error also failed" in note
        for note in caught.value.__notes__
    )
    monkeypatch.undo()


# --- what this module does not do -------------------------------------------


def test_no_process_is_started(base: Path, monkeypatch) -> None:
    def forbidden(*args, **kwargs):
        pytest.fail("materialization started a process")

    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(os, "system", forbidden)
    tree = build(base)
    discard(tree)


def test_module_imports_no_subprocess_and_no_historical_module() -> None:
    """Structural: executing what is materialized is M3's job, not this one's."""

    source = Path(materialize.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    assert "subprocess" not in imported
    assert imported & {"gate3_native_boundary"}
    assert not {name for name in imported if name.startswith("gate3_route_v2")}


def test_no_path_based_creation_or_removal_survives() -> None:
    """The path-based primitives are gone, not kept as a fallback.

    Two ways to remove an object, one of which resolves by name, is what this
    boundary exists to end — so their absence is asserted rather than assumed.
    """

    source = Path(materialize.__file__).read_text(encoding="utf-8")
    for banned in (
        "os.makedirs",
        "os.mkdir",
        "os.unlink",
        "os.rmdir",
        "os.open",
        "os.chmod",
        "lexists",
        "_create_exclusively",
        "_drop_name",
    ):
        assert banned not in source, banned


def test_creation_and_removal_go_through_the_boundary() -> None:
    """And through it alone: no direct native call is made from here."""

    source = Path(materialize.__file__).read_text(encoding="utf-8")
    for required in (
        "boundary.open_chain",
        "boundary.create_directory",
        "boundary.create_file",
        "boundary.remove",
        "boundary.confirm_absent",
        "boundary.revalidate",
        "boundary.close_chain",
    ):
        assert required in source, required
    assert "ctypes" not in source


# --- availability -----------------------------------------------------------


def test_public_entry_points_refuse_until_the_backend_is_admitted(
    base: Path,
) -> None:
    with pytest.raises(materialize.MaterializationError) as caught:
        materialize.materialize(
            commit=COMMIT, inventory=INVENTORY, read_blob=reader(), base=base
        )
    assert caught.value.code == "HANDLE_BOUNDARY_UNAVAILABLE"

    tree = build(base)
    try:
        with pytest.raises(materialize.MaterializationError) as caught:
            materialize.cleanup(tree)
        assert caught.value.code == "HANDLE_BOUNDARY_UNAVAILABLE"
    finally:
        discard(tree)


def test_availability_is_the_boundarys_answer_not_this_modules(monkeypatch) -> None:
    """Forwarded, not decided here — and the forwarding is what is asserted."""

    assert materialize.handle_boundary_available() is False
    monkeypatch.setattr(boundary, "handle_boundary_available", lambda: True)
    assert materialize.handle_boundary_available() is True


def test_the_refusal_precedes_any_injected_call(base: Path) -> None:
    """Nothing untrusted runs before the refusal, so refusing costs nothing."""

    def forbidden(commit: str, path: str) -> bytes:
        pytest.fail("the injected reader ran before the refusal")

    with pytest.raises(materialize.MaterializationError):
        materialize.materialize(
            commit=COMMIT, inventory=INVENTORY, read_blob=forbidden, base=base
        )
    assert sorted(base.iterdir()) == []


def test_the_bound_path_is_reachable_only_from_tests() -> None:
    source = Path(materialize.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    callers: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        for inner in ast.walk(node):
            if isinstance(inner, ast.Call) and isinstance(inner.func, ast.Name):
                if inner.func.id in {"_materialize_bound", "_cleanup_bound"}:
                    callers.add(node.name)
    assert callers == {"materialize", "cleanup"}


def test_m2_is_not_wired_into_the_production_verifier() -> None:
    here = Path(materialize.__file__).resolve().parent
    candidate = here / "gate3_route_v2_ab_candidate.py"
    assert "gate3_historical_materialize" not in candidate.read_text(encoding="utf-8")
    assert materialize.ACTIVE is False


# --- errors -----------------------------------------------------------------


def test_errors_carry_no_path_or_content(base: Path) -> None:
    """A closed code, and nothing else. Not a rule — a structural property."""

    with pytest.raises(materialize.MaterializationError) as caught:
        build(base, read_blob=lambda c, p: b"tampered")
    message = str(caught.value)
    assert message == caught.value.code
    assert str(base) not in message
    assert "tampered" not in message


# --- M3-b-2A: materialized-root transport authority ------------------------


def test_transport_root_returns_the_authority_value_without_resolving(
    base: Path, monkeypatch
) -> None:
    tree = build(base)
    calls = []
    real_revalidate = boundary.revalidate

    def watching(bindings, anchor):
        calls.append(anchor)
        return real_revalidate(bindings, anchor)

    def forbidden(*_args, **_kwargs):
        raise AssertionError("ambient path source reached")

    monkeypatch.setattr(boundary, "revalidate", watching)
    monkeypatch.setattr(Path, "resolve", forbidden)
    monkeypatch.setattr(os, "getcwd", forbidden)
    monkeypatch.setattr(os, "getenv", forbidden)
    try:
        assert materialize.transport_root(tree) == os.fspath(tree.root)
        assert calls == [dict(tree.created)[""]]
    finally:
        discard(tree)


def test_transport_bundle_returns_every_verified_held_payload(base: Path) -> None:
    tree = build(base)
    try:
        root, commit, inventory, payloads = materialize.transport_bundle(tree)
        assert root == os.fspath(tree.root)
        assert commit == tree.commit
        assert inventory is tree.files
        assert payloads == BLOBS
    finally:
        discard(tree)


def test_transport_root_refuses_a_raw_string_before_revalidation(monkeypatch) -> None:
    def forbidden(*_args, **_kwargs):
        raise AssertionError("native revalidation reached for a raw string")

    monkeypatch.setattr(boundary, "revalidate", forbidden)
    with pytest.raises(materialize.MaterializationError, match="^RECORD_INVALID$"):
        materialize.transport_root("C:\\not-authority", bindings=object())


def test_transport_root_refuses_a_consumed_tree(base: Path) -> None:
    tree = build(base)
    discard(tree)
    with pytest.raises(materialize.MaterializationError, match="^RECORD_INVALID$"):
        materialize.transport_root(tree, bindings=object())


def test_transport_root_refuses_a_forged_tree_before_revalidation(monkeypatch) -> None:
    def forbidden(*_args, **_kwargs):
        raise AssertionError("native revalidation reached for a forged tree")

    monkeypatch.setattr(boundary, "revalidate", forbidden)
    forged = materialize.MaterializedTree(object())
    with pytest.raises(materialize.MaterializationError, match="^RECORD_INVALID$"):
        materialize.transport_root(forged, bindings=object())


def test_transport_root_refuses_a_recombined_identity(base: Path) -> None:
    tree = build(base)
    authority = tree._authority
    original = authority.root_identity
    authority.root_identity = "0" * 32
    try:
        with pytest.raises(
            materialize.MaterializationError, match="^RECORD_INVALID$"
        ):
            materialize.transport_root(tree, bindings=object())
    finally:
        authority.root_identity = original
        discard(tree)


def test_transport_root_preserves_the_stale_anchor_code(
    base: Path, monkeypatch
) -> None:
    tree = build(base)
    real_revalidate = boundary.revalidate

    def stale(*_args, **_kwargs):
        raise boundary.NativeError("PATH_IDENTITY_CHANGED")

    monkeypatch.setattr(boundary, "revalidate", stale)
    try:
        with pytest.raises(
            materialize.MaterializationError, match="^ROOT_IDENTITY_CHANGED$"
        ):
            materialize.transport_root(tree)
    finally:
        monkeypatch.setattr(boundary, "revalidate", real_revalidate)
        discard(tree)
