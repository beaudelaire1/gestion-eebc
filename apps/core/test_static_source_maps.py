"""Regression checks for vendored static asset references."""

import re
from pathlib import Path
from urllib.parse import unquote, urlsplit

from django.conf import settings
from django.test import SimpleTestCase


SOURCE_MAP_RE = re.compile(r"sourceMappingURL=([^\s*]+)")


class StaticSourceMapReferenceTests(SimpleTestCase):
    def test_local_source_map_references_exist(self):
        """Every local sourceMappingURL referenced by JS/CSS must resolve."""
        static_root = (Path(settings.BASE_DIR) / "static").resolve()
        missing = []

        for asset in static_root.rglob("*"):
            if not asset.is_file() or asset.suffix.lower() not in {".js", ".css"}:
                continue

            content = asset.read_text(encoding="utf-8", errors="ignore")
            for raw_reference in SOURCE_MAP_RE.findall(content):
                reference = raw_reference.strip().strip('"\'')
                parsed = urlsplit(reference)

                # Remote/data source maps are not repository assets.
                if parsed.scheme or parsed.netloc:
                    continue

                relative_path = unquote(parsed.path)
                if not relative_path:
                    continue

                target = (asset.parent / relative_path).resolve()
                try:
                    target.relative_to(static_root)
                except ValueError:
                    missing.append(
                        f"{asset.relative_to(static_root)} -> {reference} (outside static root)"
                    )
                    continue

                if not target.is_file():
                    missing.append(
                        f"{asset.relative_to(static_root)} -> {reference}"
                    )

        self.assertFalse(
            missing,
            "Missing local source-map targets:\n" + "\n".join(sorted(missing)),
        )
