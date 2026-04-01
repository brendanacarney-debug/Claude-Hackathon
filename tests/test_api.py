from __future__ import annotations

import json
import os
import tempfile
import unittest
import importlib

from fastapi.testclient import TestClient


class ApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.runtime_dir = tempfile.TemporaryDirectory()
        os.environ["HOMERECOVER_DEMO_MODE"] = "true"
        os.environ["HOMERECOVER_RUNTIME_DIR"] = self.runtime_dir.name
        os.environ["MAX_UPLOAD_MB"] = "10"
        os.environ["CORS_ORIGINS"] = "*"

        import backend.config as config
        import backend.main as main_module

        config.get_settings.cache_clear()
        main_module = importlib.reload(main_module)

        self.client = TestClient(main_module.app)

    def tearDown(self) -> None:
        self.runtime_dir.cleanup()
        os.environ.pop("HOMERECOVER_DEMO_MODE", None)
        os.environ.pop("HOMERECOVER_RUNTIME_DIR", None)
        os.environ.pop("MAX_UPLOAD_MB", None)
        os.environ.pop("CORS_ORIGINS", None)

        import backend.config as config

        config.get_settings.cache_clear()

    def test_profiles_endpoint_returns_walker_profile(self) -> None:
        response = self.client.get("/profiles")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body[0]["profile_id"], "walker_after_fall")

    def test_demo_analysis_flow_returns_analyzed_session(self) -> None:
        create_response = self.client.post(
            "/sessions",
            json={"recovery_profile": "walker_after_fall"},
        )
        self.assertEqual(create_response.status_code, 201)
        session_id = create_response.json()["session_id"]

        upload_response = self.client.post(
            f"/sessions/{session_id}/upload",
            data={"room_types": json.dumps(["bedroom"])},
            files=[("photos", ("room.jpg", b"fake-image-bytes", "image/jpeg"))],
        )
        self.assertEqual(upload_response.status_code, 200)

        analyze_response = self.client.post(f"/sessions/{session_id}/analyze")
        self.assertEqual(analyze_response.status_code, 200)

        result_response = self.client.get(f"/sessions/{session_id}")
        self.assertEqual(result_response.status_code, 200)
        result = result_response.json()

        self.assertEqual(result["session_id"], session_id)
        self.assertEqual(result["status"], "analyzed")
        self.assertTrue(result["ghost_rearrangements"])
        self.assertTrue(
            all("room_id" in waypoint for waypoint in result["safe_path"]["waypoints"])
        )

        export_response = self.client.get(f"/sessions/{session_id}/export")
        self.assertEqual(export_response.status_code, 200)
        self.assertIn("Recovery Safety Checklist", export_response.text)
