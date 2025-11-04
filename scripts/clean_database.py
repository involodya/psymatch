#!/usr/bin/env python3
"""
Скрипт для полной очистки БД
ВНИМАНИЕ: Удаляет ВСЕ данные!
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import sqlite3
from dotenv import load_dotenv

load_dotenv()

DB_PATH = os.getenv('DATABASE_PATH', 'psymatch.db')
DB_PATH = '../' + DB_PATH


def clean_database():
    """Полная очистка БД"""
    
    print("⚠️  ВНИМАНИЕ: Этот скрипт удалит ВСЕ данные из базы данных!")
    print(f"База данных: {DB_PATH}")
    print()
    
    response = input("Вы уверены? Введите 'yes' для подтверждения: ")
    
    if response.lower() != 'yes':
        print("Отменено.")
        return
    
    print()
    print("🗑️  Очистка базы данных...")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Очищаем все таблицы
        tables = [
            'user_actions',
            'test_results',
            'matches',
            'likes',
            'psychologist_profiles',
            'patient_profiles',
            'users',
            'schema_migrations'  # Сбрасываем миграции тоже
        ]
        
        for table in tables:
            try:
                cursor.execute(f'DELETE FROM {table}')
                print(f"  ✅ Очищена таблица: {table}")
            except sqlite3.Error as e:
                print(f"  ⚠️  Ошибка при очистке {table}: {e}")
        
        # Сбрасываем автоинкремент
        cursor.execute('DELETE FROM sqlite_sequence')
        
        conn.commit()
        
        print()
        print("🎉 База данных полностью очищена!")
        print()
        print("💡 Следующие шаги:")
        print("  1. Запустите migrate_db.py для применения миграций")
        print("  2. Запустите seed_test_data.py для тестовых данных (опционально)")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        conn.rollback()
    finally:
        conn.close()


if __name__ == '__main__':
    clean_database()

