"""Utility script to clean generated artifacts under the outputs directory."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path


DEFAULT_OUTPUTS_DIR = Path(__file__).resolve().parent.parent / "outputs"


def _clean_outputs(outputs_dir: Path, dry_run: bool) -> list[Path]:
    removed: list[Path] = []
    for child in outputs_dir.iterdir():
        if child.is_dir():
            if dry_run:
                removed.append(child)
                continue
            shutil.rmtree(child)
            removed.append(child)
        else:
            if dry_run:
                removed.append(child)
                continue
            child.unlink(missing_ok=True)
            removed.append(child)
    return removed


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Clean generated files in the outputs directory without deleting the folder itself."
    )
    parser.add_argument(
        "--outputs-dir",
        type=Path,
        default=DEFAULT_OUTPUTS_DIR,
        help="Path to the outputs directory (defaults to project_root/outputs)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List what would be removed without deleting anything",
    )
    args = parser.parse_args()

    outputs_dir = args.outputs_dir.resolve()
    if not outputs_dir.exists():
        raise SystemExit(f"Outputs directory not found: {outputs_dir}")
    if not outputs_dir.is_dir():
        raise SystemExit(f"Path is not a directory: {outputs_dir}")

    removed = _clean_outputs(outputs_dir, args.dry_run)
    if args.dry_run:
        print("[dry-run] Items that would be removed:")
    else:
        print("Removed:")

    if not removed:
        print("  (nothing to remove)")
        return

    for path in removed:
        print(f"  {path}")


if __name__ == "__main__":
    main()
