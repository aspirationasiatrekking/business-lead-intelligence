"""Publish complete export files without exposing partially written output."""

import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from tempfile import NamedTemporaryFile


@contextmanager
def atomic_output(
    output_path: str | Path, extension: str, *, overwrite: bool = False
) -> Iterator[Path]:
    """Write beside the target and publish only after a successful write."""
    target = Path(output_path)
    if target.suffix.lower() != extension or not target.stem:
        raise ValueError(f"Export filename must end with {extension}.")
    if not target.parent.is_dir():
        raise FileNotFoundError("Export parent directory does not exist.")
    if target.is_symlink() or (target.exists() and not target.is_file()):
        raise ValueError("Export destination must be a regular file.")
    if not overwrite and target.exists():
        raise FileExistsError(target)

    # Close the temporary handle before the caller opens it (Windows support).
    with NamedTemporaryFile(
        dir=target.parent, prefix=".export-", suffix=extension, delete=False
    ) as temporary:
        temporary_path = Path(temporary.name)

    try:
        yield temporary_path
        with temporary_path.open("rb+") as stream:
            os.fsync(stream.fileno())
        if overwrite:
            os.replace(temporary_path, target)
        else:
            # Atomic no-clobber publication, including concurrent writers.
            # Unsupported filesystems fail rather than risking an overwrite.
            os.link(temporary_path, target)
    finally:
        temporary_path.unlink(missing_ok=True)
