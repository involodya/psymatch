import sqlite3
import logging
from datetime import datetime
from typing import Optional, List, Dict, Tuple

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.init_db()
    
    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_db(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                user_type TEXT NOT NULL,
                registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                test_completed INTEGER DEFAULT 0,
                current_card_index INTEGER DEFAULT 0
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS psychologist_profiles (
                user_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                photo_file_id TEXT,
                education TEXT NOT NULL,
                experience TEXT NOT NULL,
                contact TEXT,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS patient_profiles (
                user_id INTEGER PRIMARY KEY,
                main_request TEXT NOT NULL,
                contact TEXT,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS test_results (
                user_id INTEGER PRIMARY KEY,
                values_vector TEXT NOT NULL,
                completed_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS matches (
                patient_id INTEGER,
                psychologist_id INTEGER,
                match_percentage REAL NOT NULL,
                PRIMARY KEY (patient_id, psychologist_id),
                FOREIGN KEY (patient_id) REFERENCES users(user_id),
                FOREIGN KEY (psychologist_id) REFERENCES users(user_id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS likes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_user_id INTEGER NOT NULL,
                to_user_id INTEGER NOT NULL,
                liked_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_mutual INTEGER DEFAULT 0,
                UNIQUE(from_user_id, to_user_id),
                FOREIGN KEY (from_user_id) REFERENCES users(user_id),
                FOREIGN KEY (to_user_id) REFERENCES users(user_id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                action_type TEXT NOT NULL,
                action_data TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Database initialized successfully")
    
    def create_user(self, user_id: int, username: Optional[str], user_type: str):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO users (user_id, username, user_type)
                VALUES (?, ?, ?)
            ''', (user_id, username, user_type))
            conn.commit()
            logger.info(f"User created: {user_id}, type: {user_type}")
        except sqlite3.IntegrityError:
            logger.warning(f"User {user_id} already exists")
        finally:
            conn.close()
    
    def get_user(self, user_id: int) -> Optional[Dict]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None
    
    def update_last_active(self, user_id: int):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE users SET last_active = CURRENT_TIMESTAMP
            WHERE user_id = ?
        ''', (user_id,))
        conn.commit()
        conn.close()
    
    def save_psychologist_profile(self, user_id: int, name: str, photo_file_id: str, 
                                  education: str, experience: str, contact: str):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO psychologist_profiles 
            (user_id, name, photo_file_id, education, experience, contact)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, name, photo_file_id, education, experience, contact))
        conn.commit()
        conn.close()
        logger.info(f"Psychologist profile saved: {user_id}")
    
    def save_patient_profile(self, user_id: int, main_request: str, contact: str):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO patient_profiles 
            (user_id, main_request, contact)
            VALUES (?, ?, ?)
        ''', (user_id, main_request, contact))
        conn.commit()
        conn.close()
        logger.info(f"Patient profile saved: {user_id}")
    
    def save_test_result(self, user_id: int, values_vector: str):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO test_results (user_id, values_vector)
            VALUES (?, ?)
        ''', (user_id, values_vector))
        cursor.execute('''
            UPDATE users SET test_completed = 1 WHERE user_id = ?
        ''', (user_id,))
        conn.commit()
        conn.close()
        logger.info(f"Test result saved: {user_id}")
    
    def get_test_result(self, user_id: int) -> Optional[str]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT values_vector FROM test_results WHERE user_id = ?', (user_id,))
        row = cursor.fetchone()
        conn.close()
        return row['values_vector'] if row else None
    
    def save_match(self, patient_id: int, psychologist_id: int, match_percentage: float):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO matches 
            (patient_id, psychologist_id, match_percentage)
            VALUES (?, ?, ?)
        ''', (patient_id, psychologist_id, match_percentage))
        conn.commit()
        conn.close()
    
    def get_psychologists_for_patient(self, patient_id: int) -> List[Dict]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT 
                u.user_id, u.username,
                pp.name, pp.photo_file_id, pp.education, pp.experience, pp.contact,
                m.match_percentage,
                CASE WHEN l.from_user_id IS NOT NULL THEN 1 ELSE 0 END as already_liked
            FROM users u
            JOIN psychologist_profiles pp ON u.user_id = pp.user_id
            JOIN matches m ON u.user_id = m.psychologist_id
            LEFT JOIN likes l ON l.from_user_id = ? AND l.to_user_id = u.user_id
            WHERE m.patient_id = ? AND u.test_completed = 1
            ORDER BY m.match_percentage DESC
        ''', (patient_id, patient_id))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    def get_all_psychologists(self) -> List[int]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT user_id FROM users 
            WHERE user_type = 'psychologist' AND test_completed = 1
        ''')
        rows = cursor.fetchall()
        conn.close()
        return [row['user_id'] for row in rows]
    
    def get_all_patients(self) -> List[int]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT user_id FROM users 
            WHERE user_type = 'patient' AND test_completed = 1
        ''')
        rows = cursor.fetchall()
        conn.close()
        return [row['user_id'] for row in rows]
    
    def create_like(self, from_user_id: int, to_user_id: int) -> Tuple[bool, bool]:
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id FROM likes 
            WHERE from_user_id = ? AND to_user_id = ?
        ''', (from_user_id, to_user_id))
        if cursor.fetchone():
            conn.close()
            return False, False
        
        cursor.execute('''
            INSERT INTO likes (from_user_id, to_user_id)
            VALUES (?, ?)
        ''', (from_user_id, to_user_id))
        
        cursor.execute('''
            SELECT id FROM likes 
            WHERE from_user_id = ? AND to_user_id = ?
        ''', (to_user_id, from_user_id))
        is_mutual = cursor.fetchone() is not None
        
        if is_mutual:
            cursor.execute('''
                UPDATE likes SET is_mutual = 1 
                WHERE (from_user_id = ? AND to_user_id = ?) 
                OR (from_user_id = ? AND to_user_id = ?)
            ''', (from_user_id, to_user_id, to_user_id, from_user_id))
        
        conn.commit()
        conn.close()
        logger.info(f"Like created: {from_user_id} -> {to_user_id}, mutual: {is_mutual}")
        return True, is_mutual
    
    def get_likes_for_psychologist(self, psychologist_id: int) -> List[Dict]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT 
                u.user_id, u.username,
                pp.main_request, pp.contact,
                l.liked_date, l.is_mutual,
                m.match_percentage
            FROM likes l
            JOIN users u ON l.from_user_id = u.user_id
            JOIN patient_profiles pp ON u.user_id = pp.user_id
            LEFT JOIN matches m ON m.patient_id = u.user_id AND m.psychologist_id = ?
            WHERE l.to_user_id = ?
            ORDER BY l.liked_date DESC
        ''', (psychologist_id, psychologist_id))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    def get_patient_info(self, patient_id: int) -> Optional[Dict]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT u.user_id, u.username, pp.main_request, pp.contact
            FROM users u
            JOIN patient_profiles pp ON u.user_id = pp.user_id
            WHERE u.user_id = ?
        ''', (patient_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None
    
    def get_psychologist_info(self, psychologist_id: int) -> Optional[Dict]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT u.user_id, u.username, 
                   pp.name, pp.photo_file_id, pp.education, pp.experience, pp.contact
            FROM users u
            JOIN psychologist_profiles pp ON u.user_id = pp.user_id
            WHERE u.user_id = ?
        ''', (psychologist_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None
    
    def update_card_index(self, user_id: int, index: int):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE users SET current_card_index = ? WHERE user_id = ?
        ''', (index, user_id))
        conn.commit()
        conn.close()
    
    def get_card_index(self, user_id: int) -> int:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT current_card_index FROM users WHERE user_id = ?', (user_id,))
        row = cursor.fetchone()
        conn.close()
        return row['current_card_index'] if row else 0
    
    def log_action(self, user_id: int, action_type: str, action_data: Optional[str] = None):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO user_actions (user_id, action_type, action_data)
            VALUES (?, ?, ?)
        ''', (user_id, action_type, action_data))
        conn.commit()
        conn.close()
    
    def get_statistics(self) -> Dict:
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) as count FROM users WHERE user_type = 'psychologist'")
        psychologists_count = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM users WHERE user_type = 'patient'")
        patients_count = cursor.fetchone()['count']
        
        cursor.execute("""
            SELECT COUNT(*) as count FROM users 
            WHERE datetime(last_active) >= datetime('now', '-1 day')
        """)
        active_users_24h = cursor.fetchone()['count']
        
        cursor.execute("""
            SELECT COUNT(*) as count FROM users 
            WHERE user_type = 'psychologist' 
            AND datetime(last_active) >= datetime('now', '-1 day')
        """)
        active_psychologists_24h = cursor.fetchone()['count']
        
        cursor.execute("""
            SELECT COUNT(*) as count FROM users 
            WHERE user_type = 'patient' 
            AND datetime(last_active) >= datetime('now', '-1 day')
        """)
        active_patients_24h = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM likes WHERE is_mutual = 1")
        mutual_matches = cursor.fetchone()['count'] // 2
        
        cursor.execute("""
            SELECT COUNT(*) as count FROM likes 
            WHERE is_mutual = 1 
            AND datetime(liked_date) >= datetime('now', '-1 day')
        """)
        matches_24h = cursor.fetchone()['count'] // 2
        
        conn.close()
        
        return {
            'psychologists_count': psychologists_count,
            'patients_count': patients_count,
            'active_users_24h': active_users_24h,
            'active_psychologists_24h': active_psychologists_24h,
            'active_patients_24h': active_patients_24h,
            'mutual_matches': mutual_matches,
            'matches_24h': matches_24h
        }

