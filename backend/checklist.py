from __future__ import annotations

import inspect
import json
import os
from typing import Any

from backend.models import Checklist, Hazard, Recommendation, RecoveryProfile, coerce_hazards, coerce_profile, coerce_recommendations


FALLBACK_CHECKLISTS: dict[str, Checklist] = {
    "walker_after_fall": Checklist(
        first_night=[
            "Remove all loose rugs from the path between bed and bathroom.",
            "Clear the walking path of any furniture, shoes, cords, or clutter.",
            "Place the walker within arm's reach of the bed.",
            "Put a night light in the hallway and bathroom.",
            "Move water, phone, charger, and other daily essentials to the nightstand.",
            "Make sure all doors on the bathroom route open fully and stay open.",
            "Place a non-slip mat in the bathroom if the floor gets slippery.",
            "Test that the patient can reach light controls before standing up.",
        ],
        first_48_hours=[
            "Install or arrange a grab bar near the toilet or shower area.",
            "Practice the bed-to-bathroom route together during daytime.",
            "Route all cords along walls instead of across walking paths.",
            "Check whether bed height feels safe for sit-to-stand transfers.",
            "Set up a bedside caddy with daily essentials in one place.",
            "Confirm the patient can reach the phone or call device from bed at night.",
        ],
    )
}


async def generate_checklist(
    hazards: list[Hazard] | list[dict],
    recommendations: list[Recommendation] | list[dict],
    profile: RecoveryProfile | dict,
    *,
    client: Any | None = None,
    model: str = "claude-sonnet-4-6",
) -> Checklist:
    hazard_models = coerce_hazards(hazards)
    recommendation_models = coerce_recommendations(recommendations)
    profile_model = coerce_profile(profile)

    if client is None:
        client = _build_default_client()
    if client is None:
        return _fallback_checklist(profile_model)

    prompt = _build_prompt(hazard_models, recommendation_models, profile_model)

    try:
        message_result = client.messages.create(
            model=model,
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}],
        )
        if inspect.isawaitable(message_result):
            message_result = await message_result

        response_text = _extract_response_text(message_result)
        payload = json.loads(_strip_code_fences(response_text))
        return Checklist(
            first_night=[str(item) for item in payload["first_night"]],
            first_48_hours=[str(item) for item in payload["first_48_hours"]],
        )
    except Exception:
        return _fallback_checklist(profile_model)


def _build_prompt(
    hazards: list[Hazard],
    recommendations: list[Recommendation],
    profile: RecoveryProfile,
) -> str:
    hazard_summary = "\n".join(
        f"- [{hazard.severity.upper()}] {hazard.explanation}" for hazard in hazards
    )
    rec_summary = "\n".join(
        f"- Priority {recommendation.priority}: {recommendation.text}"
        for recommendation in recommendations
    )

    return f"""You are a home safety advisor helping a caregiver prepare their home for a patient coming home from the hospital.

Patient profile: {profile.label}
Constraints: {", ".join(profile.constraints)}

Detected hazards:
{hazard_summary}

Recommendations:
{rec_summary}

Create two checklists:

1. FIRST NIGHT CHECKLIST: Things that must be done before the patient sleeps at home tonight. These should be quick, doable actions that each take 15 minutes or less. Focus on removing immediate dangers and setting up essentials within reach.

2. FIRST 48 HOURS CHECKLIST: Things to do within the first two days. These can be slightly more involved, like buying a night light, rearranging furniture, or discussing equipment with the care team.

Rules:
- Write in plain, direct language a stressed caregiver can follow.
- Each item should be one concrete action, not a vague suggestion.
- Do not use medical jargon.
- Do not give medical advice or mention specific medications.
- Include 6 to 10 items in each checklist.
- Start each item with an action verb such as Remove, Move, Place, Check, or Install.

Respond in this exact JSON format:
{{
  "first_night": ["item1", "item2"],
  "first_48_hours": ["item1", "item2"]
}}"""


def _build_default_client() -> Any | None:
    if not os.getenv("ANTHROPIC_API_KEY"):
        return None

    try:
        from anthropic import AsyncAnthropic
    except Exception:
        return None

    return AsyncAnthropic(api_key=os.environ["ANTHROPIC_API_KEY"])


def _extract_response_text(message_result: Any) -> str:
    content = getattr(message_result, "content", None)
    if content is None:
        raise ValueError("Claude response did not contain content.")

    parts: list[str] = []
    for item in content:
        if hasattr(item, "text"):
            parts.append(str(item.text))
        elif isinstance(item, dict) and "text" in item:
            parts.append(str(item["text"]))
    if not parts:
        raise ValueError("Claude response did not include any text blocks.")
    return "\n".join(parts).strip()


def _strip_code_fences(text: str) -> str:
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped

    lines = stripped.splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].startswith("```"):
        lines = lines[:-1]
    if lines and lines[0].strip().lower() == "json":
        lines = lines[1:]
    return "\n".join(lines).strip()


def _fallback_checklist(profile: RecoveryProfile) -> Checklist:
    template = FALLBACK_CHECKLISTS.get(profile.profile_id)
    if template is not None:
        return Checklist(
            first_night=list(template.first_night),
            first_48_hours=list(template.first_48_hours),
        )

    return Checklist(
        first_night=[
            "Clear the main walking path before tonight.",
            "Place essential items within arm's reach of the bed.",
            "Improve lighting on the route to the bathroom.",
        ],
        first_48_hours=[
            "Review any remaining trip hazards and remove them.",
            "Rearrange furniture to improve walking clearance.",
            "Discuss home safety concerns with the care team if needed.",
        ],
    )
