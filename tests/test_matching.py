"""
Тесты для matching.py
"""

import sys
import pytest
import json
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from database import Database
from matching import MatchingSystem, PsychologicalTest


@pytest.fixture
def db():
    """Создает временную БД для тестов"""
    import os
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as f:
        db_path = f.name
    
    database = Database(db_path)
    yield database
    
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture
def matching_system(db):
    """Создает систему матчинга"""
    return MatchingSystem(db)


def test_calculate_match_percentage_identical(matching_system):
    """Тест расчета совместимости для идентичных векторов"""
    vector = json.dumps([1.0, 0.5, -0.3, 0.7, 0.2])
    
    percentage = matching_system.calculate_match_percentage(vector, vector)
    assert percentage == 100.0


def test_calculate_match_percentage_opposite(matching_system):
    """Тест расчета совместимости для противоположных векторов"""
    vector1 = json.dumps([1.0, 1.0, 1.0, 1.0, 1.0])
    vector2 = json.dumps([-1.0, -1.0, -1.0, -1.0, -1.0])
    
    percentage = matching_system.calculate_match_percentage(vector1, vector2)
    assert percentage == 0.0


def test_calculate_match_percentage_range(matching_system):
    """Тест что совместимость в диапазоне 0-100"""
    vector1 = json.dumps([0.5, 0.3, -0.2, 0.7, 0.1])
    vector2 = json.dumps([0.3, 0.6, 0.1, -0.4, 0.5])
    
    percentage = matching_system.calculate_match_percentage(vector1, vector2)
    assert 0.0 <= percentage <= 100.0


def test_calculate_all_matches_for_patient(db, matching_system):
    """Тест расчета всех совпадений для пациента"""
    # Создаем пациента
    db.create_user(1, 'patient1', 'patient')
    db.save_patient_profile(1, 'Тревога', '@patient1')
    db.save_test_result(1, json.dumps([0.5, 0.3, -0.2, 0.7, 0.1]))
    
    # Создаем психологов
    db.create_user(2, 'psych1', 'psychologist')
    db.save_psychologist_profile(2, 'Психолог 1', 'photo', 'МГУ', '5 лет', '@psych1')
    db.save_test_result(2, json.dumps([0.6, 0.4, -0.1, 0.6, 0.2]))
    
    db.create_user(3, 'psych2', 'psychologist')
    db.save_psychologist_profile(3, 'Психолог 2', 'photo', 'СПбГУ', '10 лет', '@psych2')
    db.save_test_result(3, json.dumps([0.3, 0.6, 0.1, -0.4, 0.5]))
    
    # Рассчитываем совпадения
    matching_system.calculate_all_matches_for_patient(1)
    
    # Проверяем что совпадения созданы
    match1 = db.get_match_percentage(1, 2)
    match2 = db.get_match_percentage(1, 3)
    
    assert match1 is not None
    assert match2 is not None
    assert 0.0 <= match1 <= 100.0
    assert 0.0 <= match2 <= 100.0


def test_psychological_test():
    """Тест психологического теста"""
    questions = [
        {
            "question": "Тестовый вопрос?",
            "options": ["A", "B", "C", "D", "E"],
            "weights": [1.0, 0.5, 0.0, -0.5, -1.0]
        }
    ]
    
    test = PsychologicalTest(questions)
    
    assert test.get_total_questions() == 1
    
    question = test.get_question(0)
    assert question is not None
    assert question['question'] == "Тестовый вопрос?"
    
    # Тест расчета вектора
    answers = {0: 0}  # Выбран первый вариант (индекс 0)
    vector_str = test.calculate_values_vector(answers)
    vector = json.loads(vector_str)
    
    assert len(vector) > 0
    assert all(-1.0 <= v <= 1.0 for v in vector)

