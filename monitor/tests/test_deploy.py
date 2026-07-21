import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.store import Store


class DeployStateTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self._tmp.name) / "test.db")

    def tearDown(self) -> None:
        self.store.close()
        self._tmp.cleanup()

    def test_sin_despliegue_inactivo(self) -> None:
        state = self.store.deploy_state()
        self.assertFalse(state["active"])
        self.assertIsNone(state["until"])

    def test_start_activa_la_ventana(self) -> None:
        self.store.start_deploy(900)
        state = self.store.deploy_state()
        self.assertTrue(state["active"])
        self.assertIsNotNone(state["until"])
        self.assertIsNotNone(state["started_at"])

    def test_end_desactiva_y_limpia(self) -> None:
        self.store.start_deploy(900)
        self.store.end_deploy()
        state = self.store.deploy_state()
        self.assertFalse(state["active"])
        self.assertIsNone(state["until"])

    def test_timeout_expira_pero_conserva_flag(self) -> None:
        self.store.start_deploy(-1)
        state = self.store.deploy_state()
        self.assertFalse(state["active"])
        self.assertIsNotNone(state["until"])


if __name__ == "__main__":
    unittest.main()
