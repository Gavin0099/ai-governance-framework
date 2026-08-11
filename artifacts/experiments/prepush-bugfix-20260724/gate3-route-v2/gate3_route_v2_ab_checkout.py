from __future__ import annotations

import os
import shutil
from collections.abc import Mapping
from pathlib import Path

import gate3_route_v2 as route
import gate3_route_v2_ab as pair


GIT_OMITTED_EMPTY_DIRS = (
    Path("arm-runtime/external"),
    Path("arm-runtime/locators"),
    Path("arm-runtime/private"),
)


def materialize_git_pair_tree(source_root: Path, destination_root: Path) -> Path:
    """Copy a Git-representable pair tree and restore contract-required empties."""
    source_root = source_root.resolve()
    destination_root = destination_root.resolve()
    if not source_root.is_dir():
        raise route.RouteV2Error("Git pair source is not a directory")
    if destination_root.exists():
        raise route.RouteV2Error("materialized pair destination already exists")
    if source_root == destination_root or source_root in destination_root.parents:
        raise route.RouteV2Error("materialized pair destination overlaps source")
    if any(
        os.path.lexists(source_root / relative)
        for relative in GIT_OMITTED_EMPTY_DIRS
    ):
        raise route.RouteV2Error("Git pair source contains runtime-only directory")

    shutil.copytree(source_root, destination_root, symlinks=True)
    for relative in GIT_OMITTED_EMPTY_DIRS:
        (destination_root / relative).mkdir(exist_ok=True)
    return destination_root


def verify_git_pair_tree(
    source_root: Path,
    destination_root: Path,
    *,
    contract_manifest: bytes,
    expected_manifest_sha256: str,
    expected_pins: Mapping[str, str],
) -> dict[str, object]:
    materialized = materialize_git_pair_tree(source_root, destination_root)
    return pair.verify_pair(
        materialized,
        contract_manifest=contract_manifest,
        expected_manifest_sha256=expected_manifest_sha256,
        expected_pins=expected_pins,
    )
