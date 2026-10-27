"""Guard the files Home Assistant Supervisor uses to present app updates."""

import os
import re
import struct
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ADDON_PATH = "addon/viesmann_dashboard"
ADDON = ROOT / ADDON_PATH


def version_from(config):
    return re.search(r'^version: "(\d+\.\d+\.\d+)"$', config, re.MULTILINE).group(1)


class ReleaseMetadataTests(unittest.TestCase):
    def test_current_version_has_nonempty_latest_release_notes(self):
        version = version_from((ADDON / "config.yaml").read_text(encoding="utf-8"))
        changelog = (ADDON / "CHANGELOG.md").read_text(encoding="utf-8")
        sections = re.split(r"^## ", changelog, flags=re.MULTILINE)
        heading, _, notes = sections[1].partition("\n")
        self.assertEqual(heading.strip(), version)
        self.assertRegex(notes, r"(?m)^- \S.+", "The latest release needs user-visible changes")

    def test_supervisor_branding_is_square_png(self):
        for filename, expected_size in [("icon.png", 128), ("logo.png", 256)]:
            with self.subTest(filename=filename):
                data = (ADDON / filename).read_bytes()
                self.assertEqual(data[:8], b"\x89PNG\r\n\x1a\n")
                self.assertEqual(struct.unpack(">II", data[16:24]), (expected_size, expected_size))

    @unittest.skipUnless(os.getenv("RELEASE_BASE_REF"), "Set RELEASE_BASE_REF to compare a release against its base")
    def test_app_changes_advance_version_and_update_changelog(self):
        base = os.environ["RELEASE_BASE_REF"]
        if set(base) == {"0"}:
            self.skipTest("Initial repository push has no previous release")

        def git(*args):
            return subprocess.check_output(["git", *args], cwd=ROOT, text=True, encoding="utf-8")

        changed = git("diff", "--name-only", base, "HEAD", "--", ADDON_PATH).splitlines()
        if not changed:
            self.skipTest("No app changes in this revision")
        old_version = version_from(git("show", f"{base}:{ADDON_PATH}/config.yaml"))
        version = version_from((ADDON / "config.yaml").read_text(encoding="utf-8"))
        self.assertGreater(tuple(map(int, version.split("."))), tuple(map(int, old_version.split("."))),
                           "App changes need a new image version so Home Assistant can offer the update")
        self.assertIn(f"{ADDON_PATH}/CHANGELOG.md", changed,
                      "App changes need release notes visible in Home Assistant")


if __name__ == "__main__":
    unittest.main()
