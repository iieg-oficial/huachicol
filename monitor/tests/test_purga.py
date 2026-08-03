import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.store import Store


class DropUnknownTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self._tmp.name) / "test.db")
        for slug in ("sextante", "geoserver"):
            self._guardar(slug)

    def tearDown(self) -> None:
        self.store.close()
        self._tmp.cleanup()

    def _guardar(self, slug: str) -> None:
        self.store.save_state(
            slug=slug,
            label=slug.title(),
            status="ok",
            version="1.0.0",
            deployed_at=None,
            detail=None,
            checks={},
            containers=[],
            latency_ms=10,
            consecutive_failures=0,
            consecutive_successes=1,
            since="2026-07-31T14:00:00Z",
            alerted=False,
            alerted_at=None,
        )
        self.store.record_check(slug, "ok", 10, None)
        self.store.record_event(slug, "recovered", "down", "ok", None, True)

    def test_borra_el_slug_que_ya_no_esta_en_targets(self) -> None:
        obsoletos = self.store.drop_unknown(["sextante"])
        self.assertEqual(obsoletos, ["geoserver"])
        self.assertIsNone(self.store.get_state("geoserver"))
        self.assertIsNotNone(self.store.get_state("sextante"))

    def test_arrastra_historial_y_eventos(self) -> None:
        self.store.drop_unknown(["sextante"])
        self.assertEqual(self.store.history("geoserver"), [])
        slugs = [e["slug"] for e in self.store.recent_events()]
        self.assertNotIn("geoserver", slugs)
        self.assertIn("sextante", slugs)

    def test_sin_obsoletos_no_toca_nada(self) -> None:
        obsoletos = self.store.drop_unknown(["sextante", "geoserver"])
        self.assertEqual(obsoletos, [])
        self.assertEqual(len(self.store.all_states()), 2)

    def test_lista_vacia_no_borra(self) -> None:
        self.assertEqual(self.store.drop_unknown([]), [])
        self.assertEqual(len(self.store.all_states()), 2)


if __name__ == "__main__":
    unittest.main()
