import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.alerting import (
    KIND_DEPLOYED,
    KIND_DOWN,
    KIND_RECOVERED,
    KIND_REMINDER,
    evaluate,
)
from app.config import Config, Target
from app.probes import ProbeResult


def _config(**overrides) -> Config:
    base = {
        "targets": [Target(slug="svc", label="Servicio", url="http://x/ontoy")],
        "failure_threshold": 3,
        "recovery_threshold": 1,
        "reminder_hours": 0,
    }
    base.update(overrides)
    return Config(**base)


def _result(status: str, version: str | None = "1.0.0") -> ProbeResult:
    return ProbeResult(slug="svc", label="Servicio", status=status, version=version)


class HysteresisTest(unittest.TestCase):
    def test_no_alerta_antes_del_umbral(self):
        config = _config()
        state, event = evaluate(_result("unreachable"), None, config)
        self.assertIsNone(event)
        self.assertEqual(state["consecutive_failures"], 1)

        state, event = evaluate(_result("unreachable"), state, config)
        self.assertIsNone(event)
        self.assertEqual(state["consecutive_failures"], 2)

    def test_alerta_exactamente_en_el_umbral(self):
        config = _config()
        state = None
        for _ in range(2):
            state, event = evaluate(_result("unreachable"), state, config)
            self.assertIsNone(event)

        state, event = evaluate(_result("unreachable"), state, config)
        self.assertIsNotNone(event)
        self.assertEqual(event.kind, KIND_DOWN)
        self.assertTrue(state["alerted"])

    def test_no_repite_la_alerta_en_ciclos_siguientes(self):
        config = _config()
        state = None
        for _ in range(3):
            state, event = evaluate(_result("unreachable"), state, config)

        for _ in range(10):
            state, event = evaluate(_result("unreachable"), state, config)
            self.assertIsNone(event, "no debe re-alertar mientras siga caido")

    def test_fallo_intermitente_no_alerta(self):
        config = _config()
        state = None
        for status in ("unreachable", "unreachable", "ok", "unreachable", "ok"):
            state, event = evaluate(_result(status), state, config)
            self.assertIsNone(event)

    def test_recuperacion_notifica_una_vez(self):
        config = _config()
        state = None
        for _ in range(3):
            state, event = evaluate(_result("down"), state, config)
        self.assertEqual(event.kind, KIND_DOWN)

        state, event = evaluate(_result("ok"), state, config)
        self.assertEqual(event.kind, KIND_RECOVERED)
        self.assertFalse(state["alerted"])

        state, event = evaluate(_result("ok"), state, config)
        self.assertIsNone(event)

    def test_degraded_cuenta_como_fallo(self):
        config = _config()
        state = None
        for _ in range(3):
            state, event = evaluate(_result("degraded"), state, config)
        self.assertIsNotNone(event)
        self.assertEqual(event.status, "degraded")

    def test_cambio_de_version_genera_evento_de_despliegue(self):
        config = _config()
        state, _ = evaluate(_result("ok", "1.0.0"), None, config)
        state, event = evaluate(_result("ok", "1.1.0"), state, config)
        self.assertEqual(event.kind, KIND_DEPLOYED)
        self.assertEqual(event.previous_version, "1.0.0")
        self.assertEqual(event.version, "1.1.0")

    def test_primera_observacion_no_reporta_despliegue(self):
        config = _config()
        _, event = evaluate(_result("ok", "1.0.0"), None, config)
        self.assertIsNone(event)

    def test_recordatorio_desactivado_por_defecto(self):
        config = _config()
        state = None
        for _ in range(3):
            state, event = evaluate(_result("down"), state, config)
        for _ in range(20):
            state, event = evaluate(_result("down"), state, config)
            self.assertIsNone(event)

    def test_umbral_de_uno_alerta_inmediato(self):
        config = _config(failure_threshold=1)
        _, event = evaluate(_result("unreachable"), None, config)
        self.assertIsNotNone(event)
        self.assertEqual(event.kind, KIND_DOWN)

    def test_since_se_conserva_mientras_el_estado_no_cambia(self):
        config = _config()
        previo = {
            "status": "ok",
            "version": "1.0.0",
            "alerted": False,
            "consecutive_failures": 0,
            "consecutive_successes": 5,
            "since": "2020-01-01T00:00:00Z",
            "alerted_at": None,
        }
        state, _ = evaluate(_result("ok"), previo, config)
        self.assertEqual(state["since"], "2020-01-01T00:00:00Z")

    def test_since_se_reinicia_al_cambiar_de_estado(self):
        config = _config()
        previo = {
            "status": "ok",
            "version": "1.0.0",
            "alerted": False,
            "consecutive_failures": 0,
            "consecutive_successes": 5,
            "since": "2020-01-01T00:00:00Z",
            "alerted_at": None,
        }
        state, _ = evaluate(_result("down"), previo, config)
        self.assertNotEqual(state["since"], "2020-01-01T00:00:00Z")
        self.assertTrue(state["since"].startswith("20"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
