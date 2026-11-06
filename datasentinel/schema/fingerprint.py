"""Schema fingerprint extraction and representation."""

from __future__ import annotations

from datasentinel.core.dataset import DataSet
from datasentinel.core.types import SchemaFingerprint


class SchemaFingerprintGenerator:
    """Generates schema fingerprints capturing column types and characteristics."""

    @classmethod
    def generate(cls, dataset: DataSet) -> SchemaFingerprint:
        """Extract a complete schema fingerprint from a DataSet."""
        return dataset.fingerprint()
