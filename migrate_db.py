#!/usr/bin/env python3
"""
Система версионированных миграций для PsyMatch
"""

import sqlite3
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

DB_PATH = os.getenv('DATABASE_PATH', 'psymatch.db')
MIGRATIONS_DIR = Path(__file__).parent / 'migrations'


def init_migrations_table(conn):
    """Создает таблицу для отслеживания примененных миграций"""
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()


def get_applied_migrations(conn):
    """Возвращает список примененных миграций"""
    cursor = conn.cursor()
    cursor.execute('SELECT version FROM schema_migrations ORDER BY version')
    return {row[0] for row in cursor.fetchall()}


def get_pending_migrations(applied):
    """Возвращает список миграций, которые нужно применить"""
    migrations = []
    
    if not MIGRATIONS_DIR.exists():
        return migrations
    
    for file in sorted(MIGRATIONS_DIR.glob('*.sql')):
        version = int(file.stem.split('_')[0])
        if version not in applied:
            migrations.append((version, file))
    
    return sorted(migrations)


def apply_migration(conn, version, filepath):
    """Применяет одну миграцию"""
    print(f"Применение миграции {version}: {filepath.name}")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        sql = f.read()
    
    cursor = conn.cursor()
    try:
        # Выполняем SQL из файла
        cursor.executescript(sql)
        
        # Записываем, что миграция применена
        cursor.execute('INSERT INTO schema_migrations (version) VALUES (?)', (version,))
        conn.commit()
        
        print(f"✅ Миграция {version} применена успешно")
        return True
        
    except sqlite3.Error as e:
        print(f"❌ Ошибка при применении миграции {version}: {e}")
        conn.rollback()
        return False


def migrate():
    """Основная функция миграции"""
    
    if not os.path.exists(DB_PATH):
        print(f"База данных {DB_PATH} не найдена. Создаем новую...")
    
    conn = sqlite3.connect(DB_PATH)
    
    try:
        # Инициализируем таблицу миграций
        init_migrations_table(conn)
        
        # Получаем примененные миграции
        applied = get_applied_migrations(conn)
        print(f"Применено миграций: {len(applied)}")
        
        # Получаем ожидающие миграции
        pending = get_pending_migrations(applied)
        
        if not pending:
            print("✅ Все миграции уже применены. База данных актуальна.")
            return
        
        print(f"Найдено новых миграций: {len(pending)}")
        print()
        
        # Применяем миграции
        for version, filepath in pending:
            if not apply_migration(conn, version, filepath):
                print("❌ Миграция прервана из-за ошибки")
                break
        else:
            print()
            print("🎉 Все миграции применены успешно!")
            
    finally:
        conn.close()


if __name__ == '__main__':
    migrate()
