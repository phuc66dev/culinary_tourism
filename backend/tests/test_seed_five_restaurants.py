"""Regression tests for the five District 4 sample POIs (no database required)."""
import ast
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_FILE = ROOT / "data" / "seed" / "sample_pois_quan4.json"
SEED_SCRIPT = ROOT / "backend" / "scripts" / "seed_pois.py"
EXPECTED = {
    "nem-nuong-nia": "Nem Nướng Nia",
    "pho-mui-241": "Quán Phở Mùi 241",
    "pha-lau-bo-co-thao": "Phá Lấu Bò Cô Thảo",
    "oc-thao-vinh-khanh": "Quán Ốc Thảo",
    "dua-tac-co-ut": "Dừa Tắc Cô Út",
}


class TestFiveRestaurantSeed(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.items = json.loads(DATA_FILE.read_text(encoding="utf-8"))

    def test_exactly_five_requested_restaurants(self):
        self.assertEqual(len(self.items), 5)
        self.assertEqual({i["slug"]: i["name"] for i in self.items}, EXPECTED)

    def test_geojson_and_wards(self):
        for item in self.items:
            with self.subTest(poi=item["slug"]):
                loc = item["location"]
                self.assertEqual(loc["type"], "Point")
                self.assertEqual(len(loc["coordinates"]), 2)
                lng, lat = loc["coordinates"]
                self.assertTrue(106.69 < lng < 106.72)
                self.assertTrue(10.74 < lat < 10.78)
                self.assertTrue(item["ward"].startswith("Phường "))
                self.assertEqual(item["trigger_radius"], 30)

    def test_vi_and_en_localizations_are_ready_to_generate_audio(self):
        for item in self.items:
            with self.subTest(poi=item["slug"]):
                self.assertEqual(set(item["localizations"]), {"vi", "en"})
                self.assertEqual(item["localizations"]["vi"]["description"], item["original_description"])
                self.assertTrue(item["localizations"]["en"]["title"].strip())
                self.assertTrue(item["localizations"]["en"]["description"].strip())
                self.assertFalse(item["is_active"])  # Activation Gate requires completed EN MP3
                self.assertEqual(item["images"], [])  # No falsely attributed images

    def test_demo_owner_reassigned_and_script_compiles(self):
        script = SEED_SCRIPT.read_text(encoding="utf-8")
        ast.parse(script, filename=str(SEED_SCRIPT))
        self.assertIn('OWNER_DEMO_POI_SLUG = "nem-nuong-nia"', script)
        self.assertIn('"source_hash": fingerprint', script)


if __name__ == "__main__":
    unittest.main()
