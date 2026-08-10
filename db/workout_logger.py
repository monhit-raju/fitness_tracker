import pymysql
import sqlite3
import json
import os
from datetime import datetime

class WorkoutLogger:
    def __init__(self):
        self.connection = None
        self.db_type = None  # 'mysql' or 'sqlite'
        self.db_file = os.path.join(os.path.dirname(__file__), 'fitness_tracker.db')
        self.connect()
        if self.connection:
            self.create_tables()

    def connect(self):
        # 1. Try MySQL if host/credentials specified
        try:
            db_host = os.environ.get('DB_HOST', 'localhost')
            db_user = os.environ.get('DB_USER', 'root')
            db_password = os.environ.get('DB_PASSWORD', '')
            db_name = os.environ.get('DB_NAME', 'sports')
            db_port = int(os.environ.get('DB_PORT', 3306))

            self.connection = pymysql.connect(
                host=db_host,
                port=db_port,
                user=db_user,
                password=db_password,
                database=db_name,
                cursorclass=pymysql.cursors.DictCursor,
                connect_timeout=3
            )
            self.db_type = 'mysql'
            print("Successfully connected to MySQL database")
            return
        except Exception as e:
            print(f"[DB INFO] Could not connect to MySQL ({e}). Switching to SQLite fallback...")

        # 2. Fallback to SQLite (built-in, local file)
        try:
            os.makedirs(os.path.dirname(self.db_file), exist_ok=True)
            self.connection = sqlite3.connect(self.db_file, check_same_thread=False)
            self.connection.row_factory = sqlite3.Row
            self.db_type = 'sqlite'
            print(f"Successfully connected to SQLite database ({self.db_file})")
        except Exception as e:
            print(f"[DB ERROR] Failed to initialize SQLite database: {e}")
            self.connection = None
            self.db_type = None

    def _get_cursor(self):
        if not self.connection:
            return None
        return self.connection.cursor()

    def create_tables(self):
        if not self.connection:
            return
        cursor = self._get_cursor()

        if self.db_type == 'mysql':
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS workouts (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT DEFAULT 1,
                    exercise_type VARCHAR(50) NOT NULL,
                    sets INT DEFAULT 0,
                    reps INT DEFAULT 0,
                    duration_seconds INT DEFAULT 0,
                    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    end_time TIMESTAMP NULL,
                    video_path VARCHAR(500) NULL,
                    details JSON NULL
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS analysis_details (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    workout_id INT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    rep_count INT DEFAULT 0,
                    angle FLOAT DEFAULT NULL,
                    stage VARCHAR(50) DEFAULT NULL,
                    details JSON NULL,
                    FOREIGN KEY (workout_id) REFERENCES workouts(id) ON DELETE CASCADE
                )
            """)
        else:
            # SQLite schema
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS workouts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER DEFAULT 1,
                    exercise_type TEXT NOT NULL,
                    sets INTEGER DEFAULT 0,
                    reps INTEGER DEFAULT 0,
                    duration_seconds INTEGER DEFAULT 0,
                    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    end_time TIMESTAMP NULL,
                    video_path TEXT NULL,
                    details TEXT NULL
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS analysis_details (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    workout_id INTEGER NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    rep_count INTEGER DEFAULT 0,
                    angle REAL DEFAULT NULL,
                    stage TEXT DEFAULT NULL,
                    details TEXT NULL,
                    FOREIGN KEY (workout_id) REFERENCES workouts(id) ON DELETE CASCADE
                )
            """)
        self.connection.commit()
        print(f"Database tables verified successfully [{self.db_type.upper()}]")

    def _exec(self, sql, params=()):
        if not self.connection:
            return None
        if self.db_type == 'sqlite':
            sql = sql.replace('%s', '?')
        cursor = self.connection.cursor()
        cursor.execute(sql, params)
        return cursor

    def log_workout(self, exercise_type, sets=0, reps=0, duration_seconds=0):
        if not self.connection:
            return None
        cursor = self._exec("""
            INSERT INTO workouts (exercise_type, sets, reps, duration_seconds)
            VALUES (%s, %s, %s, %s)
        """, (exercise_type, sets, reps, duration_seconds))
        self.connection.commit()
        workout_id = cursor.lastrowid
        print(f"Workout logged with ID: {workout_id} [{self.db_type.upper()}]")
        return workout_id

    def log_analysis_detail(self, workout_id, rep_count, angle=None, stage=None, details=None):
        if not self.connection or not workout_id:
            return
        details_json = json.dumps(details) if details else None
        self._exec("""
            INSERT INTO analysis_details (workout_id, rep_count, angle, stage, details)
            VALUES (%s, %s, %s, %s, %s)
        """, (workout_id, rep_count, angle, stage, details_json))
        self.connection.commit()

    def update_workout_end(self, workout_id, duration_seconds, video_path=None):
        if not self.connection or not workout_id:
            return
        if self.db_type == 'sqlite':
            self._exec("""
                UPDATE workouts
                SET end_time = CURRENT_TIMESTAMP, duration_seconds = %s, video_path = %s
                WHERE id = %s
            """, (duration_seconds, video_path, workout_id))
        else:
            self._exec("""
                UPDATE workouts
                SET end_time = CURRENT_TIMESTAMP, duration_seconds = %s, video_path = %s
                WHERE id = %s
            """, (duration_seconds, video_path, workout_id))
        self.connection.commit()

    def update_workout_summary(self, workout_id, completed_sets, duration, video_path):
        if not self.connection or not workout_id:
            return
        self._exec("""
            UPDATE workouts
            SET sets = %s, duration_seconds = %s, end_time = CURRENT_TIMESTAMP, video_path = %s
            WHERE id = %s
        """, (completed_sets, duration, video_path, workout_id))
        self.connection.commit()
        print(f"Workout {workout_id} summary updated")

    def _row_to_dict(self, row):
        if row is None:
            return None
        if isinstance(row, dict):
            return row
        return dict(row)

    def _rows_to_dicts(self, rows):
        return [self._row_to_dict(r) for r in rows]

    def get_recent_workouts(self, limit=5):
        if not self.connection:
            return []
        cursor = self._exec("""
            SELECT id, exercise_type, sets, reps, duration_seconds,
                   DATE(start_time) as date, start_time, end_time, video_path
            FROM workouts
            ORDER BY start_time DESC
            LIMIT %s
        """, (limit,))
        return self._rows_to_dicts(cursor.fetchall())

    def get_weekly_stats(self):
        if not self.connection:
            return {}
        if self.db_type == 'mysql':
            cursor = self._exec("""
                SELECT DATE(start_time) as day, COUNT(*) as workout_count,
                       SUM(duration_seconds) as total_duration
                FROM workouts
                WHERE start_time >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
                GROUP BY day
                ORDER BY day
            """)
        else:
            cursor = self._exec("""
                SELECT DATE(start_time) as day, COUNT(*) as workout_count,
                       SUM(duration_seconds) as total_duration
                FROM workouts
                WHERE start_time >= date('now', '-7 days')
                GROUP BY day
                ORDER BY day
            """)
        rows = self._rows_to_dicts(cursor.fetchall())
        return {
            str(stat['day']): {
                'workout_count': stat['workout_count'],
                'total_duration': stat['total_duration'] or 0
            }
            for stat in rows
        }

    def get_exercise_distribution(self):
        if not self.connection:
            return []
        cursor = self._exec("""
            SELECT exercise_type, COUNT(*) as count, AVG(duration_seconds) as avg_duration
            FROM workouts
            GROUP BY exercise_type
        """)
        return self._rows_to_dicts(cursor.fetchall())

    def get_user_stats(self):
        if not self.connection:
            return {'total_workouts': 0, 'total_exercises': 0, 'streak_days': 0}

        cursor = self._exec("""
            SELECT
                COUNT(DISTINCT id) as total_workouts,
                COALESCE(SUM(sets * reps), 0) as total_exercises
            FROM workouts
            WHERE user_id = 1
        """)
        stats = self._row_to_dict(cursor.fetchone()) or {}

        if self.db_type == 'mysql':
            cursor = self._exec("""
                SELECT COUNT(DISTINCT DATE(start_time)) as streak_days
                FROM workouts
                WHERE user_id = 1
                  AND start_time >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
            """)
        else:
            cursor = self._exec("""
                SELECT COUNT(DISTINCT DATE(start_time)) as streak_days
                FROM workouts
                WHERE user_id = 1
                  AND start_time >= date('now', '-30 days')
            """)
        streak_row = self._row_to_dict(cursor.fetchone()) or {}

        return {
            'total_workouts': stats.get('total_workouts', 0),
            'total_exercises': stats.get('total_exercises', 0),
            'streak_days': streak_row.get('streak_days', 0)
        }

    def get_personal_records(self):
        if not self.connection:
            return {}
        records = {}
        cursor = self._exec("""
            SELECT w.exercise_type, MAX(d.rep_count) as max_reps
            FROM workouts w
            JOIN analysis_details d ON w.id = d.workout_id
            GROUP BY w.exercise_type
        """)
        rows = self._rows_to_dicts(cursor.fetchall())
        for r in rows:
            records[r['exercise_type']] = r['max_reps']

        cursor = self._exec("SELECT MAX(duration_seconds) as max_duration FROM workouts")
        row = self._row_to_dict(cursor.fetchone())
        records['max_duration'] = row.get('max_duration', 0) if row else 0
        return records

    def get_yearly_activity(self):
        if not self.connection:
            return []
        if self.db_type == 'mysql':
            cursor = self._exec("""
                SELECT DATE(start_time) as day, COUNT(*) as count
                FROM workouts
                WHERE start_time >= DATE_SUB(CURDATE(), INTERVAL 365 DAY)
                GROUP BY day
                ORDER BY day
            """)
        else:
            cursor = self._exec("""
                SELECT DATE(start_time) as day, COUNT(*) as count
                FROM workouts
                WHERE start_time >= date('now', '-365 days')
                GROUP BY day
                ORDER BY day
            """)
        rows = self._rows_to_dicts(cursor.fetchall())
        return [
            {'day': str(row['day']), 'count': row['count']}
            for row in rows
        ]

    def getAllWorkouts(self):
        if not self.connection:
            return []
        cursor = self._exec("""
            SELECT id, exercise_type, sets, reps, duration_seconds, start_time, end_time, video_path
            FROM workouts
            ORDER BY start_time DESC
        """)
        return self._rows_to_dicts(cursor.fetchall())

    def close(self):
        if self.connection:
            self.connection.close()
            print(f"Database connection closed [{self.db_type.upper() if self.db_type else 'N/A'}]")

