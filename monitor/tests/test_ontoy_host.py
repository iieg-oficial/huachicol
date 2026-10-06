import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "version-api"))

MEMINFO = """MemTotal:       16000000 kB
MemFree:         2000000 kB
MemAvailable:    4000000 kB
SwapTotal:       4000000 kB
SwapFree:        3600000 kB
"""


class MetricasDeHostTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.proc = Path(self._tmp.name)
        (self.proc / "loadavg").write_text("0.80 0.60 0.45 1/900 12345\n")
        (self.proc / "meminfo").write_text(MEMINFO)
        (self.proc / "uptime").write_text("259827.42 1000000.00\n")

        os.environ["ONTOY_PROC_PATH"] = str(self.proc)
        for modulo in list(sys.modules):
            if modulo == "ontoy_server":
                del sys.modules[modulo]
        import ontoy_server
        self.mod = ontoy_server

    def tearDown(self) -> None:
        os.environ.pop("ONTOY_PROC_PATH", None)
        self._tmp.cleanup()

    def test_la_carga_se_mide_por_nucleo(self) -> None:
        carga = self.mod._check_carga()
        self.assertEqual(carga["load_1m"], 0.8)
        self.assertEqual(carga["load_15m"], 0.45)
        self.assertEqual(carga["cores"], self.mod._cpu_cores())

    def test_la_memoria_usa_available_y_no_free(self) -> None:
        memoria = self.mod._check_memoria()
        self.assertEqual(memoria["total_gb"], 15.26)
        self.assertEqual(memoria["used_percent"], 75.0)

    def test_el_swap_por_encima_del_umbral_queda_degradado(self) -> None:
        swap = self.mod._check_swap()
        self.assertEqual(swap["used_percent"], 10.0)
        self.assertEqual(swap["status"], "degraded")

    def test_el_uptime_llega_en_segundos_enteros(self) -> None:
        self.assertEqual(self.mod._uptime_segundos(), 259827)

    def test_sin_proc_las_metricas_se_omiten_en_vez_de_reventar(self) -> None:
        self.mod.PROC_PATH = Path("/no/existe")
        self.assertIsNone(self.mod._check_carga())
        self.assertIsNone(self.mod._check_memoria())
        self.assertIsNone(self.mod._uptime_segundos())

    def test_un_host_sufriendo_no_tumba_el_estado_del_servicio(self) -> None:
        checks = {
            "disk": {"status": "ok"},
            "containers": {"status": "ok"},
            "memoria": {"status": "down"},
            "swap": {"status": "degraded"},
            "peer_S4": {"status": "down"},
        }
        self.assertEqual(self.mod._worst(self.mod._criticos(checks)), "ok")

    def test_un_check_critico_si_lo_tumba(self) -> None:
        checks = {"disk": {"status": "down"}, "memoria": {"status": "ok"}}
        self.assertEqual(self.mod._worst(self.mod._criticos(checks)), "down")

    def test_los_informativos_quedan_marcados_en_la_respuesta(self) -> None:
        checks = {"disk": {"status": "ok"}, "swap": {"status": "ok"}, "peer_S2": {"status": "ok"}}
        self.mod._marcar_informativos(checks)
        self.assertNotIn("informativo", checks["disk"])
        self.assertTrue(checks["swap"]["informativo"])
        self.assertTrue(checks["peer_S2"]["informativo"])

    def test_las_aristas_se_leen_del_entorno(self) -> None:
        os.environ["ONTOY_PEER_CHECKS"] = "S2=10.0.0.2:8088, S4=10.0.0.4:6432 ,roto"
        try:
            self.assertEqual(
                self.mod._parse_peer_checks(),
                [("S2", "10.0.0.2", 8088), ("S4", "10.0.0.4", 6432)],
            )
        finally:
            os.environ.pop("ONTOY_PEER_CHECKS")


if __name__ == "__main__":
    unittest.main()
