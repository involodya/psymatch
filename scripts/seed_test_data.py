#!/usr/bin/env python3
"""
Скрипт для заполнения БД тестовыми данными
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from database import Database
from dotenv import load_dotenv
import json

load_dotenv()

DB_PATH = os.getenv('DATABASE_PATH', 'psymatch.db')
db = Database('../ '+ DB_PATH)

# Тестовые данные
TEST_PSYCHOLOGISTS = [
    {
        'user_id': 1001,
        'username': 'psych_anna',
        'name': 'Анна Иванова',
        'gender': 'Женский',
        'age': 35,
        'education': 'МГУ, факультет психологии',
        'about_me': 'Работаю с подростками и взрослыми. Верю в силу эмпатии и принятия.',
        'approach': 'Когнитивно-поведенческая терапия (КПТ)',
        'work_requests': 'Тревога, депрессия, отношения',
        'price': '2000-3000 руб./сессия',
        'experience': '7 лет частной практики',
        'contact': '@anna_psych'
    },
    {
        'user_id': 1002,
        'username': 'psych_dmitry',
        'name': 'Дмитрий Петров',
        'gender': 'Мужской',
        'age': 42,
        'education': 'СПбГУ, клиническая психология',
        'about_me': 'Помогаю людям найти внутренние ресурсы для преодоления трудностей.',
        'approach': 'Гештальт',
        'work_requests': 'Кризисы, утрата, поиск себя',
        'price': '3000-5000 руб./сессия',
        'experience': '15 лет опыта',
        'contact': '@dmitry_psych'
    },
    {
        'user_id': 1003,
        'username': 'psych_maria',
        'name': 'Мария Смирнова',
        'gender': 'Женский',
        'age': 28,
        'education': 'МГППУ, консультативная психология',
        'about_me': 'Специализируюсь на работе с тревожными расстройствами.',
        'approach': '3 волна КПТ (АСТ, ДБТ, CFT, MBCT, схема-терапия)',
        'work_requests': 'Тревожные расстройства, панические атаки, ОКР',
        'price': '1000-2000 руб./сессия',
        'experience': '4 года практики',
        'contact': '@maria_psych'
    }
]

TEST_PATIENTS = [
    {
        'user_id': 2001,
        'username': 'patient_ivan',
        'main_request': 'Тревога, проблемы с поиском работы, низкая самооценка',
        'contact': '@ivan_patient'
    },
    {
        'user_id': 2002,
        'username': 'patient_olga',
        'main_request': 'Депрессия после расставания, проблемы со сном',
        'contact': '@olga_patient'
    }
]

# Тестовые векторы значений (для совместимости)
TEST_VALUES_VECTORS = {
    1001: json.dumps([0.5, 0.3, -0.2, 0.7, 0.1]),
    1002: json.dumps([0.3, 0.6, 0.1, -0.4, 0.5]),
    1003: json.dumps([0.7, 0.2, 0.4, 0.5, -0.3]),
    2001: json.dumps([0.6, 0.4, -0.1, 0.6, 0.2]),
    2002: json.dumps([0.4, 0.5, 0.2, -0.3, 0.4])
}


def seed_database():
    """Заполнить БД тестовыми данными"""
    
    print("🌱 Заполнение БД тестовыми данными...")
    print()
    
    # Создаем психологов
    print("👨‍⚕️ Создание психологов...")
    for psych in TEST_PSYCHOLOGISTS:
        user_id = psych['user_id']
        
        # Создаем пользователя
        db.create_user(user_id, psych['username'], 'psychologist')
        
        # Создаем профиль
        db.save_psychologist_profile(
            user_id,
            psych['name'],
            f'photo_{user_id}',  # fake photo_file_id
            psych['education'],
            psych['experience'],
            psych['contact'],
            gender=psych['gender'],
            age=psych['age'],
            about_me=psych['about_me'],
            approach=psych['approach'],
            work_requests=psych['work_requests'],
            price=psych['price']
        )
        
        # Сохраняем результат теста
        db.save_test_result(user_id, TEST_VALUES_VECTORS[user_id])
        
        print(f"  ✅ {psych['name']} (ID: {user_id})")
    
    print()
    
    # Создаем пациентов
    print("👤 Создание пациентов...")
    for patient in TEST_PATIENTS:
        user_id = patient['user_id']
        
        # Создаем пользователя
        db.create_user(user_id, patient['username'], 'patient')
        
        # Создаем профиль
        db.save_patient_profile(
            user_id,
            patient['main_request'],
            patient['contact']
        )
        
        # Сохраняем результат теста
        db.save_test_result(user_id, TEST_VALUES_VECTORS[user_id])
        
        print(f"  ✅ @{patient['username']} (ID: {user_id})")
    
    print()
    
    # Рассчитываем совместимость
    print("🔥 Расчет совместимости...")
    from matching import MatchingSystem
    matching_system = MatchingSystem(db)
    
    for patient in TEST_PATIENTS:
        matching_system.calculate_all_matches_for_patient(patient['user_id'])
    
    print("  ✅ Совместимость рассчитана")
    
    print()
    
    # Создаем тестовые лайки
    print("❤️ Создание тестовых лайков...")
    db.create_like(2001, 1001)  # Иван лайкает Анну
    db.create_like(2001, 1003)  # Иван лайкает Марию
    db.create_like(2002, 1002)  # Ольга лайкает Дмитрия
    db.create_like(1001, 2001)  # Анна лайкает Ивана (взаимно!)
    print("  ✅ Созданы тестовые лайки")
    
    print()
    print("🎉 Готово! Тестовые данные добавлены.")
    print()
    print("📊 Статистика:")
    print(f"  - Психологов: {len(TEST_PSYCHOLOGISTS)}")
    print(f"  - Пациентов: {len(TEST_PATIENTS)}")
    print(f"  - Лайков: 4")
    print(f"  - Взаимных: 1")
    print()
    print("💡 Тестовые ID:")
    print(f"  Психологи: {', '.join(str(p['user_id']) for p in TEST_PSYCHOLOGISTS)}")
    print(f"  Пациенты: {', '.join(str(p['user_id']) for p in TEST_PATIENTS)}")


if __name__ == '__main__':
    seed_database()

