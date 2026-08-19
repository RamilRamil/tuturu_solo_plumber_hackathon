"""Sequential coverage.json wave merge. Slug is identity; no EN/RU matching."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ingest.coverage_state import (
    STATUS_FAILED,
    STATUS_LOADED,
    empty_coverage_state,
    load_coverage_state,
    merge_wave,
    save_coverage_state,
)


def _loaded(state: dict) -> set[str]:
    return {r["slug"] for r in state["regions"] if r["status"] == STATUS_LOADED}


class CoverageStateTests(unittest.TestCase):
    def test_sequential_waves_keep_both_loaded(self) -> None:
        state = empty_coverage_state()
        state = merge_wave(
            state,
            [{"slug": "moscow", "label": "Moscow", "status": STATUS_LOADED}],
            poi_count_db=10,
            poi_count_wave=10,
        )
        state = merge_wave(
            state,
            [{"slug": "tver", "label": "Tver", "status": STATUS_LOADED}],
            poi_count_db=25,
            poi_count_wave=15,
        )
        self.assertEqual(_loaded(state), {"moscow", "tver"})
        self.assertEqual(state["poi_count_db"], 25)
        self.assertEqual(state["poi_count_wave"], 15)
        self.assertEqual(state["regions_loaded"], ["moscow", "tver"])

    def test_failed_wave_does_not_drop_or_mark_loaded(self) -> None:
        state = merge_wave(
            empty_coverage_state(),
            [{"slug": "moscow", "label": "Moscow", "status": STATUS_LOADED}],
            poi_count_db=10,
            poi_count_wave=10,
        )
        state = merge_wave(
            state,
            [{"slug": "tver", "label": "Tver", "status": STATUS_LOADED}],
            poi_count_db=25,
            poi_count_wave=15,
        )
        failed = merge_wave(
            state,
            [{"slug": "spb", "label": "SPb", "status": STATUS_FAILED}],
            poi_count_db=25,
            poi_count_wave=0,
        )
        self.assertEqual(_loaded(failed), {"moscow", "tver"})
        spb = next(r for r in failed["regions"] if r["slug"] == "spb")
        self.assertEqual(spb["status"], STATUS_FAILED)
        self.assertNotIn("spb", failed["regions_loaded"])

        keep = merge_wave(
            failed,
            [{"slug": "moscow", "label": "Moscow", "status": STATUS_FAILED}],
            poi_count_db=25,
            poi_count_wave=0,
        )
        moscow = next(r for r in keep["regions"] if r["slug"] == "moscow")
        self.assertEqual(moscow["status"], STATUS_LOADED)
        self.assertEqual(_loaded(keep), {"moscow", "tver"})

    def test_load_missing_file_is_empty(self) -> None:
        state = load_coverage_state(Path("/tmp/burger-coverage-missing-no-such.json"))
        self.assertEqual(state["regions"], [])
        self.assertEqual(state["poi_count_db"], 0)

    def test_legacy_regions_loaded_identity_migrate(self) -> None:
        tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        tmp.close()
        path = Path(tmp.name)
        try:
            path.write_text(
                json.dumps({"regions_loaded": ["yaroslavl-oblast"], "poi_count": 2084}) + "\n",
                encoding="utf-8",
            )
            state = load_coverage_state(path)
            self.assertEqual(len(state["regions"]), 1)
            self.assertEqual(state["regions"][0]["slug"], "yaroslavl-oblast")
            self.assertEqual(state["regions"][0]["label"], "yaroslavl-oblast")
            self.assertEqual(state["regions"][0]["status"], STATUS_LOADED)
            merged = merge_wave(
                state,
                [{"slug": "tver", "label": "Tver", "status": STATUS_LOADED}],
                poi_count_db=3000,
                poi_count_wave=900,
            )
            self.assertEqual(_loaded(merged), {"yaroslavl-oblast", "tver"})
            save_coverage_state(path, merged)
            again = load_coverage_state(path)
            self.assertEqual(_loaded(again), {"yaroslavl-oblast", "tver"})
            self.assertEqual(again["poi_count_db"], 3000)
        finally:
            try:
                path.unlink()
            except OSError:
                pass

    def test_slug_not_confused_with_label(self) -> None:
        state = merge_wave(
            empty_coverage_state(),
            [{"slug": "moscow", "label": "Moskva", "status": STATUS_LOADED}],
            poi_count_db=1,
            poi_count_wave=1,
        )
        state = merge_wave(
            state,
            [{"slug": "moskva", "label": "moscow", "status": STATUS_LOADED}],
            poi_count_db=2,
            poi_count_wave=1,
        )
        self.assertEqual(_loaded(state), {"moscow", "moskva"})
        labels = {r["slug"]: r["label"] for r in state["regions"]}
        self.assertEqual(labels["moscow"], "Moskva")
        self.assertEqual(labels["moskva"], "moscow")


if __name__ == "__main__":
    unittest.main()
