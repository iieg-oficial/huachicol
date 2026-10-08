import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.store import Store

METRICAS = {
    "cores": 8,
    "load_1m": 1.2,
    "memory_used_percent": 41.2,
    "temperaturas": [{"nombre": "CPU", "celsius": 75}],
}


class HistorialDeHostTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self._tmp.name) / "test.db")

    def tearDown(self) -> None:
        self.store.close()
        self._tmp.cleanup()

    def _insertar(self, nodo, minutos_atras, metricas=None):
        momento = datetime.now(timezone.utc) - timedelta(minutes=minutos_atras)
        marca = momento.isoformat(timespec="seconds").replace("+00:00", "Z")
        import json
        with self.store._lock:
            self.store._conn.execute(
                "INSERT INTO host_history (nodo, medido_en, metricas) VALUES (?,?,?)",
                (nodo, marca, json.dumps(metricas or METRICAS)),
            )
            self.store._conn.commit()

    def test_la_primera_muestra_siempre_se_guarda(self) -> None:
        self.assertTrue(self.store.guardar_host("S1", METRICAS, cada_seg=300))
        self.assertEqual(len(self.store.historial_host("S1")), 1)

    def test_no_guarda_otra_antes_del_intervalo(self) -> None:
        self.store.guardar_host("S1", METRICAS, cada_seg=300)
        self.assertFalse(self.store.guardar_host("S1", METRICAS, cada_seg=300))
        self.assertEqual(len(self.store.historial_host("S1")), 1)

    def test_guarda_de_nuevo_cuando_paso_el_intervalo(self) -> None:
        self._insertar("S1", minutos_atras=10)
        self.assertTrue(self.store.guardar_host("S1", METRICAS, cada_seg=300))
        self.assertEqual(len(self.store.historial_host("S1")), 2)

    def test_cada_nodo_lleva_su_propio_ritmo(self) -> None:
        self.store.guardar_host("S1", METRICAS, cada_seg=300)
        self.assertTrue(self.store.guardar_host("S3", METRICAS, cada_seg=300))

    def test_un_nodo_sin_metricas_no_ensucia_la_tabla(self) -> None:
        self.assertFalse(self.store.guardar_host("S1", {}, cada_seg=300))
        self.assertFalse(self.store.guardar_host("", METRICAS, cada_seg=300))
        self.assertEqual(self.store.historial_host("S1"), [])

    def test_la_muestra_devuelve_sus_metricas_junto_a_la_hora(self) -> None:
        self.store.guardar_host("S1", METRICAS, cada_seg=300)
        muestra = self.store.historial_host("S1")[0]
        self.assertIn("medido_en", muestra)
        self.assertEqual(muestra["temperaturas"][0]["celsius"], 75)

    def test_lo_anterior_a_la_ventana_queda_fuera(self) -> None:
        self._insertar("S1", minutos_atras=60 * 30)
        self.assertEqual(self.store.historial_host("S1", horas=24), [])

    def test_las_muestras_salen_de_la_mas_vieja_a_la_mas_nueva(self) -> None:
        self._insertar("S1", minutos_atras=30, metricas={"load_1m": 1})
        self._insertar("S1", minutos_atras=10, metricas={"load_1m": 2})
        cargas = [m["load_1m"] for m in self.store.historial_host("S1")]
        self.assertEqual(cargas, [1, 2])

    def test_la_purga_tambien_limpia_el_historial_de_host(self) -> None:
        self._insertar("S1", minutos_atras=60 * 24 * 40)
        self.store.prune(retention_days=30)
        self.assertEqual(self.store.historial_host("S1", horas=168), [])


if __name__ == "__main__":
    unittest.main()
