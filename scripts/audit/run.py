"""Run — a collection of AuditResults sharing run-level defaults.

A Run is allowed to contain mixed schemas; consumers must group by schema
before averaging composites. Run-level provenance (git_sha, default skill
shas) supplies defaults; per-result provenance is authoritative when both
are present.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping

from .result import AuditResult


SCHEMA_VERSION = 2


@dataclass(frozen=True)
class Run:
    run_id: str
    timestamp: str
    git_sha: str
    default_skill_shas: Mapping[str, str]
    results: tuple[AuditResult, ...]

    def to_dict(self) -> dict:
        return {
            "schema_version": SCHEMA_VERSION,
            "run_id": self.run_id,
            "timestamp": self.timestamp,
            "git_sha": self.git_sha,
            "default_skill_shas": dict(self.default_skill_shas),
            "results": [r.to_dict() for r in self.results],
        }

    @classmethod
    def from_dict(cls, d: Mapping) -> "Run":
        version = d.get("schema_version")
        if version != SCHEMA_VERSION:
            raise ValueError(
                f"Run.from_dict: schema_version {version!r} ≠ {SCHEMA_VERSION} "
                f"(legacy v1 records do not round-trip into the v2 package)"
            )
        return cls(
            run_id=d["run_id"],
            timestamp=d["timestamp"],
            git_sha=d["git_sha"],
            default_skill_shas=dict(d.get("default_skill_shas", {})),
            results=tuple(AuditResult.from_dict(r) for r in d["results"]),
        )

    def write(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False))

    @classmethod
    def read(cls, path: Path) -> "Run":
        return cls.from_dict(json.loads(Path(path).read_text()))

    def by_schema(self, schema_id: str) -> tuple[AuditResult, ...]:
        return tuple(r for r in self.results if r.schema_id == schema_id)

    def schemas_present(self) -> tuple[str, ...]:
        seen: list[str] = []
        for r in self.results:
            if r.schema_id not in seen:
                seen.append(r.schema_id)
        return tuple(seen)
