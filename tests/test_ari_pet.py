from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
PET = ROOT / "pets" / "ari"
ROW_FRAMES = {
    "idle": (0, 6),
    "running-right": (1, 8),
    "running-left": (2, 8),
    "waving": (3, 4),
    "jumping": (4, 5),
    "failed": (5, 8),
    "waiting": (6, 6),
    "running": (7, 6),
    "review": (8, 6),
}


class AriPetTests(unittest.TestCase):
    def test_manifest_and_sprite_contract(self):
        spec = json.loads((PET / "pet.json").read_text(encoding="utf-8"))
        self.assertEqual(spec["id"], "ari")
        self.assertEqual(spec["spriteVersionNumber"], 2)
        self.assertEqual(spec["spritesheetPath"], "spritesheet.webp")

        raw = (PET / spec["spritesheetPath"]).read_bytes()
        self.assertEqual(raw[:4], b"RIFF")
        self.assertEqual(raw[8:12], b"WEBP")
        self.assertEqual(int.from_bytes(raw[4:8], "little") + 8, len(raw))
        offset = raw.find(b"VP8L")
        self.assertNotEqual(offset, -1, "Expected lossless RGBA WebP")
        self.assertEqual(raw[offset + 8], 0x2F)
        dimensions = int.from_bytes(raw[offset + 9:offset + 13], "little")
        width = (dimensions & 0x3FFF) + 1
        height = ((dimensions >> 14) & 0x3FFF) + 1
        self.assertEqual((width, height), (1536, 2288))

        for name, (row, count) in ROW_FRAMES.items():
            with self.subTest(state=name):
                animation = spec["animations"][name]
                self.assertTrue(animation["frames"])
                self.assertTrue(set(animation["frames"]) <= set(range(row * 8, row * 8 + count)))
                self.assertGreater(animation["fps"], 0)
                self.assertEqual(animation["fallback"], "idle")

    def test_installer_discovers_ari(self):
        import sys
        sys.path.insert(0, str(ROOT / "scripts"))
        import install_codex
        self.assertIn("ari", install_codex.discover_pets(ROOT))


if __name__ == "__main__":
    unittest.main()
