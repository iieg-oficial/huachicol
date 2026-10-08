import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.store import Store


class UptimeTramosTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self._tmp.name) / "test.db")
        self.ahora = datetime.now(timezone.utc).replace(second=0, microsecond=0)

    def tearDown(self) -> None:
        self.store.close()
        self._tmp.cleanup()

    def _sondeo(self, minutos_atras: int, status: str, detail: str | None = None) -> None:
        momento = self.ahora - timedelta(minutes=minutos_atras)
        marca = momento.isoformat(timespec="seconds").replace("+00:00", "Z")
        with self.store._lock:
            self.store._conn.execute(
                "INSERT INTO check_history (slug, checked_at, status, latency_ms, detail)"
                " VALUES (?,?,?,?,?)",
                ("gateway-hub", marca, status, 40, detail),
            )
            self.store._conn.commit()

    def test_sin_lecturas_es_un_solo_tramo_sin_datos(self) -> None:
        resultado = self.store.uptime_tramos("gateway-hub")
        self.assertEqual(len(resultado["tramos"]), 1)
        self.assertEqual(resultado["tramos"][0]["estado"], "sin_datos")
        self.assertEqual(resultado["tramos"][0]["dur"], 1440)
        self.assertEqual(resultado["celdas"], 1440)

    def test_lecturas_consecutivas_iguales_se_comprimen(self) -> None:
        for minutos in range(1, 11):
            self._sondeo(minutos, "ok")
        tramos = self.store.uptime_tramos("gateway-hub")["tramos"]
        self.assertEqual([t["estado"] for t in tramos], ["sin_datos", "ok"])
        self.assertEqual(tramos[1]["dur"], 10)

    def test_una_caida_corta_conserva_su_duracion(self) -> None:
        for minutos in range(1, 21):
            status = "down" if 10 <= minutos < 14 else "ok"
            detalle = "plugin_qgis · HTTP 404" if status == "down" else None
            self._sondeo(minutos, status, detalle)
        tramos = self.store.uptime_tramos("gateway-hub")["tramos"]
        caidas = [t for t in tramos if t["estado"] == "down"]
        self.assertEqual(len(caidas), 1)
        self.assertEqual(caidas[0]["dur"], 4)
        self.assertEqual(caidas[0]["detalle"], "plugin_qgis · HTTP 404")

    def test_los_tramos_cubren_la_ventana_completa_y_no_se_enciman(self) -> None:
        for minutos in range(1, 60):
            self._sondeo(minutos, "degraded" if minutos % 2 else "ok")
        resultado = self.store.uptime_tramos("gateway-hub")
        esperado = 0
        for tramo in resultado["tramos"]:
            self.assertEqual(tramo["min"], esperado)
            esperado += tramo["dur"]
        self.assertEqual(esperado, resultado["celdas"])

    def test_la_resolucion_cambia_el_numero_de_celdas(self) -> None:
        resultado = self.store.uptime_tramos("gateway-hub", resolucion_seg=600)
        self.assertEqual(resultado["celdas"], 144)
        self.assertEqual(resultado["resolucion_seg"], 600)

    def test_lo_anterior_a_la_ventana_queda_fuera(self) -> None:
        self._sondeo(2000, "down")
        estados = [t["estado"] for t in self.store.uptime_tramos("gateway-hub")["tramos"]]
        self.assertEqual(estados, ["sin_datos"])


if __name__ == "__main__":
    unittest.main()
