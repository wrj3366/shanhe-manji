#!/usr/bin/env python3
"""Build the public, static edition of 山河慢记 into ``dist/``."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "dist"
TRAVEL_SCRIPT = ROOT / "scripts" / "travel.py"
CORE_FILES = (
    "index.html",
    "assets/library.css",
    "assets/library.js",
    "assets/library-data.js",
    "ili-original.html",
    "route-options-grassland.html",
    "route-yining-loop.html",
    "travel-journal.html",
)
CORE_DIRECTORIES = ("autumn-homecoming",)
PUBLIC_ASSET_SUFFIXES = {
    ".css", ".gif", ".html", ".jpeg", ".jpg", ".js", ".json", ".md",
    ".png", ".svg", ".txt", ".webp", ".woff", ".woff2",
}
PRIVATE_PARTS = {".git", ".idea", ".env", "__pycache__", "scripts", "tests"}
ABOUT_HTML = """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <meta name="description" content="山河慢记项目说明">
  <title>关于 · 山河慢记</title>
  <link rel="stylesheet" href="assets/library.css">
</head>
<body>
  <header class="site-header"><a class="brand" href="index.html">山河慢记 <span>我们的旅行日志</span></a></header>
  <main>
    <section class="continuation" style="margin-top:clamp(48px,9vw,112px)">
      <div>
        <p class="eyebrow">ABOUT THIS JOURNAL</p>
        <h1>一份持续更新的旅行档案</h1>
        <p>山河慢记把行前路书、途中观察与旅后复盘放在一起。计划和真实经历分开记录，让每次出发都能接着过去的经验继续写。</p>
      </div>
      <div class="continuation-notes">
        <p><strong>计划</strong><span>路线、节奏和待核实事项</span></p>
        <p><strong>记录</strong><span>真实到访与现场感受</span></p>
        <p><strong>复盘</strong><span>值得保留的经验和下一站</span></p>
        <a href="https://github.com/wrjvszq/shanhe-manji" rel="noopener noreferrer">查看 GitHub 仓库 ↗</a>
        <a href="index.html">返回旅行档案首页</a>
      </div>
    </section>
  </main>
