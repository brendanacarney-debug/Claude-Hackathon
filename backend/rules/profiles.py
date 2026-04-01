from __future__ import annotations

from backend.models import RecoveryProfile


PROFILES: dict[str, RecoveryProfile] = {
    "walker_after_fall": RecoveryProfile(
        profile_id="walker_after_fall",
        label="Walker after fall or fracture",
        constraints=[
            "no_bending",
            "needs_walker_clearance",
            "fall_risk",
            "night_bathroom_risk",
        ],
        min_path_width_m=0.9,
        hazard_weights={
            "floor_obstacle": 5,
            "path_obstruction": 5,
            "transfer_challenge": 4,
            "bathroom_risk": 5,
            "reachability_issue": 3,
            "lighting_issue": 4,
            "wound_care_issue": 2,
        },
    )
}


def get_profile(profile_id: str) -> RecoveryProfile:
    try:
        return PROFILES[profile_id]
    except KeyError as exc:
        raise KeyError(f"Unknown recovery profile: {profile_id}") from exc


def list_profiles() -> list[RecoveryProfile]:
    return list(PROFILES.values())
