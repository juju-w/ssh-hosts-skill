#!/usr/bin/env python3
"""Build the localized SkillHub/WorkBuddy distribution package."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="new output directory")
    args = parser.parse_args()

    packaging_dir = Path(__file__).resolve().parent
    repository = packaging_dir.parents[1]
    source = repository / "skills" / "ssh-hosts"
    output = args.output.expanduser().resolve()

    if output.exists():
        parser.error(f"output already exists: {output}")

    shutil.copytree(source, output)

    for relative in (
        Path("SKILL.md"),
        Path("agents/openai.yaml"),
        Path("references/configuration.md"),
        Path("references/examples.md"),
        Path("references/platforms.md"),
    ):
        localized = packaging_dir / relative
        destination = output / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(localized, destination)

    assets = output / "assets"
    for icon in ("ssh-hosts-icon-128.png", "ssh-hosts-icon-512.png"):
        path = assets / icon
        if path.exists():
            path.unlink()
    if assets.exists() and not any(assets.iterdir()):
        assets.rmdir()

    print(f"Built SkillHub zh-CN package: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
