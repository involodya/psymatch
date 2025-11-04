-- Migration 001: Initial schema (базовая схема v1.0)
-- Эта миграция уже применена, если БД существует

-- Таблица пользователей
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    user_type TEXT NOT NULL,
    registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    test_completed INTEGER DEFAULT 0,
    current_card_index INTEGER DEFAULT 0
);

-- Таблица профилей психологов
CREATE TABLE IF NOT EXISTS psychologist_profiles (
    user_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    photo_file_id TEXT,
    education TEXT NOT NULL,
    experience TEXT NOT NULL,
    contact TEXT,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- Таблица профилей пациентов
CREATE TABLE IF NOT EXISTS patient_profiles (
    user_id INTEGER PRIMARY KEY,
    main_request TEXT NOT NULL,
    contact TEXT,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- Таблица результатов тестов
CREATE TABLE IF NOT EXISTS test_results (
    user_id INTEGER PRIMARY KEY,
    values_vector TEXT NOT NULL,
    completed_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- Таблица совпадений
CREATE TABLE IF NOT EXISTS matches (
    patient_id INTEGER,
    psychologist_id INTEGER,
    match_percentage REAL NOT NULL,
    PRIMARY KEY (patient_id, psychologist_id),
    FOREIGN KEY (patient_id) REFERENCES users(user_id),
    FOREIGN KEY (psychologist_id) REFERENCES users(user_id)
);

-- Таблица лайков
CREATE TABLE IF NOT EXISTS likes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    from_user_id INTEGER NOT NULL,
    to_user_id INTEGER NOT NULL,
    liked_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_mutual INTEGER DEFAULT 0,
    UNIQUE(from_user_id, to_user_id),
    FOREIGN KEY (from_user_id) REFERENCES users(user_id),
    FOREIGN KEY (to_user_id) REFERENCES users(user_id)
);

-- Таблица действий пользователей
CREATE TABLE IF NOT EXISTS user_actions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    action_type TEXT NOT NULL,
    action_data TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

