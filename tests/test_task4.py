from __future__ import annotations

import asyncio
import json
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.analysis import DetectedObject, ImageData, RoomLayout, VisionAnalysisResult
from backend.checklist import generate_checklist
from backend.models import Room
from backend.pipeline import run_full_analysis
from backend.rules.engine import score_hazards
from backend.rules.profiles import get_profile
from backend.rules.recommendations import generate_recommendations
from backend.spatial.room_builder import build_room_model


FIXTURE_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "demo_session.json"


class _FailingClient:
    class _Messages:
        def create(self, **_: object) -> object:
            raise RuntimeError("simulated API failure")

    def __init__(self) -> None:
        self.messages = self._Messages()


class Task4Tests(unittest.TestCase):
    def setUp(self) -> None:
        fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        self.profile = get_profile("walker_after_fall")
        self.rooms = [Room.from_dict(item) for item in fixture["rooms"]]

    def test_score_hazards_matches_expected_demo_shape(self) -> None:
        hazards = score_hazards(self.rooms, self.profile, [])

        self.assertEqual(len(hazards), 5)

        by_class = {hazard.hazard_class: hazard for hazard in hazards}
        self.assertEqual(by_class["floor_obstacle"].severity, "urgent")
        self.assertIn("obj-003", by_class["floor_obstacle"].related_object_ids)

        self.assertEqual(by_class["path_obstruction"].severity, "urgent")
        self.assertIn("obj-004", by_class["path_obstruction"].related_object_ids)

        self.assertEqual(by_class["lighting_issue"].severity, "urgent")
        self.assertEqual(by_class["transfer_challenge"].severity, "moderate")
        self.assertEqual(by_class["reachability_issue"].severity, "moderate")

    def test_generate_recommendations_assigns_priority_and_fills_templates(self) -> None:
        hazards = score_hazards(self.rooms, self.profile, [])
        recommendations = generate_recommendations(hazards, self.rooms, self.profile)

        self.assertEqual(len(recommendations), len(hazards))
        self.assertEqual([item.priority for item in recommendations], [1, 2, 3, 4, 5])
        self.assertTrue(all("{" not in item.text for item in recommendations))
        self.assertTrue(all("}" not in item.text for item in recommendations))
        self.assertTrue(all(hazard.recommendation_ids for hazard in hazards))

    def test_generate_checklist_falls_back_when_api_fails(self) -> None:
        hazards = score_hazards(self.rooms, self.profile, [])
        recommendations = generate_recommendations(hazards, self.rooms, self.profile)

        checklist = asyncio.run(
            generate_checklist(
                hazards,
                recommendations,
                self.profile,
                client=_FailingClient(),
            )
        )

        self.assertGreaterEqual(len(checklist.first_night), 6)
        self.assertGreaterEqual(len(checklist.first_48_hours), 6)
        self.assertTrue(checklist.first_night[0].startswith("Remove"))

    def test_room_builder_and_rules_engine_work_together(self) -> None:
        vision_result = VisionAnalysisResult(
            room_type="bedroom",
            room_layout=RoomLayout(
                approximate_dimensions={"width": 5.0, "length": 4.0},
                door_positions=["east wall"],
                floor_type="hardwood",
                lighting_quality="adequate",
                overall_clutter_level="minimal",
            ),
            objects=[
                DetectedObject(
                    "bed",
                    "bed against left wall",
                    "against west wall",
                    {"width": 1.6, "height": 0.52, "depth": 2.0},
                    False,
                    False,
                ),
                DetectedObject(
                    "rug",
                    "loose area rug",
                    "between bed and door on floor",
                    {"width": 1.2, "height": 0.01, "depth": 0.8},
                    True,
                    True,
                ),
                DetectedObject(
                    "chair",
                    "chair blocking route",
                    "near door on likely walking path",
                    {"width": 0.6, "height": 0.85, "depth": 0.6},
                    False,
                    True,
                ),
                DetectedObject(
                    "door",
                    "bedroom door",
                    "east wall",
                    {"width": 0.9, "height": 2.1, "depth": 0.05},
                    False,
                    True,
                ),
                DetectedObject(
                    "shelf",
                    "high shelf with medications",
                    "high shelf against north wall",
                    {"width": 1.0, "height": 0.3, "depth": 0.25},
                    False,
                    False,
                ),
            ],
            observed_hazards=["chair narrows path near door", "medications stored high"],
            notes="",
        )

        room = build_room_model(vision_result)
        hazards = score_hazards([room], self.profile, vision_result.observed_hazards)

        classes = {hazard.hazard_class for hazard in hazards}
        self.assertIn("floor_obstacle", classes)
        self.assertIn("path_obstruction", classes)
        self.assertIn("reachability_issue", classes)

    def test_pipeline_uses_real_task4_modules(self) -> None:
        async def fake_analyze_room_photos(images: list[ImageData], recovery_profile: str):
            self.assertEqual(recovery_profile, "walker_after_fall")
            self.assertEqual(len(images), 3)
            return [
                VisionAnalysisResult(
                    room_type="bedroom",
                    room_layout=RoomLayout(
                        approximate_dimensions={"width": 5.0, "length": 4.0},
                        door_positions=["east wall"],
                        floor_type="hardwood",
                        lighting_quality="adequate",
                        overall_clutter_level="minimal",
                    ),
                    objects=[
                        DetectedObject(
                            "bed",
                            "bed against left wall",
                            "against west wall",
                            {"width": 1.6, "height": 0.52, "depth": 2.0},
                            False,
                            False,
                        ),
                        DetectedObject(
                            "nightstand",
                            "nightstand on far side of bed",
                            "beside bed on far side",
                            {"width": 0.45, "height": 0.58, "depth": 0.4},
                            False,
                            False,
                        ),
                        DetectedObject(
                            "rug",
                            "loose area rug",
                            "between bed and door on floor",
                            {"width": 1.2, "height": 0.01, "depth": 0.8},
                            True,
                            True,
                        ),
                        DetectedObject(
                            "chair",
                            "chair blocking route",
                            "near door on likely walking path",
                            {"width": 0.6, "height": 0.85, "depth": 0.6},
                            False,
                            True,
                        ),
                        DetectedObject(
                            "door",
                            "bedroom door",
                            "east wall",
                            {"width": 0.9, "height": 2.1, "depth": 0.05},
                            False,
                            True,
                        ),
                        DetectedObject(
                            "lamp",
                            "bedside lamp",
                            "beside bed",
                            {"width": 0.3, "height": 0.5, "depth": 0.3},
                            False,
                            False,
                        ),
                        DetectedObject(
                            "shelf",
                            "high shelf with medications",
                            "high shelf against north wall",
                            {"width": 1.0, "height": 0.3, "depth": 0.25},
                            False,
                            False,
                        ),
                    ],
                    observed_hazards=["chair narrows path near door", "medications stored high"],
                    notes="",
                ),
                VisionAnalysisResult(
                    room_type="hallway",
                    room_layout=RoomLayout(
                        approximate_dimensions={"width": 1.3, "length": 3.0},
                        door_positions=["west wall", "east wall"],
                        floor_type="hardwood",
                        lighting_quality="dark",
                        overall_clutter_level="minimal",
                    ),
                    objects=[
                        DetectedObject(
                            "door",
                            "hallway door from bedroom",
                            "west wall",
                            {"width": 0.9, "height": 2.1, "depth": 0.05},
                            False,
                            True,
                        ),
                        DetectedObject(
                            "door",
                            "hallway door to bathroom",
                            "east wall",
                            {"width": 0.9, "height": 2.1, "depth": 0.05},
                            False,
                            True,
                        ),
                    ],
                    observed_hazards=["hallway is dark with no visible light source"],
                    notes="",
                ),
                VisionAnalysisResult(
                    room_type="bathroom",
                    room_layout=RoomLayout(
                        approximate_dimensions={"width": 2.5, "length": 2.5},
                        door_positions=["west wall"],
                        floor_type="linoleum",
                        lighting_quality="adequate",
                        overall_clutter_level="minimal",
                    ),
                    objects=[
                        DetectedObject(
                            "door",
                            "bathroom door",
                            "west wall",
                            {"width": 0.9, "height": 2.1, "depth": 0.05},
                            False,
                            True,
                        ),
                        DetectedObject(
                            "toilet",
                            "toilet beside counter",
                            "against north wall",
                            {"width": 0.4, "height": 0.4, "depth": 0.65},
                            False,
                            False,
                        ),
                        DetectedObject(
                            "counter",
                            "bathroom counter beside toilet",
                            "against west wall near toilet",
                            {"width": 1.0, "height": 0.9, "depth": 0.5},
                            False,
                            False,
                        ),
                        DetectedObject(
                            "grab_bar",
                            "grab bar beside bathtub",
                            "mounted beside bathtub",
                            {"width": 0.4, "height": 0.1, "depth": 0.1},
                            False,
                            False,
                        ),
                        DetectedObject(
                            "bathtub",
                            "bathtub with non-slip mat",
                            "against east wall",
                            {"width": 0.7, "height": 0.5, "depth": 1.5},
                            False,
                            False,
                        ),
                    ],
                    observed_hazards=[],
                    notes="non-slip surface visible",
                ),
            ]

        dummy_images = [
            ImageData(b"img1", "bedroom", 1),
            ImageData(b"img2", "hallway", 2),
            ImageData(b"img3", "bathroom", 3),
        ]

        with patch("backend.pipeline.analyze_room_photos", side_effect=fake_analyze_room_photos):
            session = asyncio.run(
                run_full_analysis(
                    session_id="session-123",
                    images=dummy_images,
                    recovery_profile="walker_after_fall",
                    image_urls=["one.jpg", "two.jpg", "three.jpg"],
                )
            )

        classes = [hazard["class"] for hazard in session["hazards"]]
        self.assertIn("floor_obstacle", classes)
        self.assertIn("path_obstruction", classes)
        self.assertIn("lighting_issue", classes)
        self.assertIn("transfer_challenge", classes)
        self.assertIn("reachability_issue", classes)
        self.assertEqual(session["status"], "analyzed")
        self.assertEqual(session["images"]["originals"], ["one.jpg", "two.jpg", "three.jpg"])
        self.assertTrue(session["recommendations"])
        self.assertTrue(session["ghost_rearrangements"])
        self.assertTrue(session["checklist"]["first_night"])
        self.assertTrue(
            all("room_id" in waypoint for waypoint in session["safe_path"]["waypoints"])
        )
        self.assertIn(
            "hallway_mid",
            [waypoint["label"] for waypoint in session["safe_path"]["waypoints"]],
        )


if __name__ == "__main__":
    unittest.main()
