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


class DetalleDelNodoTest(unittest.TestCase):
    def _servicio(self, slug, node, **extra):
        base = servicio(slug, node)
        base.update(extra)
        return base

    def test_el_disco_del_reportero_llega_al_bloque_host(self):
        s = self._servicio("huachicol", "S1", host={"cores": 8})
        s["checks"]["disk"] = {"status": "ok", "used_percent": 41.3, "free_gb": 248.6}
        nodos = _agrupar_por_nodo([s])
        self.assertEqual(nodos[0]["host"]["disk_used_percent"], 41.3)
        self.assertEqual(nodos[0]["host"]["disk_free_gb"], 248.6)

    def test_el_disco_de_quien_no_reporta_no_contamina_el_nodo(self):
        s = self._servicio("acervo", "S1")
        s["checks"]["disk"] = {"status": "ok", "used_percent": 99.9, "free_gb": 1}
        nodos = _agrupar_por_nodo([s])
        self.assertNotIn("disk_used_percent", nodos[0]["host"])

    def test_los_tramos_de_cada_servicio_viajan_para_dibujar_su_barra(self):
        tramos = {"desde": "x", "celdas": 1440, "tramos": [{"min": 0, "dur": 1440, "estado": "ok"}]}
        nodos = _agrupar_por_nodo([self._servicio("mariachi", "S1", uptime_tramos=tramos)])
        self.assertEqual(nodos[0]["servicios"][0]["uptime_tramos"]["celdas"], 1440)

    def test_los_contenedores_de_todos_los_servicios_del_nodo_se_juntan(self):
        uno = self._servicio("mariachi", "S1", containers=[{"name": "mariachi-api"}])
        dos = self._servicio("acervo", "S1", containers=[{"name": "acervo-seaweedfs"}])
        nodos = _agrupar_por_nodo([uno, dos])
        self.assertEqual(
            [c["name"] for c in nodos[0]["contenedores"]],
            ["acervo-seaweedfs", "mariachi-api"],
        )

    def test_el_motivo_del_fallo_acompana_al_servicio(self):
        nodos = _agrupar_por_nodo([
            self._servicio("gateway-hub", "S1", status="down", detail="plugin_qgis (HTTP 404)"),
        ])
        self.assertEqual(nodos[0]["servicios"][0]["detail"], "plugin_qgis (HTTP 404)")
