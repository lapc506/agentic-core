"""Plugin integrity verification — prevents supply chain attacks."""
from __future__ import annotations
import hashlib
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class IntegrityResult:
    valid: bool
    plugin_name: str
    expected_hash: str
    actual_hash: str
    warnings: list[str] = field(default_factory=list)


class PluginIntegrityVerifier:
    """Verifies plugin manifest integrity and detects tampering."""

    HASH_ALGORITHM = "sha256"
    LOCKFILE_NAME = "plugin-lock.json"

    def __init__(self, plugins_dir: str = "plugins") -> None:
        self._dir = Path(plugins_dir)
        self._lockfile = self._dir / self.LOCKFILE_NAME
        self._known_hashes: dict[str, str] = {}
        self._load_lockfile()

    def _load_lockfile(self) -> None:
        """Load known plugin hashes from lockfile."""
        if self._lockfile.exists():
            try:
                data = json.loads(self._lockfile.read_text())
                self._known_hashes = data.get("plugins", {})
            except Exception:
                logger.warning("Failed to load plugin lockfile")

    def _save_lockfile(self) -> None:
        """Save plugin hashes to lockfile."""
        self._lockfile.parent.mkdir(parents=True, exist_ok=True)
        data = {"version": 1, "plugins": self._known_hashes}
        self._lockfile.write_text(json.dumps(data, indent=2))

    def compute_hash(self, plugin_path: Path) -> str:
        """Compute SHA-256 hash of a plugin's manifest + source files."""
        hasher = hashlib.sha256()

        # Hash manifest
        manifest = plugin_path / "manifest.json"
        if manifest.exists():
            hasher.update(manifest.read_bytes())

        # Hash all .py files sorted alphabetically
        for py_file in sorted(plugin_path.rglob("*.py")):
            hasher.update(py_file.read_bytes())

        # Hash all .yaml files
        for yaml_file in sorted(plugin_path.rglob("*.yaml")):
            hasher.update(yaml_file.read_bytes())

        return hasher.hexdigest()

    def verify(self, plugin_name: str, plugin_path: Path) -> IntegrityResult:
        """Verify a plugin's integrity against known hash."""
        actual_hash = self.compute_hash(plugin_path)
        expected_hash = self._known_hashes.get(plugin_name, "")

        warnings: list[str] = []

        if not expected_hash:
            warnings.append(f"Plugin '{plugin_name}' not in lockfile — first-time registration")
            # Auto-register on first use
            self._known_hashes[plugin_name] = actual_hash
            self._save_lockfile()
            return IntegrityResult(
                valid=True, plugin_name=plugin_name,
                expected_hash=actual_hash, actual_hash=actual_hash,
                warnings=warnings,
            )

        valid = actual_hash == expected_hash
        if not valid:
            warnings.append(f"Plugin '{plugin_name}' hash mismatch — possible tampering!")
            logger.error("SECURITY: Plugin integrity check FAILED for %s (expected=%s, actual=%s)",
                        plugin_name, expected_hash[:12], actual_hash[:12])

        return IntegrityResult(
            valid=valid, plugin_name=plugin_name,
            expected_hash=expected_hash, actual_hash=actual_hash,
            warnings=warnings,
        )

    def register(self, plugin_name: str, plugin_path: Path) -> str:
        """Register a plugin's hash in the lockfile."""
        hash_val = self.compute_hash(plugin_path)
        self._known_hashes[plugin_name] = hash_val
        self._save_lockfile()
        return hash_val

    def verify_all(self) -> list[IntegrityResult]:
        """Verify all plugins in the directory."""
        results: list[IntegrityResult] = []
        if not self._dir.exists():
            return results
        for plugin_dir in sorted(self._dir.iterdir()):
            if plugin_dir.is_dir() and not plugin_dir.name.startswith("."):
                result = self.verify(plugin_dir.name, plugin_dir)
                results.append(result)
        return results

    @property
    def known_count(self) -> int:
        return len(self._known_hashes)
