import sqlite3
from datetime import datetime, timedelta
import json

class Database:
    def __init__(self, db_path="psymatch.db"):
        self.db_path = db_path
        self.init_db()

    def get_connection(self):
        return sqlite3.connect(self.db_path)

    def init_db(self):
        """Инициализация базы данных"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Таблица пользователей
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    role TEXT NOT NULL,  -- 'psychologist' или 'patient'
                    name TEXT,
                    photo_file_id TEXT,
                    education TEXT,  -- только для психологов
                    experience TEXT,  -- только для психологов
                    request TEXT,  -- только для пациентов
                    test_answers TEXT,  -- JSON с ответами на тест
                    registered_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_active DATETIME DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1
                )
            ''')

            # Таблица лайков
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS likes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    from_user_id INTEGER,
                    to_user_id INTEGER,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(from_user_id, to_user_id)
                )
            ''')

            # Таблица просмотренных профилей
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS viewed_profiles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    viewed_user_id INTEGER,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, viewed_user_id)
                )
            ''')

            # Таблица аналитики (для логов поведения)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS analytics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    action TEXT,  -- 'swipe_right', 'swipe_left', 'view_profile', etc.
                    target_user_id INTEGER,
                    profile_position INTEGER,  -- позиция в списке профилей
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT  -- JSON с дополнительной информацией
                )
            ''')

            conn.commit()

    def register_user(self, user_id, role):
        """Регистрация нового пользователя"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO users (user_id, role, registered_at, last_active)
                VALUES (?, ?, ?, ?)
            ''', (user_id, role, datetime.now(), datetime.now()))
            conn.commit()

    def update_user_profile(self, user_id, **kwargs):
        """Обновление профиля пользователя"""
        fields = []
        values = []

        for key, value in kwargs.items():
            if key in ['name', 'photo_file_id', 'education', 'experience', 'request', 'test_answers']:
                fields.append(f"{key} = ?")
                values.append(value)

        if fields:
            values.append(user_id)
            query = f"UPDATE users SET {', '.join(fields)}, last_active = ? WHERE user_id = ?"
            values.insert(-1, datetime.now())

            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, values)
                conn.commit()

    def get_user(self, user_id):
        """Получение данных пользователя"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()

            if row:
                columns = [desc[0] for desc in cursor.description]
                user_data = dict(zip(columns, row))

                # Парсим JSON поля
                if user_data.get('test_answers'):
                    user_data['test_answers'] = json.loads(user_data['test_answers'])

                return user_data
        return None

    def save_test_answers(self, user_id, answers):
        """Сохранение ответов на тест"""
        self.update_user_profile(user_id, test_answers=json.dumps(answers))

    def add_like(self, from_user_id, to_user_id):
        """Добавление лайка"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute('''
                    INSERT INTO likes (from_user_id, to_user_id)
                    VALUES (?, ?)
                ''', (from_user_id, to_user_id))
                conn.commit()
                return True
            except sqlite3.IntegrityError:
                # Лайк уже существует
                return False

    def check_mutual_like(self, user1_id, user2_id):
        """Проверка взаимного лайка"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT COUNT(*) FROM likes
                WHERE (from_user_id = ? AND to_user_id = ?) OR (from_user_id = ? AND to_user_id = ?)
            ''', (user1_id, user2_id, user2_id, user1_id))
            count = cursor.fetchone()[0]
            return count == 2

    def get_likes_for_user(self, user_id):
        """Получение всех лайков для пользователя (кто его лайкнул)"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT u.* FROM likes l
                JOIN users u ON l.from_user_id = u.user_id
                WHERE l.to_user_id = ?
                ORDER BY l.created_at DESC
            ''', (user_id,))

            likes = []
            for row in cursor.fetchall():
                columns = [desc[0] for desc in cursor.description]
                user_data = dict(zip(columns, row))
                if user_data.get('test_answers'):
                    user_data['test_answers'] = json.loads(user_data['test_answers'])
                likes.append(user_data)

            return likes

    def get_profiles_for_swiping(self, user_id, role_to_find, offset=0, limit=10):
        """Получение профилей для листания"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Получаем просмотренные профили
            cursor.execute('''
                SELECT viewed_user_id FROM viewed_profiles
                WHERE user_id = ?
            ''', (user_id,))
            viewed_ids = [row[0] for row in cursor.fetchall()]
            viewed_ids.append(user_id)  # Исключаем себя

            # Получаем пользователей нужной роли, которых еще не просмотрели
            placeholders = ','.join('?' * len(viewed_ids))
            query = f'''
                SELECT * FROM users
                WHERE role = ? AND user_id NOT IN ({placeholders})
                AND is_active = 1
                ORDER BY registered_at DESC
                LIMIT ? OFFSET ?
            '''

            cursor.execute(query, [role_to_find] + viewed_ids + [limit, offset])
            profiles = []

            for row in cursor.fetchall():
                columns = [desc[0] for desc in cursor.description]
                profile = dict(zip(columns, row))
                if profile.get('test_answers'):
                    profile['test_answers'] = json.loads(profile['test_answers'])
                profiles.append(profile)

            return profiles

    def mark_profile_viewed(self, user_id, viewed_user_id):
        """Отметить профиль как просмотренный"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute('''
                    INSERT INTO viewed_profiles (user_id, viewed_user_id)
                    VALUES (?, ?)
                ''', (user_id, viewed_user_id))
                conn.commit()
            except sqlite3.IntegrityError:
                pass  # Уже отмечено

    def log_analytics(self, user_id, action, target_user_id=None, profile_position=None, metadata=None):
        """Логирование действия для аналитики"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO analytics (user_id, action, target_user_id, profile_position, metadata)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, action, target_user_id, profile_position, json.dumps(metadata) if metadata else None))
            conn.commit()

    def get_statistics(self):
        """Получение статистики для админов"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Общее количество пользователей по ролям
            cursor.execute("SELECT role, COUNT(*) FROM users WHERE is_active = 1 GROUP BY role")
            role_counts = dict(cursor.fetchall())

            psychologists_count = role_counts.get('psychologist', 0)
            patients_count = role_counts.get('patient', 0)

            # Активные пользователи (заходили за последние сутки)
            yesterday = datetime.now() - timedelta(days=1)
            cursor.execute("SELECT COUNT(*) FROM users WHERE last_active > ?", (yesterday,))
            active_users_count = cursor.fetchone()[0]

            # Общее количество пар (взаимных лайков)
            cursor.execute('''
                SELECT COUNT(*) FROM (
                    SELECT DISTINCT
                        CASE WHEN l1.from_user_id < l1.to_user_id
                            THEN l1.from_user_id || '-' || l1.to_user_id
                            ELSE l1.to_user_id || '-' || l1.from_user_id
                        END as pair_id
                    FROM likes l1
                    INNER JOIN likes l2 ON l1.from_user_id = l2.to_user_id AND l1.to_user_id = l2.from_user_id
                )
            ''')
            total_matches = cursor.fetchone()[0]

            # Новые пары за последние сутки
            cursor.execute('''
                SELECT COUNT(*) FROM (
                    SELECT DISTINCT
                        CASE WHEN l1.from_user_id < l1.to_user_id
                            THEN l1.from_user_id || '-' || l1.to_user_id
                            ELSE l1.to_user_id || '-' || l1.from_user_id
                        END as pair_id
                    FROM likes l1
                    INNER JOIN likes l2 ON l1.from_user_id = l2.to_user_id AND l1.to_user_id = l2.from_user_id
                    WHERE l1.created_at > ? AND l2.created_at > ?
                )
            ''', (yesterday, yesterday))
            new_matches_today = cursor.fetchone()[0]

            return {
                'psychologists_count': psychologists_count,
                'patients_count': patients_count,
                'active_users_count': active_users_count,
                'total_matches': total_matches,
                'new_matches_today': new_matches_today
            }

    def update_last_active(self, user_id):
        """Обновление времени последней активности"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET last_active = ? WHERE user_id = ?", (datetime.now(), user_id))
            conn.commit()