</body>
</html>
"""


class BuildError(Exception):
    """A public bundle could not be created safely."""


class LinkCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        wanted = "href" if tag in {"a", "link"} else "src" if tag in {"img", "script", "source"} else None
        if not wanted:
            return
        for name, value in attrs:
            if name == wanted and value:
                self.links.append((wanted, value))


def run_travel(command: str) -> None:
    result = subprocess.run(
        [sys.executable, str(TRAVEL_SCRIPT), command],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    if result.returncode:
        detail = result.stderr.strip() or result.stdout.strip() or "unknown error"
        raise BuildError(f"travel.py {command} failed: {detail}")


def tracked_paths() -> set[Path]:
    result = subprocess.run(
        ["git", "ls-files", "-z"], cwd=ROOT, capture_output=True,
    )
    if result.returncode:
        raise BuildError("git ls-files failed; the public bundle requires a Git worktree")
    return {
        ROOT.joinpath(*PurePosixPath(raw.decode("utf-8")).parts).resolve()
        for raw in result.stdout.split(b"\0") if raw
    }


def source_path(raw: str) -> Path:
    base = raw.partition("#")[0]
    parsed = urlsplit(base)
    if not base or parsed.scheme or parsed.netloc or parsed.query or "\\" in base:
        raise BuildError(f"unsafe public link: {raw}")
    decoded = unquote(parsed.path)
    pure = PurePosixPath(decoded)
    if pure.is_absolute() or ".." in pure.parts or any(part in PRIVATE_PARTS for part in pure.parts):
        raise BuildError(f"unsafe public link: {raw}")
    target = ROOT.joinpath(*pure.parts).resolve()
    try:
        target.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise BuildError(f"public link escapes repository: {raw}") from exc
    if not target.exists():
        raise BuildError(f"missing public link target: {raw}")
    return target


def collect_data_paths(value: object) -> set[str]:
    paths: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            if key == "path" and isinstance(child, str):
                paths.add(child)
            else:
                paths.update(collect_data_paths(child))
    elif isinstance(value, list):
        for child in value:
            paths.update(collect_data_paths(child))
    return paths


def public_data_paths() -> set[str]:
    values: list[object] = [json.loads((ROOT / "data/preferences.json").read_text(encoding="utf-8"))]
    for trip_file in sorted((ROOT / "trips").glob("*/trip.json")):
        values.append(json.loads(trip_file.read_text(encoding="utf-8")))
        journal = trip_file.with_name("journal.json")
        values.append(json.loads(journal.read_text(encoding="utf-8")))
    result: set[str] = set()
    for value in values:
        result.update(collect_data_paths(value))
    for trip_directory in sorted(path for path in (ROOT / "trips").iterdir() if path.is_dir()):
        for name in ("plan.md", "review.md"):
            document = trip_directory / name
            if document.exists():
                result.add(document.relative_to(ROOT).as_posix())
    return result


def copy_file(source: Path, staging: Path, tracked: set[Path]) -> None:
    if source.resolve() not in tracked:
        raise BuildError(f"refusing to publish untracked file: {source.relative_to(ROOT)}")
    relative = source.relative_to(ROOT)
    destination = staging / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def copy_public_directory(source: Path, staging: Path, tracked: set[Path]) -> None:
    relative = source.relative_to(ROOT)
    if relative.parts and relative.parts[0] == "trips" and (len(relative.parts) < 3 or relative.parts[2] != "page"):
        raise BuildError(f"trip page directories must use trips/<id>/page: {relative}")
    for item in sorted(source.rglob("*")):
        if (
            not item.is_file()
            or item.resolve() not in tracked
            or any(part in PRIVATE_PARTS for part in item.relative_to(ROOT).parts)
        ):
            continue
        if item.suffix.lower() in PUBLIC_ASSET_SUFFIXES or source.relative_to(ROOT).as_posix() in CORE_DIRECTORIES:
            copy_file(item, staging, tracked)


def published_target(raw: str, staging: Path) -> Path:
    target = source_path(raw)
    relative = target.relative_to(ROOT)
    return staging / relative


def write_published_index(staging: Path) -> None:
    source = (ROOT / "index.html").read_text(encoding="utf-8")
    source = source.replace(
        "当前为本地私人档案；公开分享另行选择内容。",
        "公开版持续更新；计划、现场记录与复盘会分开标注。",
    )
    source = source.replace('href="README.md"', 'href="about.html"')
    (staging / "index.html").write_text(source, encoding="utf-8", newline="\n")


def is_external_or_anchor(raw: str) -> bool:
    if raw.startswith("#"):
        return True
    parsed = urlsplit(raw)
    return bool(parsed.scheme or parsed.netloc)


def check_html_links(staging: Path) -> None:
    errors: list[str] = []
    for html_file in sorted(staging.rglob("*.html")):
        parser = LinkCollector()
        parser.feed(html_file.read_text(encoding="utf-8"))
        for attribute, raw in parser.links:
            if is_external_or_anchor(raw):
                continue
            parsed = urlsplit(raw)
            decoded = unquote(parsed.path)
            target = (html_file.parent / decoded).resolve()
            try:
                target.relative_to(staging.resolve())
            except ValueError:
                errors.append(f"{html_file.relative_to(staging)}: {attribute} escapes site: {raw}")
                continue
            if target.is_dir():
                target = target / "index.html"
            if not target.exists():
                errors.append(f"{html_file.relative_to(staging)}: broken {attribute}: {raw}")
    if errors:
        raise BuildError("broken local links:\n" + "\n".join(errors))


def check_data_links(paths: set[str], staging: Path) -> None:
    missing: list[str] = []
    for raw in sorted(paths):
        target = published_target(raw, staging)
        if target.is_dir():
            target = target / "index.html"
        if not target.exists():
            missing.append(raw)
    if missing:
        raise BuildError("data links missing from public bundle: " + ", ".join(missing))


def replace_output(staging: Path, output: Path) -> None:
    backup = output.with_name(f".{output.name}.previous")
    if backup.exists():
        shutil.rmtree(backup)
    if output.exists():
        output.rename(backup)
    try:
        staging.rename(output)
    except Exception:
        if backup.exists() and not output.exists():
            backup.rename(output)
        raise
    if backup.exists():
        shutil.rmtree(backup)


def build_site() -> None:
    output = DEFAULT_OUTPUT.resolve()
    run_travel("check")
    run_travel("build")
    data_paths = public_data_paths()
    tracked = tracked_paths()
    staging = Path(tempfile.mkdtemp(prefix=f".{output.name}.build-", dir=ROOT))
    try:
        for relative in CORE_FILES:
            if relative != "index.html":
                copy_file(ROOT / relative, staging, tracked)
        write_published_index(staging)
        (staging / "about.html").write_text(ABOUT_HTML, encoding="utf-8", newline="\n")
        for relative in CORE_DIRECTORIES:
            copy_public_directory(ROOT / relative, staging, tracked)
        for page_directory in sorted((ROOT / "trips").glob("*/page")):
            if page_directory.is_dir():
                copy_public_directory(page_directory, staging, tracked)
        for raw in sorted(data_paths):
            source = source_path(raw)
            if source.is_dir():
                if source.relative_to(ROOT).as_posix() not in CORE_DIRECTORIES:
                    copy_public_directory(source, staging, tracked)
            else:
                copy_file(source, staging, tracked)
        check_html_links(staging)
        check_data_links(data_paths, staging)
        replace_output(staging, output)
    except Exception:
        if staging.exists():
            shutil.rmtree(staging)
        raise


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    if argv:
        print("error: build_site.py does not accept arguments", file=sys.stderr)
        return 2
    try:
        build_site()
    except (BuildError, json.JSONDecodeError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print("Built public site: dist/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
