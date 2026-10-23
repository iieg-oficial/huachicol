import io
import json
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import Target, load_targets
from app.probes import probe


def respuesta(payload):
    cuerpo = io.BytesIO(json.dumps(payload).encode())
    contexto = mock.MagicMock()
    contexto.__enter__.return_value = cuerpo
    return contexto


class NodoDelTargetTest(unittest.TestCase):
    def test_un_ontoy_sin_node_toma_el_del_target(self):
        target = Target(slug="mariachi", label="Mariachi", url="http://x/ontoy", node="S1")
        with mock.patch("urllib.request.urlopen", return_value=respuesta({"status": "ok"})):
            self.assertEqual(probe(target).node, "S1")

    def test_el_node_del_ontoy_gana_al_del_target(self):
        target = Target(slug="mapalab", label="MapaLab", url="http://x/ontoy", node="S1")
        payload = {"status": "ok", "node": "S2"}
        with mock.patch("urllib.request.urlopen", return_value=respuesta(payload)):
            self.assertEqual(probe(target).node, "S2")

    def test_un_servicio_inalcanzable_se_queda_en_su_nodo(self):
        target = Target(slug="minerva", label="Minerva", url="http://x/ontoy", node="forja")
        fallo = urllib.error.URLError("timed out")
        with mock.patch("urllib.request.urlopen", side_effect=fallo):
            resultado = probe(target)
        self.assertEqual(resultado.status, "unreachable")
        self.assertEqual(resultado.node, "forja")

    def test_sin_node_en_ningun_lado_queda_vacio(self):
        target = Target(slug="sieej", label="SIEEJ", url="http://x/ontoy")
        with mock.patch("urllib.request.urlopen", return_value=respuesta({"status": "ok"})):
            self.assertIsNone(probe(target).node)


class CargaDeTargetsTest(unittest.TestCase):
    def test_el_node_se_lee_y_uno_en_blanco_cuenta_como_ausente(self):
        with tempfile.TemporaryDirectory() as tmp:
            ruta = Path(tmp) / "targets.json"
            ruta.write_text(json.dumps([
                {"slug": "mariachi", "url": "http://x/ontoy", "node": " S1 "},
                {"slug": "sieej", "url": "http://y/ontoy", "node": ""},
            ]))
            targets = load_targets(ruta)
        self.assertEqual([t.node for t in targets], ["S1", None])


if __name__ == "__main__":
    unittest.main()
