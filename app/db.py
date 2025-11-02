from __future__ import annotations

import json
import sqlite3
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional


ISO_FMT = "%Y-%m-%dT%H:%M:%S"


def _now() -> str:
    return datetime.utcnow().strftime(ISO_FMT)


@dataclass(slots=True)
class User:
    id: int
    telegram_id: int
    role: str
    username: Optional[str]
    full_name: Optional[str]
    contact: Optional[str]
    registered_at: Optional[str]
    last_active_at: Optional[str]
    test_completed: bool
    traits: Dict[str, float]


class Database:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        with self.conn:
            self.conn.executescript(
                """
                PRAGMA foreign_keys = ON;

                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id INTEGER NOT NULL UNIQUE,
                    role TEXT NOT NULL,
                    username TEXT,
                    full_name TEXT,
                    contact TEXT,
                    registered_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now')),
                    last_active_at TEXT,
                    test_completed INTEGER DEFAULT 0,
                    traits_json TEXT
                );

                CREATE TABLE IF NOT EXISTS psychologists (
                    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
                    photo_file_id TEXT,
                    education TEXT,
                    experience TEXT,
                    bio TEXT
                );

                CREATE TABLE IF NOT EXISTS patients (
                    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
                    main_request TEXT
                );

                CREATE TABLE IF NOT EXISTS test_answers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    audience TEXT NOT NULL,
                    question_id TEXT NOT NULL,
                    value INTEGER NOT NULL,
                    created_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now'))
                );

                CREATE TABLE IF NOT EXISTS likes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    liker_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    liked_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    created_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now')),
                    UNIQUE(liker_id, liked_id)
                );

                CREATE TABLE IF NOT EXISTS matches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    patient_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    psychologist_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    created_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now')),
                    UNIQUE(patient_id, psychologist_id)
                );

                CREATE TABLE IF NOT EXISTS match_scores (
                    patient_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    psychologist_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    score REAL NOT NULL,
                    updated_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now')),
                    PRIMARY KEY (patient_id, psychologist_id)
                );

                CREATE TABLE IF NOT EXISTS patient_swipe_state (
                    patient_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
                    current_index INTEGER NOT NULL DEFAULT 0
                );
                """
            )

    @contextmanager
    def _cursor(self) -> Iterator[sqlite3.Cursor]:
        cursor = self.conn.cursor()
        try:
            yield cursor
        finally:
            cursor.close()

    def close(self) -> None:
        self.conn.close()

    def upsert_user(
        self,
        telegram_id: int,
        role: str,
        username: Optional[str],
        full_name: Optional[str],
        contact: Optional[str],
    ) -> int:
        with self.conn:
            cursor = self.conn.execute(
                """
                INSERT INTO users (telegram_id, role, username, full_name, contact, last_active_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT (telegram_id)
                DO UPDATE SET
                    role=excluded.role,
                    username=excluded.username,
                    full_name=excluded.full_name,
                    contact=excluded.contact,
                    last_active_at=excluded.last_active_at
                RETURNING id
                """,
                (telegram_id, role, username, full_name, contact, _now()),
            )
            row = cursor.fetchone()
            return int(row[0])

    def update_last_active(self, user_id: int) -> None:
        with self.conn:
            self.conn.execute(
                "UPDATE users SET last_active_at = ? WHERE id = ?",
                (_now(), user_id),
            )

    def save_patient_profile(self, user_id: int, request: str) -> None:
        with self.conn:
            self.conn.execute(
                """
                INSERT INTO patients (user_id, main_request)
                VALUES (?, ?)
                ON CONFLICT(user_id) DO UPDATE SET main_request=excluded.main_request
                """,
                (user_id, request),
            )

    def save_psychologist_profile(
        self,
        user_id: int,
        photo_file_id: Optional[str],
        education: Optional[str],
        experience: Optional[str],
        bio: Optional[str],
    ) -> None:
        with self.conn:
            self.conn.execute(
                """
                INSERT INTO psychologists (user_id, photo_file_id, education, experience, bio)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    photo_file_id=excluded.photo_file_id,
                    education=excluded.education,
                    experience=excluded.experience,
                    bio=excluded.bio
                """,
                (user_id, photo_file_id, education, experience, bio),
            )

    def get_user_by_telegram(self, telegram_id: int) -> Optional[User]:
        cursor = self.conn.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return self._row_to_user(row)

    def get_user(self, user_id: int) -> Optional[User]:
        cursor = self.conn.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return self._row_to_user(row)

    def _row_to_user(self, row: sqlite3.Row) -> User:
        raw_traits = row["traits_json"]
        traits = json.loads(raw_traits) if raw_traits else {}
        return User(
            id=row["id"],
            telegram_id=row["telegram_id"],
            role=row["role"],
            username=row["username"],
            full_name=row["full_name"],
            contact=row["contact"],
            registered_at=row["registered_at"],
            last_active_at=row["last_active_at"],
            test_completed=bool(row["test_completed"]),
            traits=traits,
        )

    def save_test_results(
        self,
        user_id: int,
        audience: str,
        traits: Dict[str, float],
        answers: Iterable[tuple[str, int]],
    ) -> None:
        serialized = json.dumps(traits)
        now = _now()
        with self.conn:
            self.conn.execute(
                "UPDATE users SET traits_json = ?, test_completed = 1, last_active_at = ? WHERE id = ?",
                (serialized, now, user_id),
            )
            self.conn.executemany(
                "INSERT INTO test_answers (user_id, audience, question_id, value, created_at) VALUES (?, ?, ?, ?, ?)",
                ((user_id, audience, question_id, value, now) for question_id, value in answers),
            )

    def list_psychologists(self) -> List[sqlite3.Row]:
        cursor = self.conn.execute(
            """
            SELECT u.*, p.photo_file_id, p.education, p.experience, p.bio
            FROM users u
            JOIN psychologists p ON p.user_id = u.id
            WHERE u.role = 'psychologist'
            ORDER BY u.registered_at ASC
            """
        )
        return cursor.fetchall()

    def list_patients(self) -> List[sqlite3.Row]:
        cursor = self.conn.execute(
            """
            SELECT u.*, pa.main_request
            FROM users u
            JOIN patients pa ON pa.user_id = u.id
            WHERE u.role = 'patient'
            ORDER BY u.registered_at ASC
            """
        )
        return cursor.fetchall()

    def record_like(self, liker_id: int, liked_id: int) -> bool:
        try:
            with self.conn:
                self.conn.execute(
                    "INSERT INTO likes (liker_id, liked_id) VALUES (?, ?)",
                    (liker_id, liked_id),
                )
            return True
        except sqlite3.IntegrityError:
            return False

    def has_like(self, liker_id: int, liked_id: int) -> bool:
        cursor = self.conn.execute(
            "SELECT 1 FROM likes WHERE liker_id = ? AND liked_id = ?",
            (liker_id, liked_id),
        )
        return cursor.fetchone() is not None

    def ensure_match(self, patient_id: int, psychologist_id: int) -> None:
        with self.conn:
            self.conn.execute(
                """
                INSERT INTO matches (patient_id, psychologist_id)
                VALUES (?, ?)
                ON CONFLICT(patient_id, psychologist_id) DO NOTHING
                """,
                (patient_id, psychologist_id),
            )

    def list_patients_who_liked(self, psychologist_id: int) -> List[sqlite3.Row]:
        cursor = self.conn.execute(
            """
            SELECT u.*, pa.main_request, l.created_at
            FROM likes l
            JOIN users u ON u.id = l.liker_id
            LEFT JOIN patients pa ON pa.user_id = u.id
            WHERE l.liked_id = ? AND u.role = 'patient'
            ORDER BY l.created_at DESC
            """,
            (psychologist_id,),
        )
        return cursor.fetchall()

    def upsert_match_score(self, patient_id: int, psychologist_id: int, score: float) -> None:
        with self.conn:
            self.conn.execute(
                """
                INSERT INTO match_scores (patient_id, psychologist_id, score, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(patient_id, psychologist_id) DO UPDATE SET
                    score=excluded.score,
                    updated_at=excluded.updated_at
                """,
                (patient_id, psychologist_id, score, _now()),
            )

    def get_ranked_psychologists(self, patient_id: int) -> List[sqlite3.Row]:
        cursor = self.conn.execute(
            """
            SELECT ms.score, u.*, p.photo_file_id, p.education, p.experience, p.bio
            FROM match_scores ms
            JOIN users u ON u.id = ms.psychologist_id
            JOIN psychologists p ON p.user_id = u.id
            WHERE ms.patient_id = ?
            ORDER BY ms.score DESC, u.registered_at ASC
            """,
            (patient_id,),
        )
        return cursor.fetchall()

    def set_patient_swipe_index(self, patient_id: int, index: int) -> None:
        with self.conn:
            self.conn.execute(
                """
                INSERT INTO patient_swipe_state (patient_id, current_index)
                VALUES (?, ?)
                ON CONFLICT(patient_id) DO UPDATE SET current_index=excluded.current_index
                """,
                (patient_id, index),
            )

    def get_patient_swipe_index(self, patient_id: int) -> int:
        cursor = self.conn.execute(
            "SELECT current_index FROM patient_swipe_state WHERE patient_id = ?",
            (patient_id,),
        )
        row = cursor.fetchone()
        return int(row["current_index"]) if row else 0

    def fetch_stats(self) -> Dict[str, Any]:
        day_ago = (datetime.utcnow() - timedelta(days=1)).strftime(ISO_FMT)
        cursor = self.conn.execute(
            "SELECT COUNT(*) FROM users WHERE role = 'psychologist'"
        )
        psychologists = cursor.fetchone()[0]

        cursor = self.conn.execute("SELECT COUNT(*) FROM users WHERE role = 'patient'")
        patients = cursor.fetchone()[0]

        cursor = self.conn.execute(
            """
            SELECT role, COUNT(*) as cnt
            FROM users
            WHERE last_active_at >= ?
            GROUP BY role
            """,
            (day_ago,),
        )
        active_counts = defaultdict(int)
        for row in cursor.fetchall():
            active_counts[row["role"]] = row["cnt"]

        cursor = self.conn.execute("SELECT COUNT(*) FROM matches")
        matches_total = cursor.fetchone()[0]

        cursor = self.conn.execute(
            "SELECT COUNT(*) FROM matches WHERE created_at >= ?",
            (day_ago,),
        )
        matches_recent = cursor.fetchone()[0]

        return {
            "psychologists": psychologists,
            "patients": patients,
            "active_total": sum(active_counts.values()),
            "active_patients": active_counts.get("patient", 0),
            "active_psychologists": active_counts.get("psychologist", 0),
            "matches_total": matches_total,
            "matches_recent": matches_recent,
        }

    def list_patient_likes(self, patient_id: int) -> List[int]:
        cursor = self.conn.execute(
            "SELECT liked_id FROM likes WHERE liker_id = ?",
            (patient_id,),
        )
        return [row["liked_id"] for row in cursor.fetchall()]

    def list_likes_for_psychologist(self, psychologist_id: int) -> List[int]:
        cursor = self.conn.execute(
            "SELECT liker_id FROM likes WHERE liked_id = ?",
            (psychologist_id,),
        )
        return [row["liker_id"] for row in cursor.fetchall()]

    def is_match(self, patient_id: int, psychologist_id: int) -> bool:
        cursor = self.conn.execute(
            "SELECT 1 FROM matches WHERE patient_id = ? AND psychologist_id = ?",
            (patient_id, psychologist_id),
        )
        return cursor.fetchone() is not None

    def get_patient_profile(self, patient_id: int) -> Optional[sqlite3.Row]:
        cursor = self.conn.execute(
            """
            SELECT u.*, pa.main_request
            FROM users u
            JOIN patients pa ON pa.user_id = u.id
            WHERE u.id = ?
            """,
            (patient_id,),
        )
        return cursor.fetchone()

    def get_psychologist_profile(self, psychologist_id: int) -> Optional[sqlite3.Row]:
        cursor = self.conn.execute(
            """
            SELECT u.*, p.photo_file_id, p.education, p.experience, p.bio
            FROM users u
            JOIN psychologists p ON p.user_id = u.id
            WHERE u.id = ?
            """,
            (psychologist_id,),
        )
        return cursor.fetchone()


