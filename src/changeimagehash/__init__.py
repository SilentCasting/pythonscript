"""Change Image Hash: give images a new MD5/SHA-256 without changing how they look."""

from changeimagehash.core import Hashes, Result, change_hash, collect_files

__version__ = "1.0.0"

__all__ = ["Hashes", "Result", "__version__", "change_hash", "collect_files"]
