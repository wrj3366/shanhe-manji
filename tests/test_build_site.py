import importlib.util
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_site.py"
SPEC = importlib.util.spec_from_file_location("build_site", SCRIPT)
BUILD_SITE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(BUILD_SITE)


class BuildSiteTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        result = subprocess.run(
            [sys.executable, str(SCRIPT)], cwd=ROOT, text=True, capture_output=True,
        )
        if result.returncode:
            raise AssertionError(result.stderr)
        cls.dist = ROOT / "dist"

    def test_bundle_contains_public_pages_and_directly_linked_documents(self):
        expected = {
            "index.html", "about.html", "assets/library.css", "assets/library.js",
            "assets/library-data.js", "autumn-homecoming/index.html",
            "ili-original.html", "route-options-grassland.html",
            "route-yining-loop.html", "travel-journal.html",
            "notes/travel-field-notes.md",
            "trips/2026-06-ili/plan.md", "trips/2026-06-ili/review.md",
            "trips/2026-09-autumn-homecoming/plan.md",
            "trips/2026-09-autumn-homecoming/review.md",
        }
        present = {path.relative_to(self.dist).as_posix() for path in self.dist.rglob("*") if path.is_file()}
        self.assertTrue(expected <= present)

    def test_bundle_excludes_private_sources_and_unrelated_untracked_pages(self):
        excluded = {
            "AGENTS.md", "README.md", "data/preferences.json", "scripts/travel.py",
            "tests/test_travel.py", "trips/2026-06-ili/journal.json",
            "trips/2026-06-ili/trip.json", "route-options-preview.html",
            "publish-route-options/index.html",
        }
        for relative in excluded:
            self.assertFalse((self.dist / relative).exists(), relative)

    def test_published_home_has_public_copy_and_validated_links(self):
        index = (self.dist / "index.html").read_text(encoding="utf-8")
        self.assertIn("公开版持续更新", index)
        self.assertNotIn("当前为本地私人档案", index)
        self.assertIn('href="about.html"', index)
        BUILD_SITE.check_html_links(self.dist)
        BUILD_SITE.check_data_links(BUILD_SITE.public_data_paths(), self.dist)

    def test_untracked_file_inside_public_directory_is_not_bundled(self):
        secret = ROOT / "autumn-homecoming" / "untracked-secret.key"
        secret.write_text("private\n", encoding="utf-8")
        try:
            BUILD_SITE.build_site()
            self.assertFalse((self.dist / "autumn-homecoming" / secret.name).exists())
        finally:
            secret.unlink(missing_ok=True)

    def test_arguments_cannot_redirect_output_over_source_directories(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--output", "assets"],
            cwd=ROOT, text=True, capture_output=True,
        )
        self.assertEqual(result.returncode, 2)
        self.assertTrue((ROOT / "assets" / "library.js").exists())


if __name__ == "__main__":
    unittest.main()
