"""Exact disposable subtree export. No task or evaluator bytes enter a leaf."""

from io import BytesIO
from pathlib import PurePosixPath
import tarfile

from governance_tools import solo_r2_attempt_materialization as material
from governance_tools import solo_r2_disposable_binding as binding


class DisposableGitMaterializer(material.FrozenGitMaterializer):
    def __init__(self, *, authority, **kwargs):
        super().__init__(**kwargs)
        if type(authority) is not binding.ExperimentInputAuthority:
            material._fail(material.PAIR_INVALID)
        self.authority = authority
        self._validate_packet()

    def _validate_packet(self):
        packet = self.packet
        if (type(packet) is not material.TreatmentInstruction
                or len(packet.payload) != material.TREATMENT_PACKET_BYTES
                or material._sha256_bytes(packet.payload) != material.TREATMENT_PACKET_SHA256
                or material._git_blob_sha1(packet.payload) != material.TREATMENT_PACKET_GIT_BLOB
                or packet.sha256 != material.TREATMENT_PACKET_SHA256
                or packet.git_blob != material.TREATMENT_PACKET_GIT_BLOB):
            material._fail(material.PAIR_INVALID)

    def verify_authority(self):
        loaded = binding.load_input_authority(
            git=self.git, repository=self.repository, temp_root=self.leaves.root,
        )
        if loaded != self.authority:
            material._fail(material.PAIR_INVALID)
        self._validate_packet()
        return loaded.document()

    def task_bytes(self):
        item = self.verify_authority()["task_prompt"]
        raw = material._run_git(self.git, self.repository,
            ("--no-replace-objects", "cat-file", "blob", f"{item['commit']}:{item['path']}"),
            temp_root=self.leaves.root)
        self._verify_blob(raw, item)
        return raw

    @staticmethod
    def _verify_blob(raw, item):
        if (len(raw) != item["bytes"] or material._sha256_bytes(raw) != item["sha256"]
                or material._git_blob_sha1(raw) != item["git_blob_oid"]):
            material._fail(material.PAIR_INVALID)

    def _verified_payloads(self):
        data = self.verify_authority()
        snapshot = data["base_snapshot"]
        archive = material._run_git(self.git, self.repository,
            ("--no-replace-objects", "-c", "core.autocrlf=false", "archive", "--format=tar",
             f"{snapshot['commit']}:{snapshot['subdirectory']}"), temp_root=self.leaves.root)
        expected = {str(PurePosixPath(item["path"]).relative_to(snapshot["subdirectory"])): item
                    for item in snapshot["files"]}
        payloads = {}
        forbidden = {data[k]["git_blob_oid"] for k in ("task_prompt", "rubric", "oracle", "reference_repair")}
        forbidden.add(material.TREATMENT_PACKET_GIT_BLOB)
        try:
            with tarfile.open(fileobj=BytesIO(archive), mode="r:") as stream:
                for member in stream.getmembers():
                    # Closed two-file set rejects parent/whole-tree export, links,
                    # duplicate names and every noncanonical path before any write.
                    if (member.name not in expected or member.name in payloads
                            or member.type != tarfile.REGTYPE
                            or member.size != expected[member.name]["bytes"]):
                        material._fail(material.PAIR_INVALID)
                    source = stream.extractfile(member)
                    if source is None:
                        material._fail(material.PAIR_INVALID)
                    raw = source.read()
                    self._verify_blob(raw, expected[member.name])
                    if material._git_blob_sha1(raw) in forbidden:
                        material._fail(material.PAIR_INVALID)
                    payloads[member.name] = raw
        except (tarfile.TarError, OSError, EOFError, ValueError):
            material._fail(material.PAIR_INVALID)
        if set(payloads) != set(expected):
            material._fail(material.PAIR_INVALID)
        return snapshot, payloads

    def materialize(self, token):
        snapshot, payloads = self._verified_payloads()
        leaf = self.leaves.create(token)
        try:
            for name, raw in payloads.items():
                with (leaf.path / name).open("xb") as stream:
                    stream.write(raw)
            expected = tuple(sorted((name, len(raw), material._sha256_bytes(raw))
                                    for name, raw in payloads.items()))
            if material.workspace_inventory(leaf.path) != expected:
                material._fail(material.PAIR_INVALID)
            return leaf
        except BaseException:
            self.leaves.release(leaf)
            raise

    def _one(self, pair_id, ordinal, treatment):
        leaf = self.materialize(f"{pair_id}-qualification-{ordinal}")
        try:
            inventory = material.workspace_inventory(leaf.path)
            return material.ArmMaterializationEvidence(
                ordinal, self.authority.document()["base_snapshot"]["commit"],
                inventory, material.inventory_sha256(inventory),
                leaf.acl.sandbox_principal, leaf.acl.sandbox_account_generation,
                self.packet.sha256 if treatment else None, True,
            )
        finally:
            self.leaves.release(leaf)

    def qualify_pair(self, pair_id, host_local):
        host_local.validate()
        result = material.PairMaterializationEvidence(
            self._one(pair_id, 1, False), self._one(pair_id, 2, True),
            host_local, self.authority,
        )
        result.validate()
        return result
