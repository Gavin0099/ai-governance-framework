"""Read-only materialization of a pinned commit (M2).

Step 2 of the historical materialization design.  It writes the verified
inventory into a private temporary root, captures that root's **identity**
rather than only its path, and re-verifies before anyone may use it.

Not active.  Nothing here is wired into the production candidate verifier; the
production path switches at M4.

It starts no process and executes no historical code — blob bytes arrive
through an injected reader, so this module never shells out.  Executing what it
materializes is M3's job, not this one's.

Creation, writing, reading back, removal and the absence check are all
handle-bound: every one of them goes through `gate3_native_boundary`, relative
to a handle this module holds, so no component is ever re-resolved by name and a
concurrent process replacing an ancestor cannot redirect them.

One thing is **not** handle-bound and is named here rather than left to be
discovered: `verify` still enumerates the tree by path to compare the observed
file set against the record. That walk reads no bytes and refuses to descend
through a reparse point, but it is a path walk, and the adapter offers no
handle-bound directory enumeration to replace it with. "All verification is
handle-bound" is therefore not a claim this module may make.  The path-based versions
that preceded them are gone rather than kept as a fallback; two ways to remove
an object, one of which resolves by name, is the situation this boundary exists
to end.

`base` must already exist.  It is borrowed, pinned for the tree's lifetime, and
never created, deleted or marked — an object this module creates owes a
deletion and a borrowed one owes never being deleted, and nothing can hold both
obligations at once.

The public `materialize` and `cleanup` entry points still refuse.
`handle_boundary_available()` defers to the native boundary, which reports
False until an admission record and a capability probe exist; this module does
not decide that question and does not pretend to.  M3-b-2A's transport helpers
consume an already-live tree and do not move that availability boundary.
"""

from __future__ import annotations

import hashlib
import os
import stat
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from types import MappingProxyType
from typing import Callable, Mapping

import gate3_native_boundary as boundary


ACTIVE = False
"""M2 is not wired into the production verifier.  M4 switches that path."""

ROOT_PREFIX = "gate3-historical-"

BlobReader = Callable[[str, str], bytes]
"""(commit, repo-relative path) -> exact blob bytes.  Injected, never spawned."""


class MaterializationError(ValueError):
    """Closed error that never renders artifact content or absolute paths."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


_MINT = object()
"""Module-private construction token.

