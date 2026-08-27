import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.api import _agrupar_por_nodo


def servicio(slug, node, status="ok", host=None, peers=None, containers=(2, 2)):
    checks = {"disk": {"status": "ok"}}
    for nombre, valor in (peers or {}).items():
        checks[f"peer_{nombre}"] = valor
    corriendo, total = containers
    return {
        "slug": slug,
        "label": slug,
        "status": status,
        "version": "1.0.0",
        "uptime_24h": 100,
        "node": node,
        "host": host or {},
        "checks": checks,
        "container_summary": {"total": total, "running": corriendo},
    }


class AgruparPorNodoTest(unittest.TestCase):
    def test_los_servicios_de_un_nodo_caen_en_una_sola_tarjeta(self):
        nodos = _agrupar_por_nodo([
            servicio("mariachi", "S1"),
            servicio("acervo", "S1"),
            servicio("mapalab", "S2"),
        ])
        self.assertEqual([n["node"] for n in nodos], ["S1", "S2"])
        self.assertEqual([s["slug"] for s in nodos[0]["servicios"]], ["acervo", "mariachi"])

    def test_los_contenedores_del_nodo_se_suman(self):
        nodos = _agrupar_por_nodo([
            servicio("mariachi", "S1", containers=(5, 5)),
            servicio("acervo", "S1", containers=(2, 3)),
        ])
        self.assertEqual(nodos[0]["containers"], {"total": 8, "running": 7})

    def test_las_metricas_de_host_las_pone_el_reportero(self):
        nodos = _agrupar_por_nodo([
            servicio("mariachi", "S1"),
            servicio("huachicol", "S1", host={"memory_used_percent": 41.2, "cores": 8}),
        ])
        self.assertEqual(nodos[0]["host"]["memory_used_percent"], 41.2)

    def test_un_servicio_caido_tumba_el_nodo(self):
        nodos = _agrupar_por_nodo([
            servicio("mariachi", "S1"),
            servicio("acervo", "S1", status="down"),
        ])
        self.assertEqual(nodos[0]["status"], "down")

    def test_un_servicio_degradado_deja_el_nodo_degradado(self):
        nodos = _agrupar_por_nodo([servicio("mapalab", "S2", status="degraded")])
        self.assertEqual(nodos[0]["status"], "degraded")

    def test_las_aristas_se_cuelgan_del_nodo_sin_el_prefijo(self):
        nodos = _agrupar_por_nodo([
            servicio("mariachi", "S1", peers={"S4": {"status": "ok", "latency_ms": 6}}),
        ])
        self.assertEqual(nodos[0]["peers"]["S4"]["latency_ms"], 6)

    def test_quien_no_declara_nodo_no_se_pierde(self):
        nodos = _agrupar_por_nodo([servicio("vine", None)])
        self.assertEqual(nodos[0]["node"], "sin-nodo")


if __name__ == "__main__":
    unittest.main()
