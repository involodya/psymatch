from __future__ import annotations

from collections import defaultdict
from typing import Dict, Iterable, Tuple

from .db import Database, User
from .resources import load_questions


ROLE_TO_SECTION = {
    "patient": "patients",
    "psychologist": "psychologists",
}


def _normalize(value: int, min_value: int, max_value: int) -> float:
    value = max(min_value, min(value, max_value))
    if max_value == min_value:
        return 0.0
    return (value - min_value) / (max_value - min_value)


def aggregate_traits(audience: str, answers: Dict[str, int]) -> Tuple[Dict[str, float], Iterable[tuple[str, int]]]:
    data = load_questions()
    section_name = ROLE_TO_SECTION[audience]
    questions = {q["id"]: q for q in data[section_name]}
    scale = data.get("scale", {"min": 1, "max": 5})
    min_scale = int(scale.get("min", 1))
    max_scale = int(scale.get("max", 5))

    totals = defaultdict(float)
    weights = defaultdict(float)

    for question_id, answer in answers.items():
        question = questions.get(question_id)
        if not question:
            continue
        normalized = _normalize(answer, min_scale, max_scale)
        for trait, weight in question["traits"].items():
            totals[trait] += normalized * float(weight)
            weights[trait] += float(weight)

    traits = {
        trait: totals[trait] / weights[trait]
        for trait in totals
        if weights[trait] > 0
    }

    ordered_answers = tuple((qid, answers[qid]) for qid in answers if qid in questions)
    return traits, ordered_answers


def compatibility(patient_traits: Dict[str, float], psychologist_traits: Dict[str, float]) -> float:
    if not patient_traits or not psychologist_traits:
        return 0.0

    all_traits = set(patient_traits) | set(psychologist_traits)
    if not all_traits:
        return 0.0

    total = 0.0
    for trait in all_traits:
        p_val = patient_traits.get(trait, 0.5)
        s_val = psychologist_traits.get(trait, 0.5)
        diff = abs(p_val - s_val)
        score = 1.0 - min(diff, 1.0)
        total += score

    return round((total / len(all_traits)) * 100, 2)


def _get_completed_user(db: Database, user_id: int) -> User | None:
    user = db.get_user(user_id)
    if not user or not user.test_completed:
        return None
    return user


def recalc_for_patient(db: Database, patient_id: int) -> None:
    patient = _get_completed_user(db, patient_id)
    if not patient:
        return

    for row in db.list_psychologists():
        psychologist = db._row_to_user(row)  # type: ignore[attr-defined]
        if not psychologist.test_completed:
            continue
        score = compatibility(patient.traits, psychologist.traits)
        db.upsert_match_score(patient.id, psychologist.id, score)


def recalc_for_psychologist(db: Database, psychologist_id: int) -> None:
    psychologist = _get_completed_user(db, psychologist_id)
    if not psychologist:
        return

    for row in db.list_patients():
        patient = db._row_to_user(row)  # type: ignore[attr-defined]
        if not patient.test_completed:
            continue
        score = compatibility(patient.traits, psychologist.traits)
        db.upsert_match_score(patient.id, psychologist.id, score)

