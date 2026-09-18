import sys
import os
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from backend.server import app

class TestRaygentAPI(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_health(self):
        res = self.client.get("/api/health")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["agent"], "Raygent")

    def test_avatars(self):
        res = self.client.get("/api/avatars")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("avatars", data)
        avatar_names = [a["name"] for a in data["avatars"]]
        self.assertIn("ray_video.mp4", avatar_names)
        self.assertIn("ray_portrait.jpeg", avatar_names)

    def test_mode_toggle(self):
        # Test getting mode
        res = self.client.get("/api/mode")
        self.assertEqual(res.status_code, 200)
        initial_mode = res.json()["mode"]

        # Test setting mode to local
        res = self.client.post("/api/mode", json={"mode": "local"})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["mode"], "local")

        # Revert back to initial
        res = self.client.post("/api/mode", json={"mode": initial_mode})
        self.assertEqual(res.status_code, 200)

if __name__ == "__main__":
    unittest.main()
