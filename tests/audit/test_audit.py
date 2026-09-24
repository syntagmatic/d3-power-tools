"""Unit tests for scripts/audit/.

Run with: python3 -m unittest tests.audit.test_audit
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from scripts.audit import (
    GENERAL,
    TRANSITION,
    AuditProvenance,
    AuditResult,
    DimensionScore,
    Run,
    compare,
    PairingPolicy,
)
from scripts.audit.schema import CompositeSnapshot


def _prov(**overrides) -> AuditProvenance:
    base = dict(
        block_id="block-x",
        fixture_id="default",
        generator_model="gen-m",
        judge_model="judge-m",
        evaluator_id="general",
        block_sha="abc1234",
        timestamp="2026-04-29T12:00:00Z",
    )
    base.update(overrides)
    return AuditProvenance(**base)


def _general_result(**score_overrides) -> AuditResult:
    base = {
        "visual_critic": 7.0,
        "encoding_integrity": 8.0,
        "cognitive_load": 7.0,
        "stress_test": 6.0,
    }
    base.update(score_overrides)
    scores = {
        k: DimensionScore(value=v, source_tool=k, flags=("Update Storm",) if k == "stress_test" else ())
        for k, v in base.items()
    }
    return AuditResult(
        schema_id="general", status="passed", provenance=_prov(), scores=scores,
    ).with_composite()


def _transition_result(t=7.0, vc=7.0) -> AuditResult:
    scores = {
        "transition": DimensionScore(value=t, source_tool="transition_judge"),
        "visual_critic": DimensionScore(value=vc, source_tool="visual_critic"),
    }
    return AuditResult(
        schema_id="transition", status="passed",
        provenance=_prov(block_id="hierarchy-bundles", evaluator_id="transition"),
        scores=scores,
    ).with_composite()


class TestSchema(unittest.TestCase):
    def test_general_composite(self):
        r = _general_result()
        # 7*.30 + 8*.25 + 7*.25 + 6*.20 = 2.1 + 2.0 + 1.75 + 1.2 = 7.05
        self.assertAlmostEqual(r.composite.value, 7.05, places=3)
        self.assertTrue(r.composite.complete)
        self.assertEqual(r.composite.missing_dimensions, ())

    def test_transition_composite(self):
        r = _transition_result(t=8, vc=6)
        # 8*.6 + 6*.4 = 4.8 + 2.4 = 7.2
        self.assertAlmostEqual(r.composite.value, 7.2, places=3)

    def test_complete_only_with_missing_returns_none(self):
        scores = {
            "visual_critic": DimensionScore(value=7.0, source_tool="visual_critic"),
        }
        snap = GENERAL.composite(scores, policy="complete_only")
        self.assertIsNone(snap.value)
        self.assertFalse(snap.complete)
        self.assertEqual(set(snap.missing_dimensions), {
            "encoding_integrity", "cognitive_load", "stress_test"
        })

    def test_renormalize_partial_with_one_dim(self):
        scores = {
            "visual_critic": DimensionScore(value=7.0, source_tool="visual_critic"),
        }
        snap = GENERAL.composite(scores, policy="renormalize_partial")
        # Only visual_critic present (weight 0.30 / total weight 0.30) → value=7.0
        self.assertAlmostEqual(snap.value, 7.0, places=3)
        self.assertFalse(snap.complete)

    def test_renormalize_partial_with_no_dims(self):
        snap = GENERAL.composite({}, policy="renormalize_partial")
        self.assertIsNone(snap.value)
        self.assertFalse(snap.complete)


class TestRoundTrip(unittest.TestCase):
    def test_audit_result_roundtrip(self):
        r = _general_result()
        d = r.to_dict()
        r2 = AuditResult.from_dict(d)
        self.assertEqual(r.to_dict(), r2.to_dict())

    def test_run_roundtrip(self):
        run = Run(
            run_id="rt-1", timestamp="2026-04-29T12:00Z", git_sha="abc",
            default_skill_shas={"visual_critic": "111"},
            results=(_general_result(), _transition_result()),
        )
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "run.json"
            run.write(p)
            run2 = Run.read(p)
            self.assertEqual(run.to_dict(), run2.to_dict())

    def test_from_dict_rejects_missing_provenance(self):
        d = _general_result().to_dict()
        del d["provenance"]["fixture_id"]
        with self.assertRaises(ValueError):
            AuditResult.from_dict(d)

    def test_from_dict_rejects_unknown_schema(self):
        d = _general_result().to_dict()
        d["schema_id"] = "definitely-not-a-schema"
        with self.assertRaises(ValueError):
            AuditResult.from_dict(d)

    def test_from_dict_rejects_legacy_v1_run(self):
        v1 = {
            "timestamp": "2026-04-29",
            "git_sha": "abc",
            "blocks": {},
        }
        with self.assertRaises(ValueError):
            Run.from_dict(v1)

    def test_from_dict_rejects_tampered_composite(self):
        d = _general_result().to_dict()
        d["composite"]["value"] = 99.0  # lie about the composite
        with self.assertRaises(ValueError):
            AuditResult.from_dict(d)

    def test_from_dict_rejects_cross_schema_composite(self):
        d = _general_result().to_dict()
        d["composite"]["schema_id"] = "transition"
        with self.assertRaises(ValueError):
            AuditResult.from_dict(d)


class TestCompare(unittest.TestCase):
    def _run(self, *results) -> Run:
        return Run(
            run_id="r", timestamp="t", git_sha="g",
            default_skill_shas={}, results=tuple(results),
        )

    def test_pass_within_tolerance(self):
        baseline = self._run(_general_result())
        # Same key, slightly worse composite (7.05 → 6.95, delta = -0.10, within 0.5)
        treatment = self._run(_general_result(visual_critic=6.6))
        c = compare(baseline, treatment)
        self.assertEqual(c.verdict, "pass")
        self.assertEqual(len(c.diffs), 1)
        d = c.diffs[0]
        self.assertAlmostEqual(d.per_dimension_diff["visual_critic"], -0.4, places=3)
        # Serialized form drops empty FlagChanges; that's the consumer-facing shape.
        self.assertEqual(d.to_dict()["dimension_flags_changed"], {})

    def test_fail_outside_tolerance(self):
        baseline = self._run(_general_result())
        treatment = self._run(_general_result(visual_critic=2.0, encoding_integrity=2.0))
        c = compare(baseline, treatment, tolerance=0.5)
        self.assertEqual(c.verdict, "fail")

    def test_flag_set_change_recorded(self):
        baseline = self._run(_general_result())  # has Update Storm
        treatment_scores = {
            "visual_critic": DimensionScore(value=7.0, source_tool="visual_critic"),
            "encoding_integrity": DimensionScore(value=8.0, source_tool="encoding_integrity"),
            "cognitive_load": DimensionScore(value=7.0, source_tool="cognitive_load"),
            "stress_test": DimensionScore(value=6.0, source_tool="stress_test", flags=("Stale Closure",)),
        }
        treatment = self._run(AuditResult(
            schema_id="general", status="passed", provenance=_prov(), scores=treatment_scores,
        ).with_composite())
        c = compare(baseline, treatment)
        diff = c.diffs[0].dimension_flags_changed
        self.assertIn("stress_test", diff)
        self.assertEqual(set(diff["stress_test"].added), {"Stale Closure"})
        self.assertEqual(set(diff["stress_test"].removed), {"Update Storm"})

    def test_schema_mismatch_refuses(self):
        # Same key tuple shape but different schemas → refuse
        prov_g = _prov(block_id="x", evaluator_id="general")
        prov_t = _prov(block_id="x", evaluator_id="general")  # same key
        # Force same ResultKey by giving them the same provenance, different schemas
        g = AuditResult(
            schema_id="general", status="passed", provenance=prov_g,
            scores={
                "visual_critic": DimensionScore(value=7, source_tool="visual_critic"),
                "encoding_integrity": DimensionScore(value=7, source_tool="encoding_integrity"),
                "cognitive_load": DimensionScore(value=7, source_tool="cognitive_load"),
                "stress_test": DimensionScore(value=7, source_tool="stress_test"),
            },
        ).with_composite()
        # We need same key with mismatched schema → only possible if evaluator_id differs;
        # but ResultKey.schema_id is in the key itself, so a true cross-schema collision
        # cannot pair. Instead test the inner _diff_pair refusal directly.
        from scripts.audit.compare import _diff_pair
        t_scores = {
            "transition": DimensionScore(value=7, source_tool="transition_judge"),
            "visual_critic": DimensionScore(value=7, source_tool="visual_critic"),
        }
        t = AuditResult(
            schema_id="transition", status="passed", provenance=prov_t,
            scores=t_scores,
        ).with_composite()
        with self.assertRaises(ValueError):
            _diff_pair(g, t)

    def test_unpaired_raises_by_default(self):
        baseline = self._run(_general_result())
        # Different block_id → unpaired
        treatment = self._run(AuditResult(
            schema_id="general", status="passed",
            provenance=_prov(block_id="other-block"),
            scores=_general_result().scores,
        ).with_composite())
        with self.assertRaises(ValueError):
            compare(baseline, treatment)

    def test_unpaired_inconclusive_when_allowed(self):
        baseline = self._run(_general_result())
        treatment = self._run(AuditResult(
            schema_id="general", status="passed",
            provenance=_prov(block_id="other-block"),
            scores=_general_result().scores,
        ).with_composite())
        c = compare(baseline, treatment, allow_unpaired=True)
        self.assertEqual(c.verdict, "inconclusive")
        self.assertEqual(len(c.missing_baseline), 1)
        self.assertEqual(len(c.missing_treatment), 1)

    def test_render_error_drives_fail(self):
        baseline = self._run(_general_result())
        treatment = self._run(AuditResult(
            schema_id="general", status="render_failed",
            provenance=_prov(), scores={},
            result_flags=("render-error",),
        ))
        # paired by key (same provenance) but treatment has render-error
        c = compare(baseline, treatment, allow_unpaired=True)
        self.assertEqual(c.verdict, "fail")


if __name__ == "__main__":
    unittest.main()