An authority record can only be built by code holding this, which is code in
this module.  It does not defend against a caller reaching into module
internals — nothing here does — but it does mean an authority cannot be
assembled by editing a record, which is the case this guards.
"""


class _Authority:
    """The single source of truth for one materialized tree.

    Every public attribute of `MaterializedTree` is derived from this object, so
    there is nothing to mix: a record cannot keep one tree's paths while
    carrying another tree's handles, because the paths and the handles are the
    same object's fields.  An earlier revision kept them as separate dataclass
    fields with a seal indexing a global registry, and that had two problems —
    the fields could be recombined, and the registry's strong references kept
    handles alive after the tree they belonged to was collected.

    `consumed` is set when cleanup finishes, so an authority is spent once.
    """

    __slots__ = (
        "root",
        "root_identity",
        "commit",
        "files",
        "directories",
        "chain",
        "created",
        "leaves",
        "consumed",
    )

    def __init__(
        self,
        token,
        root,
        root_identity,
        commit,
        files,
        directories,
        chain,
        created,
        leaves,
    ) -> None:
        if token is not _MINT:
            raise MaterializationError("RECORD_INVALID")
        self.root = root
        self.root_identity = root_identity
        self.commit = commit
        self.files = files
        self.directories = directories
        self.chain = chain
        self.created = created
        self.leaves = leaves
        self.consumed = False


@dataclass(frozen=True)
class MaterializedTree:
    """A materialized tree: one authority record, read through properties.

    `directories` records every directory this module created, so removal can be
    driven by what we made rather than by walking what is there now.

    The handles are carried here because every created object is removed
    through the handle that created it; reopening a name to delete it would be
    a second ownership path for one object, and the two would not stay in step.

    Nothing is stored twice.  The only field is the authority, and it holds the
    handles, so when a caller drops the tree without cleaning up, the authority
    and the handles become unreachable together and the handle finalizers run.
    """

    _authority: _Authority

    @property
    def root(self) -> Path:
        return self._authority.root

    @property
    def root_identity(self) -> str:
        return self._authority.root_identity

    @property
    def commit(self) -> str:
        return self._authority.commit

    @property
    def files(self) -> Mapping[str, str]:
        return self._authority.files

    @property
    def directories(self) -> tuple:
        return self._authority.directories

    @property
    def chain(self):
        return self._authority.chain

    @property
    def created(self) -> tuple:
        return self._authority.created

    @property
    def leaves(self) -> tuple:
        return self._authority.leaves


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _mint(*fields) -> "MaterializedTree":
    """Build the one authority record for a tree, and wrap it.

    Comparing shapes was not enough, and the gap was demonstrated rather than
    imagined: two trees built from the same commit and inventory under
    different bases produce records with identical labels, identical file
    digests and correctly-typed handles.  Swapping one bundle for the other
    passed every structural check, and cleanup then deleted the tree the record
    did not describe.

    Making the authority the only field is what closes it.  There is no longer
    a set of independently replaceable fields to recombine — swapping the
    authority swaps the whole record, which is simply a different tree rather
    than a forged mixture of two.
    """

    return MaterializedTree(_Authority(_MINT, *fields))


def _is_reparse(entry: os.stat_result) -> bool:
    """True for a symlink, a junction, or anything we cannot rule out as one.

    A junction is not a symlink: `S_ISLNK` is false for one and only the
    Windows attribute word gives it away.  That word can also be present but
    unset — `stat_result` reports `None` for a field the platform did not fill
    in — and "unknown" has to resolve to "refuse", not to "ordinary file".
    """

    if stat.S_ISLNK(entry.st_mode):
        return True
    if not hasattr(entry, "st_file_attributes"):
        # A platform without the concept at all; S_ISLNK was the whole answer.
        return False
    attributes = entry.st_file_attributes
    if type(attributes) is not int:
        return True
    return bool(attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT)


def _snapshot_inventory(inventory: Mapping[str, str]) -> Mapping[str, str]:
    """Read the caller's inventory once, into something nothing else can change.

    Every key and value is type-checked here rather than later, because a
    digest that is not a 64-character hex string cannot be compared against one
    and a non-string path cannot be validated.
    """

    if not isinstance(inventory, Mapping) or not inventory:
        raise MaterializationError("INVENTORY_INVALID")
    captured: dict[str, str] = {}
    for relative, digest in dict(inventory).items():
        if type(relative) is not str or type(digest) is not str:
            raise MaterializationError("INVENTORY_INVALID")
        if len(digest) != 64 or any(
            character not in "0123456789abcdef" for character in digest
        ):
            raise MaterializationError("INVENTORY_INVALID")
        captured[relative] = digest
    return MappingProxyType(captured)


def _root_name(commit: str, inventory: Mapping[str, str]) -> str:
    """Deterministic, so a root left by a crash is findable next time."""

    joined = "\n".join(f"{path}:{digest}" for path, digest in sorted(inventory.items()))
    return ROOT_PREFIX + _sha256(f"{commit}\n{joined}".encode("ascii"))[:32]


def _checked_relative(relative: str) -> PurePosixPath:
    """Reject anything that could escape the root before it is ever joined."""

    if type(relative) is not str or not relative:
        raise MaterializationError("PATH_INVALID")
    candidate = PurePosixPath(relative)
    if candidate.is_absolute() or candidate.drive or candidate.anchor:
        raise MaterializationError("PATH_ESCAPES_ROOT")
    if any(part in ("..", "") for part in candidate.parts):
        raise MaterializationError("PATH_ESCAPES_ROOT")
    if ":" in relative or "\\" in relative:
        raise MaterializationError("PATH_INVALID")
    return candidate


def _files_under(root: Path) -> list[Path]:
    """Every regular file under `root`, never descending through a reparse point.

    `Path.rglob` decides for itself what to follow, and that decision has moved
    between releases — junctions in particular were still walked as ordinary
    directories until 3.12.  Enumerating explicitly keeps "the walk never leaves
    the root" a property of this code rather than of the interpreter.
    """

    found: list[Path] = []

    def visit(directory: Path) -> None:
        for name in sorted(os.listdir(directory)):
            child = directory / name
            entry = os.lstat(child)
            if _is_reparse(entry):
                raise MaterializationError("PATH_IS_REPARSE_POINT")
            if stat.S_ISDIR(entry.st_mode):
                visit(child)
            elif stat.S_ISREG(entry.st_mode):
                found.append(child)
            else:
                raise MaterializationError("PATH_NOT_REGULAR_FILE")

    visit(root)
    return found


def _bindings_for(bindings):
    """The caller's bindings, or the module's own loader.

    Injectable because the tests need to observe the boundary, loaded here
    otherwise so an ordinary caller does not have to know the boundary exists.
    """

    return boundary.load_bindings() if bindings is None else bindings


def handle_boundary_available(bindings=None) -> bool:
    """Whether the handle-bound backend may be used.

    This module does not answer the question; it forwards it. The native
    boundary owns availability, and it reports False until an admission record
    and a capability probe both exist. A module that decided its own
    availability would be asserting a capability it cannot demonstrate.
    """

    return boundary.handle_boundary_available()


def _require_handle_boundary() -> None:
    if not handle_boundary_available():
        raise MaterializationError("HANDLE_BOUNDARY_UNAVAILABLE")


def _translate(error: boundary.NativeError) -> "MaterializationError":
    """Carry a boundary code across as this module's own closed code.

    Codes that mean the same thing keep their name. `BASE_NOT_FOUND` and
    `BASE_NOT_ADMISSIBLE` are new here and are kept distinct rather than
    flattened into one refusal, because a caller can fix a missing base and can
    do nothing about an unopenable one.
    """

    return MaterializationError(error.args[0])


def require_no_stale_root(bindings, base_anchor, commit, inventory) -> None:
    """Fail closed on a stale root instead of deleting it.

    A hard crash leaves a copy of public source behind.  Removing it as a side
    effect of the next verification would be a deletion nobody authorized, so
    the next run refuses and asks for local recovery.

    Handle-relative, and only `STATUS_OBJECT_NAME_NOT_FOUND` counts as absent:
    a delete-pending name, a sharing violation or an access denial all mean
    something is there or that we cannot tell, and neither is a reason to
    proceed.
    """

    name = _root_name(commit, inventory)
    try:
        boundary.confirm_absent(bindings, base_anchor, name)
    except boundary.NativeError:
        raise MaterializationError("STALE_ROOT_LOCAL_RECOVERY_REQUIRED") from None


def materialize(
    *,
    commit: str,
    inventory: Mapping[str, str],
    read_blob: BlobReader,
    base: Path,
    bindings=None,
) -> MaterializedTree:
    """Materialize the verified inventory, or refuse.

    Refuses while the native boundary reports unavailable, which it does
    everywhere today. The implementation below is handle-bound, so the reason
    for refusing is no longer that the operations are unsafe — it is that
    nothing has admitted the backend yet.
    """

    _require_handle_boundary()
    return _materialize_bound(
        commit=commit,
        inventory=inventory,
        read_blob=read_blob,
        base=base,
        bindings=bindings,
    )


def _materialize_bound(
    *,
    commit: str,
    inventory: Mapping[str, str],
    read_blob: BlobReader,
    base: Path,
    bindings=None,
) -> MaterializedTree:
    """Write the verified inventory into a private root under a borrowed `base`.

    Reachable from its own focused tests while `materialize` refuses.

    `inventory` must already have come from the bootstrap chain: paths and
    digests derived only from verified bytes.  Nothing outside it is written,
    and any blob whose bytes do not match its digest fails closed.

    `base` is required, must already exist, and must be stable across runs.  A
    per-call temporary base would put the deterministic root name inside a
    directory nobody can find again, which would silently turn the stale-root
    policy into a no-op.  This module does not create `base`: it is borrowed,
    and a borrowed object must never be deleted, which is an obligation nothing
    that also created it could hold.

    The phase order is the security property, not an implementation detail.

        1. read every blob and verify every digest
        2. pin the pre-existing base
        3. confirm the root name is absent
        4. create and write

    `read_blob` is the one piece of injected, untrusted code here, and it runs
    only in phase 1, while nothing of ours exists on disk and no handle of ours
    is open.  Pinning first would mean holding directory handles across a call
    into that code, for an unbounded time; reading first costs nothing, because
    there is nothing of ours to race yet.  From phase 3 to the end of the write
    loop no external code runs at all.
    """

    if type(commit) is not str or len(commit) != 40:
        raise MaterializationError("COMMIT_INVALID")
    if not isinstance(base, (str, os.PathLike)):
        raise MaterializationError("BASE_INVALID")

    # Phase zero: take a snapshot, before anything else looks at `inventory`.
    # The caller's object is read exactly once. A custom Mapping can run Python
    # on every lookup, and a plain dict can be mutated by the injected reader,
    # so re-reading it would mean the paths, the digests, the root name and the
    # final verification could each have seen a different inventory.
    snapshot = _snapshot_inventory(inventory)

    # Phase one: fetch and verify every blob. No filesystem state of ours exists
    # and no handle of ours is open, so untrusted code has nothing to race.
    checked_paths = {relative: _checked_relative(relative) for relative in snapshot}
    payloads: dict[str, bytes] = {}
    for relative in sorted(snapshot):
        payload = read_blob(commit, relative)
        if type(payload) is not bytes:
            raise MaterializationError("BLOB_NOT_BYTES")
        if _sha256(payload) != snapshot[relative]:
            raise MaterializationError("BLOB_DIGEST_MISMATCH")
        payloads[relative] = payload

    resolved = _bindings_for(bindings)
    base_dir = Path(base)
    root_name = _root_name(commit, snapshot)

    # Phase two: pin the borrowed base. No injected code runs from here on.
    try:
        chain = boundary.open_chain(resolved, str(base_dir))
    except boundary.NativeError as error:
        raise _translate(error) from None

    created: list[tuple[str, object]] = []
    leaves: list[tuple[str, object]] = []
    written: dict[str, str] = {}
    directories: list[str] = []
    try:
        # Phase three: the root name must be absent, and a residue is reported
        # rather than removed.
        require_no_stale_root(resolved, chain.base, commit, snapshot)

        # Phase four: create and write, every open relative to a held handle.
        root_anchor = boundary.create_directory(resolved, chain.base, root_name)
        created.append(("", root_anchor))
        anchors = {"": root_anchor}

        for relative in sorted(checked_paths):
            parts = checked_paths[relative].parts
            for depth in range(1, len(parts)):
                parent = "/".join(parts[:depth])
                if parent in anchors:
                    continue
                above = anchors["/".join(parts[: depth - 1])]
                anchor = boundary.create_directory(resolved, above, parts[depth - 1])
                anchors[parent] = anchor
                created.append((parent, anchor))
                directories.append(parent)
            parent_key = "/".join(parts[:-1])
            leaf = boundary.create_file(
                resolved, anchors[parent_key], parts[-1], payloads[relative]
            )
            leaves.append((relative, leaf))
            written[relative] = snapshot[relative]

        if dict(written) != dict(snapshot):
            raise MaterializationError("MATERIALIZED_SET_MISMATCH")

        tree = _mint(
            base_dir / root_name,
            root_anchor.identity,
            commit,
            snapshot,
            tuple(directories),
            chain,
            tuple(created),
            tuple(leaves),
        )
        verify(tree, bindings=resolved)
        return tree
    except boundary.NativeError as error:
        translated = _translate(error)
        _release(resolved, chain, created, leaves, root_name, translated)
        raise translated from None
    except BaseException as error:
        _release(resolved, chain, created, leaves, root_name, error)
        raise


def _parent_and_name(label: str, anchors: Mapping[str, object], chain, root_name):
    """Where a recorded object lives: the handle above it, and its own name.

    `confirm_absent` is handle-relative, so a name alone is not enough — the
    parent must be the anchor this module still holds, never a path.
    """

    if label == "":
        return chain.base, root_name
    parent_label, _, name = label.rpartition("/")
    return anchors[parent_label], name


def _remove_one(bindings, held, parent_anchor, name) -> None:
    """One object's whole transaction: mark, close, confirm gone.

    Split out because both teardown paths need exactly this, and two
    implementations of a three-step ordering would not stay in step. The
    confirmation is inside the transaction rather than batched at the end: a
    parent must not be attempted while its child may still exist, and a batched
    confirmation would only discover that after the parent was already tried.
    """

    boundary.remove(bindings, held)
    held.close()
    boundary.confirm_absent(bindings, parent_anchor, name)


def _teardown(bindings, chain, created, leaves, root_name):
    """Delete what was made, then release whatever deletion did not reach.

    Two sequences with opposite continuation rules, kept apart on purpose.

    *Deletion stops.* On the first object that will not confirm absent, the
    sequence ends there and no parent is attempted.

    *Release continues.* Every handle deletion did not reach is closed anyway,
    each one attempted even if an earlier close fails, because stopping there
    leaks the handles beneath it. Closing an unmarked handle starts no deletion.

    Returns a list of failure descriptions rather than raising, so an unwinding
    caller can attach them to the error that caused the unwind instead of being
    replaced by them.
    """

    anchors = {label: anchor for label, anchor in created}
    failures: list[str] = []
    removed: set[int] = set()

    stopped = False
    for label, leaf in reversed(leaves):
        parent, name = _parent_and_name(label, anchors, chain, root_name)
        try:
            _remove_one(bindings, leaf, parent, name)
            removed.add(id(leaf))
        except boundary.NativeError as error:
            failures.append(f"{label or '<root>'}: {error.args[0]}")
            stopped = True
            break
    if not stopped:
        for label, anchor in reversed(created):
            parent, name = _parent_and_name(label, anchors, chain, root_name)
            try:
                _remove_one(bindings, anchor, parent, name)
                removed.add(id(anchor))
            except boundary.NativeError as error:
                failures.append(f"{label or '<root>'}: {error.args[0]}")
                break

    for _label, held in list(leaves) + list(created):
        if id(held) in removed or held.closed:
            continue
        try:
            held.close()
        except boundary.NativeError as error:
            failures.append(f"release: {error.args[0]}")
    try:
        boundary.close_chain(bindings, chain)
    except boundary.NativeError as error:
        failures.append(f"chain: {error.args[0]}")
    return failures


def _release(bindings, chain, created, leaves, root_name, error) -> None:
    """Unwind after a failure, without becoming the failure.

    Every problem found here is attached to `error` as a note. The reason the
    unwind is happening is what the caller needs; a `CLEANUP_INCOMPLETE` raised
    over the top of it would hide that.
    """

    for failure in _teardown(bindings, chain, created, leaves, root_name):
        error.add_note(f"cleanup after this error also failed: {failure}")


def _verified_payloads(tree: MaterializedTree, *, bindings=None) -> dict[str, bytes]:
    """Re-verify identity, the exact path set and bytes, then return the bytes.

    This detects a replacement; it does not prevent one.  Preventing a
    substituted module from running is M3's loader problem, not this check.

    Each file is read back through the handle that created it, and its digest
    recomputed. An interim revision of this module dropped that read, on the
    argument that the share mask made the bytes immutable so re-reading them
    proved nothing. The argument was wrong in a way worth recording: a mask
    prevents modification, it does not observe anything, and the same sharing
    violation that stopped this process reading would have stopped M3's child
    loading the modules it was meant to execute. Design revision 21 gave role 3
    `FILE_READ_DATA` and `read_all` for exactly this.

    The read carries two obligations, and losing one of them is how the interim
    revision left a real defect behind: that the bytes are still what was
    written, and that the caller is asking about the inventory the tree was
    built from. A `verify` comparing only path names accepted a map whose every
    digest was wrong.

    Identity comes from the held anchor rather than from an `lstat` on a path,
    so it cannot be answered by whatever currently occupies the name.

    **What is still path-based:** the enumeration that compares the observed
    file set against the record. It reads no bytes and refuses to descend
    through a reparse point, but it is a path walk and the adapter has no
    handle-bound directory enumeration to replace it. This function is
    therefore not entirely handle-bound, and must not be described as if it
    were.

    `bindings` is keyword-only, deliberately. Left positional, a stale caller
    passing an inventory would have bound it silently to `bindings` and failed
    deep inside the boundary with an attribute error instead of at the
    signature, which is the wrong place to find out.

    **No caller-supplied inventory.** An earlier revision took one and
    snapshotted it here, which meant a custom `Mapping` could run arbitrary
    Python while every handle in the tree was open — a callback in the one
    phase that is supposed to have none. The sealed inventory in the tree is
    the only inventory this reads. A caller wanting to know whether the tree
    matches some inventory of theirs can compare `tree.files` themselves,
    outside the window where handles are held.

    **The record is validated first.** `_record_of` runs before anything is
    read, so a duplicated, foreign or already-spent authority is refused before
    a single byte is fetched rather than after.
    """

    resolved = _bindings_for(bindings)
    _record_of(tree)
    root_anchor = None
    for relative, anchor in tree.created:
        if relative == "":
            root_anchor = anchor
            break
    if root_anchor is None:
        raise MaterializationError("RECORD_INVALID")
    try:
        boundary.revalidate(resolved, root_anchor)
    except boundary.NativeError:
        raise MaterializationError("ROOT_IDENTITY_CHANGED") from None
    if root_anchor.identity != tree.root_identity:
        raise MaterializationError("ROOT_IDENTITY_CHANGED")

    # Path-based, and the one part of this function that is. See the docstring.
    present = {
        path.relative_to(tree.root).as_posix() for path in _files_under(tree.root)
    }
    if present != set(tree.files):
        raise MaterializationError("MATERIALIZED_SET_MISMATCH")

    # Byte-for-byte, through the handle that created each file. The leaf labels
    # were checked against the recorded paths by `_record_of`, so reading every
    # leaf covers every recorded file exactly once.
    held = dict(tree.leaves)
    if set(held) != set(tree.files):
        raise MaterializationError("RECORD_INVALID")
    payloads: dict[str, bytes] = {}
    for relative, digest in tree.files.items():
        leaf = held[relative]
        try:
            payload = boundary.read_all(resolved, leaf)
        except boundary.NativeError as error:
            raise _translate(error) from None
        if _sha256(payload) != digest:
            raise MaterializationError("MATERIALIZED_BYTES_CHANGED")
        payloads[relative] = payload
    return payloads


def verify(tree: MaterializedTree, *, bindings=None) -> None:
    """Re-verify one tree without exposing the bytes read through its handles."""

    _verified_payloads(tree, bindings=bindings)


def _record_of(tree: MaterializedTree) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Validate the record before it is allowed to name anything for deletion.

    The record is what removal follows, so a forged or edited one is a way to
    aim a deletion at an object of the forger's choosing.  Two properties are
    required: every file name must survive containment checking, and the
    recorded directories must be exactly the parents those files imply —
    nothing extra, so the record cannot smuggle in a directory to remove.

    Handle-bound removal narrows what a forged record can achieve — deletion
    acts on a handle this module opened, not on a name the record supplies — but
    the record still decides *which* held object is removed, so it is still
    checked.

    Checking `files` and `directories` alone was not enough, and the gap was
    real rather than theoretical: the handles are what actually get deleted, so
    a record could keep a valid set of path names while its `leaves`, `created`
    or `chain` were replaced wholesale, and this function would still pass it.
    The labels on the held objects are therefore required to be exactly the
    recorded paths — no extras, no duplicates, nothing missing — and the chain
    and root anchor have to be present and consistent with them.
    """

    authority = getattr(tree, "_authority", None)
    if not isinstance(authority, _Authority):
        raise MaterializationError("RECORD_INVALID")
    if authority.consumed:
        # An authority is spent once. A second cleanup would act on handles
        # that have already been closed and names that are already gone.
        raise MaterializationError("RECORD_INVALID")

    files = tree.files
    if not isinstance(files, Mapping) or not files:
        raise MaterializationError("RECORD_INVALID")
    checked: list[str] = []
    implied: set[str] = set()
    for relative in files:
        try:
            parts = _checked_relative(relative).parts
        except MaterializationError:
            raise MaterializationError("RECORD_INVALID") from None
        checked.append("/".join(parts))
        implied.update("/".join(parts[:depth]) for depth in range(1, len(parts)))
    directories = tuple(tree.directories)
    if any(type(name) is not str for name in directories):
        raise MaterializationError("RECORD_INVALID")
    if set(directories) != implied or len(set(directories)) != len(directories):
        raise MaterializationError("RECORD_INVALID")

    leaves = tuple(tree.leaves)
    created = tuple(tree.created)
    leaf_labels = [label for label, _held in leaves]
    created_labels = [label for label, _held in created]
    if len(set(leaf_labels)) != len(leaf_labels):
        raise MaterializationError("RECORD_INVALID")
    if len(set(created_labels)) != len(created_labels):
        raise MaterializationError("RECORD_INVALID")
    if set(leaf_labels) != set(checked):
        raise MaterializationError("RECORD_INVALID")
    if set(created_labels) != set(directories) | {""}:
        raise MaterializationError("RECORD_INVALID")
    if any(not isinstance(held, boundary.Leaf) for _label, held in leaves):
        raise MaterializationError("RECORD_INVALID")
    if any(not isinstance(held, boundary.Anchor) for _label, held in created):
        raise MaterializationError("RECORD_INVALID")
    held_objects = [held for _label, held in leaves + created]
    if len({id(held) for held in held_objects}) != len(held_objects):
        # One object recorded twice would be removed twice, and the second
        # attempt would act on a handle that no longer means anything.
        raise MaterializationError("RECORD_INVALID")

    chain = tree.chain
    if not isinstance(chain, boundary.PinnedChain) or not chain.anchors:
        raise MaterializationError("RECORD_INVALID")
    root_anchor = dict(created).get("")
    if root_anchor is None or root_anchor.identity != tree.root_identity:
        raise MaterializationError("RECORD_INVALID")

    return tuple(sorted(checked)), directories


