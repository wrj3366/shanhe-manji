import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path


SOURCE_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "travel.py"


class TravelCliTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "scripts").mkdir()
        (self.root / "tests").mkdir()
        (self.root / "data").mkdir()
        (self.root / "trips" / "sample").mkdir(parents=True)
        (self.root / "assets").mkdir()
        shutil.copy2(SOURCE_SCRIPT, self.root / "scripts" / "travel.py")
        self.write_json("data/preferences.json", {
            "updatedAt": "2026-01-01",
            "items": [{
                "id": "slow-travel", "category": "rhythm", "label": "慢旅行",
                "detail": "少赶路", "status": "confirmed",
                "source": {"label": "现场笔记", "path": "notes/source.md", "tripId": "sample"},
            }],
        })
        (self.root / "notes").mkdir()
        (self.root / "notes" / "source.md").write_text("evidence\n", encoding="utf-8")
        (self.root / "trips" / "sample" / "plan.md").write_text("# Plan\n", encoding="utf-8")
        (self.root / "trips" / "sample" / "review.md").write_text("# Review\n", encoding="utf-8")
        self.write_json("trips/sample/trip.json", self.trip())
        self.write_json("trips/sample/journal.json", {"entries": [self.entry()]})

    def tearDown(self):
        self.temp.cleanup()

    def trip(self, **changes):
        value = {
            "id": "sample", "title": "Sample", "status": "planned",
            "dateLabel": "2026-01-02 — 2026-01-03", "startDate": "2026-01-02",
            "endDate": "2026-01-03", "dateNote": "", "summary": "",
            "tags": [], "route": [], "highlights": [],
            "links": [
                {"label": "Plan", "path": "trips/sample/plan.md", "kind": "plan"},
                {"label": "Review", "path": "trips/sample/review.md#top", "kind": "review"},
            ],
            "updatedAt": "2026-01-03",
        }
        value.update(changes)
        return value

    def entry(self, **changes):
        value = {
            "id": "entry-1", "date": "2026-01-02", "title": "Arrival",
            "text": "Good", "type": "observation",
            "source": {"label": "用户现场反馈", "path": "notes/source.md"}, "media": [],
        }
        value.update(changes)
        return value

    def write_json(self, relative, value):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def run_cli(self, *args):
        return subprocess.run(
            [sys.executable, str(self.root / "scripts" / "travel.py"), *args],
            cwd=self.root, text=True, capture_output=True,
        )

    def test_build_is_deterministic_and_escapes_javascript_breakouts(self):
        trip = self.trip(title="</script><b>\u2028\u2029")
        self.write_json("trips/sample/trip.json", trip)
        self.write_json("trips/sample/journal.json", {"entries": [self.entry(date="2099-12-31")]})
        first = self.run_cli("build")
        self.assertEqual(first.returncode, 0, first.stderr)
        content = (self.root / "assets" / "library-data.js").read_text(encoding="utf-8")
        self.assertIn('"updatedAt":"2026-01-03"', content)
        self.assertNotIn("</script>", content)
        self.assertIn("\\u003c/script\\u003e", content)
        self.assertIn("\\u2028\\u2029", content)
        second = self.run_cli("build")
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(content, (self.root / "assets" / "library-data.js").read_text(encoding="utf-8"))

    def test_new_creates_files_and_rejects_duplicate_illegal_slug_and_dates(self):
        result = self.run_cli("new", "spring-road", "--title", "Spring", "--start", "2026-03-04", "--end", "2026-03-08")
        self.assertEqual(result.returncode, 0, result.stderr)
        trip = json.loads((self.root / "trips" / "spring-road" / "trip.json").read_text(encoding="utf-8"))
        self.assertEqual(trip["status"], "planned")
        self.assertEqual(trip["updatedAt"], date.today().isoformat())
        for name in ("trip.json", "journal.json", "plan.md", "review.md"):
            self.assertTrue((self.root / "trips" / "spring-road" / name).exists())
        plan = (self.root / "trips" / "spring-road" / "plan.md").read_text(encoding="utf-8")
        review = (self.root / "trips" / "spring-road" / "review.md").read_text(encoding="utf-8")
        self.assertIn("## 路线与每日安排", plan)
        self.assertIn("## 避坑与调整", review)
        self.assertNotEqual(self.run_cli("new", "spring-road", "--title", "Again").returncode, 0)
        self.assertNotEqual(self.run_cli("new", "Bad_slug", "--title", "Bad").returncode, 0)
        self.assertNotEqual(self.run_cli("new", "bad-date", "--title", "Bad", "--start", "2026-02-30", "--end", "2026-03-01").returncode, 0)
        self.assertFalse((self.root / "trips" / "bad-date").exists())

    def test_new_without_dates_is_idea(self):
        result = self.run_cli("new", "someday", "--title", "Someday")
        self.assertEqual(result.returncode, 0, result.stderr)
        trip = json.loads((self.root / "trips" / "someday" / "trip.json").read_text(encoding="utf-8"))
        self.assertEqual(trip["status"], "idea")
        self.assertIsNone(trip["startDate"])

    def test_note_appends_without_changing_trip_or_existing_entry(self):
        before = json.loads((self.root / "trips" / "sample" / "trip.json").read_text(encoding="utf-8"))
        result = self.run_cli("note", "sample", "--date", "2026-01-03", "--title", "Dinner", "--text", "Great noodles")
        self.assertEqual(result.returncode, 0, result.stderr)
        journal = json.loads((self.root / "trips" / "sample" / "journal.json").read_text(encoding="utf-8"))
        self.assertEqual(journal["entries"][0], self.entry())
        self.assertEqual(journal["entries"][1]["type"], "note")
        self.assertEqual(journal["entries"][1]["source"], {"label": "用户新增记录"})
        after = json.loads((self.root / "trips" / "sample" / "trip.json").read_text(encoding="utf-8"))
        self.assertEqual(after["status"], "planned")
        self.assertEqual(after["updatedAt"], date.today().isoformat())
        self.assertEqual({key: value for key, value in before.items() if key != "updatedAt"}, {key: value for key, value in after.items() if key != "updatedAt"})
        invalid = self.run_cli("note", "sample", "--date", "2026-13-01", "--title", "Bad", "--text", "Bad")
        self.assertNotEqual(invalid.returncode, 0)
        self.assertEqual(len(json.loads((self.root / "trips" / "sample" / "journal.json").read_text())["entries"]), 2)

    def test_check_rejects_bad_json_missing_and_unsafe_links(self):
        trip_path = self.root / "trips" / "sample" / "trip.json"
        trip_path.write_text("{bad", encoding="utf-8")
        self.assertNotEqual(self.run_cli("check").returncode, 0)
        self.write_json("trips/sample/trip.json", self.trip(links=[{"label": "Bad", "path": "../secret", "kind": "plan"}]))
        self.assertNotEqual(self.run_cli("check").returncode, 0)
        self.write_json("trips/sample/trip.json", self.trip(links=[{"label": "Missing", "path": "trips/sample/nope.md", "kind": "plan"}]))
        self.assertNotEqual(self.run_cli("check").returncode, 0)

    def test_check_rejects_schemes_queries_backslashes_encoded_parent_and_symlink_escape(self):
        bad_paths = [
            "javascript:alert(1)",
            "javascript%3Aalert(1)",
            "https://example.test/file",
            "trips/sample/plan.md?raw=1",
            "trips/sample/plan.md%3Fraw=1",
            "trips\\sample\\plan.md",
            "trips%5Csample%5Cplan.md",
            "%2e%2e/secret.md",
            "trips/sample/%2e%2e/%2e%2e/secret.md",
        ]
        for bad in bad_paths:
            with self.subTest(path=bad):
                self.write_json("trips/sample/trip.json", self.trip(links=[{"label": "Bad", "path": bad, "kind": "plan"}]))
                self.assertNotEqual(self.run_cli("check").returncode, 0)
        outside = Path(self.temp.name).parent / f"travel-outside-{Path(self.temp.name).name}.md"
        outside.write_text("outside\n", encoding="utf-8")
        link = self.root / "trips" / "sample" / "escape.md"
        try:
            link.symlink_to(outside)
            self.write_json("trips/sample/trip.json", self.trip(links=[{"label": "Escape", "path": "trips/sample/escape.md", "kind": "plan"}]))
            self.assertNotEqual(self.run_cli("check").returncode, 0)
        finally:
            link.unlink(missing_ok=True)
            outside.unlink(missing_ok=True)

    def test_failed_note_restores_trip_and_journal(self):
        trip_path = self.root / "trips" / "sample" / "trip.json"
        journal_path = self.root / "trips" / "sample" / "journal.json"
        original_trip = trip_path.read_text(encoding="utf-8")
        original_journal = journal_path.read_text(encoding="utf-8")
        (self.root / "assets").rmdir()
        (self.root / "assets").write_text("blocks directory creation", encoding="utf-8")
        result = self.run_cli("note", "sample", "--date", "2026-01-03", "--title", "Dinner", "--text", "Great")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(trip_path.read_text(encoding="utf-8"), original_trip)
        self.assertEqual(journal_path.read_text(encoding="utf-8"), original_journal)

    def test_check_rejects_directory_id_dates_duplicate_entries_and_bad_types(self):
        self.write_json("trips/sample/trip.json", self.trip(id="other"))
        self.assertNotEqual(self.run_cli("check").returncode, 0)
        self.write_json("trips/sample/trip.json", self.trip(startDate="2026-02-02", endDate="2026-01-01"))
        self.assertNotEqual(self.run_cli("check").returncode, 0)
        self.write_json("trips/sample/trip.json", self.trip())
        self.write_json("trips/sample/journal.json", {"entries": [self.entry(), self.entry()]})
        self.assertNotEqual(self.run_cli("check").returncode, 0)
        self.write_json("trips/sample/journal.json", {"entries": [self.entry(type="plan")]})
        self.assertNotEqual(self.run_cli("check").returncode, 0)

    def test_failed_build_does_not_replace_existing_output(self):
        output = self.root / "assets" / "library-data.js"
        output.write_text("keep me\n", encoding="utf-8")
        (self.root / "data" / "preferences.json").write_text("bad", encoding="utf-8")
        self.assertNotEqual(self.run_cli("build").returncode, 0)
        self.assertEqual(output.read_text(encoding="utf-8"), "keep me\n")


if __name__ == "__main__":
    unittest.main()
