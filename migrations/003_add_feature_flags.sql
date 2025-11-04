-- Migration 003: Добавление системы фича-флагов

-- Таблица фича-флагов
CREATE TABLE IF NOT EXISTS feature_flags (
    flag_name TEXT PRIMARY KEY,
    enabled INTEGER DEFAULT 0,
    description TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Добавляем первый фича-флаг
INSERT OR IGNORE INTO feature_flags (flag_name, enabled, description)
VALUES ('psychological_test_and_matching', 0, 'Включить психологический тест и подбор по совместимости');

