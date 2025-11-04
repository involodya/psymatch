"""
Тесты для database.py
"""

import os
import sys
import pytest
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from database import Database


@pytest.fixture
def db():
    """Создает временную БД для тестов"""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as f:
        db_path = f.name
    
    database = Database(db_path)
    yield database
    
    # Cleanup
    if os.path.exists(db_path):
        os.unlink(db_path)


def test_create_user(db):
    """Тест создания пользователя"""
    db.create_user(1, 'testuser', 'patient')
    user = db.get_user(1)
    
    assert user is not None
    assert user['user_id'] == 1
    assert user['username'] == 'testuser'
    assert user['user_type'] == 'patient'


def test_save_patient_profile(db):
    """Тест сохранения профиля пациента"""
    db.create_user(1, 'patient1', 'patient')
    db.save_patient_profile(1, 'Тревога', '@patient1')
    
    profile = db.get_patient_info(1)
    assert profile is not None
    assert profile['main_request'] == 'Тревога'
    assert profile['contact'] == '@patient1'


def test_save_psychologist_profile(db):
    """Тест сохранения профиля психолога"""
    db.create_user(1, 'psych1', 'psychologist')
    db.save_psychologist_profile(
        1, 'Иван Иванов', 'photo_id', 'МГУ', '5 лет', '@psych1',
        gender='Мужской', age=35, about_me='О себе', approach='КПТ',
        work_requests='Тревога', price='2000-3000'
    )
    
    profile = db.get_psychologist_info(1)
    assert profile is not None
    assert profile['name'] == 'Иван Иванов'
    assert profile['gender'] == 'Мужской'
    assert profile['age'] == 35
    assert profile['approach'] == 'КПТ'


def test_create_like(db):
    """Тест создания лайка"""
    db.create_user(1, 'patient1', 'patient')
    db.create_user(2, 'psych1', 'psychologist')
    
    created, is_mutual = db.create_like(1, 2)
    assert created is True
    assert is_mutual is False
    
    # Взаимный лайк
    created, is_mutual = db.create_like(2, 1)
    assert created is True
    assert is_mutual is True


def test_block_user(db):
    """Тест блокировки пользователя"""
    db.create_user(1, 'testuser', 'patient')
    
    assert db.is_user_blocked(1) is False
    
    db.block_user(1)
    assert db.is_user_blocked(1) is True
    
    db.unblock_user(1)
    assert db.is_user_blocked(1) is False


def test_delete_user_profile(db):
    """Тест удаления профиля пользователя"""
    db.create_user(1, 'testuser', 'patient')
    db.save_patient_profile(1, 'Тревога', '@test')
    
    assert db.get_user(1) is not None
    
    db.delete_user_profile(1)
    
    assert db.get_user(1) is None


def test_feature_flags(db):
    """Тест фича-флагов"""
    flag = db.get_feature_flag('psychological_test_and_matching')
    assert flag is False  # По умолчанию выключен
    
    db.set_feature_flag('psychological_test_and_matching', True)
    assert db.get_feature_flag('psychological_test_and_matching') is True


def test_save_match(db):
    """Тест сохранения совпадения"""
    db.create_user(1, 'patient1', 'patient')
    db.create_user(2, 'psych1', 'psychologist')
    
    db.save_match(1, 2, 85.5)
    
    match_percentage = db.get_match_percentage(1, 2)
    assert match_percentage == 85.5