def transport_bundle(
    tree: MaterializedTree, *, bindings=None
) -> tuple[str, str, Mapping[str, str], dict[str, bytes]]:
    """Return root and bytes only for one live, internally consistent authority.

    This is the M3-b-2 producer seam.  It accepts no path parameter and does not
    call ``resolve``, ``absolute``, cwd or an environment fallback.  The existing
    path-based set enumeration in ``_verified_payloads`` remains exactly the
    limitation documented by ``verify``; every payload byte is still read
    through its recorded held handle.
    """

    payloads = _verified_payloads(tree, bindings=bindings)
    root = os.fspath(tree.root)
    if type(root) is not str:
        raise MaterializationError("RECORD_INVALID")
    return root, tree.commit, tree.files, payloads


def transport_root(tree: MaterializedTree, *, bindings=None) -> str:
    """Return only the root projection of the verified transport bundle."""

    return transport_bundle(tree, bindings=bindings)[0]


def cleanup(tree: MaterializedTree, bindings=None) -> None:
    """Remove a materialized root, or refuse.

    Refuses for the same reason `materialize` does: the backend is not
    admitted. What has changed since the path-based version is the consequence
    of being wrong — a redirected removal used to be able to destroy someone
    else's data, and a handle-bound one cannot, because it acts on the object
    this module opened rather than on a name.
    """

    _require_handle_boundary()
    _cleanup_bound(tree, bindings=bindings)


def _cleanup_bound(tree: MaterializedTree, bindings=None) -> None:
    """Remove a materialized tree through the handles that created it.

    A hard crash never reaches this, by definition; that residue is left in
    place and reported by `require_no_stale_root` on the next run.  A removal
    that cannot complete is reported here, because unlike a crash it is
    something the caller can still act on.

    Nothing is deleted until the record validates and the root still has the
    identity it was created with.  A root that has been swapped underneath us
    means every recorded name now points somewhere we have no business
    deleting, so the answer there is to remove nothing and say so.
    """

    resolved = _bindings_for(bindings)
    _record_of(tree)

    root_anchor = dict(tree.created)[""]
    try:
        boundary.revalidate(resolved, root_anchor)
    except boundary.NativeError:
        raise MaterializationError("ROOT_IDENTITY_CHANGED") from None

    failures = _teardown(
        resolved,
        tree.chain,
        tree.created,
        tree.leaves,
        _root_name(tree.commit, tree.files),
    )
    tree._authority.consumed = True
    if failures:
        error = MaterializationError("CLEANUP_INCOMPLETE")
        for failure in failures:
            error.add_note(failure)
        raise error
