import pymysql
import json
import os

class WorkoutLogger:
    def __init__(self):
        self.connection = None
        self.connect()
        if self.connection:
            self.create_tables()

    def connect(self):
        try:
            self.connection = pymysql.connect(
                host=os.environ.get('DB_HOST', 'localhost'),
                port=int(os.environ.get('DB_PORT', 3306)),
                user=os.environ.get('DB_USER', 'root'),
                password=os.environ.get('DB_PASSWORD', ''),
                database=os.environ.get('DB_NAME', 'sports'),
                cursorclass=pymysql.cursors.DictCursor
            )
            print("Successfully connected to MySQL database")
        except Exception as e:
            print(f"[DB WARNING] Could not connect to MySQL: {e}")
            print("[DB WARNING] App will run without workout logging. Check your .env credentials.")
            self.connection = None

    def create_tables(self):
        if not self.connection:
            return
        with self.connection.cursor() as cursor:
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
            self.connection.commit()
        print("Tables created or verified successfully")

    def log_workout(self, exercise_type, sets=0, reps=0, duration_seconds=0):
        if not self.connection:
            return None
        with self.connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO workouts (exercise_type, sets, reps, duration_seconds)
                VALUES (%s, %s, %s, %s)
            """, (exercise_type, sets, reps, duration_seconds))
            self.connection.commit()
            workout_id = cursor.lastrowid
        print(f"Workout logged with ID: {workout_id}")
        return workout_id

    def log_analysis_detail(self, workout_id, rep_count, angle=None, stage=None, details=None):
        if not self.connection or not workout_id:
            return
        with self.connection.cursor() as cursor:
            details_json = json.dumps(details) if details else None
            cursor.execute("""
                INSERT INTO analysis_details (workout_id, rep_count, angle, stage, details)
                VALUES (%s, %s, %s, %s, %s)
            """, (workout_id, rep_count, angle, stage, details_json))
            self.connection.commit()

    def update_workout_end(self, workout_id, duration_seconds, video_path=None):
        if not self.connection or not workout_id:
            return
        with self.connection.cursor() as cursor:
            cursor.execute("""
                UPDATE workouts
                SET end_time = CURRENT_TIMESTAMP, duration_seconds = %s, video_path = %s
                WHERE id = %s
            """, (duration_seconds, video_path, workout_id))
            self.connection.commit()

    def get_recent_workouts(self, limit=5):
        if not self.connection:
            return []
        # DictCursor is already set on the connection — do NOT pass dictionary=True
        with self.connection.cursor() as cursor:
            cursor.execute("""
                SELECT id, exercise_type, sets, reps, duration_seconds,
                       DATE(start_time) as date, start_time, end_time, video_path
                FROM workouts
                ORDER BY start_time DESC
                LIMIT %s
            """, (limit,))
            return cursor.fetchall()

    def get_weekly_stats(self):
        if not self.connection:
            return {}
        with self.connection.cursor() as cursor:
            cursor.execute("""
                SELECT DATE(start_time) as day, COUNT(*) as workout_count,
                       SUM(duration_seconds) as total_duration
                FROM workouts
                WHERE start_time >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
                GROUP BY day
                ORDER BY day
            """)
            stats = cursor.fetchall()
        return {
            str(stat['day']): {
                'workout_count': stat['workout_count'],
                'total_duration': stat['total_duration'] or 0
            }
            for stat in stats
        }

    def get_exercise_distribution(self):
        if not self.connection:
            return []
        with self.connection.cursor() as cursor:
            cursor.execute("""
                SELECT exercise_type, COUNT(*) as count, AVG(duration_seconds) as avg_duration
                FROM workouts
                GROUP BY exercise_type
            """)
            return cursor.fetchall()

    def get_user_stats(self):
        if not self.connection:
            return {'total_workouts': 0, 'total_exercises': 0, 'streak_days': 0}
        with self.connection.cursor() as cursor:
            cursor.execute("""
                SELECT
                    COUNT(DISTINCT id) as total_workouts,
                    COALESCE(SUM(sets * reps), 0) as total_exercises
                FROM workouts
                WHERE user_id = 1
            """)
            stats = cursor.fetchone() or {}

            # Calculate streak separately to avoid complex subquery issues
            cursor.execute("""
                SELECT COUNT(DISTINCT DATE(start_time)) as streak_days
                FROM workouts
                WHERE user_id = 1
                  AND start_time >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
            """)
            streak_row = cursor.fetchone() or {}

        return {
            'total_workouts': stats.get('total_workouts', 0),
            'total_exercises': stats.get('total_exercises', 0),
            'streak_days': streak_row.get('streak_days', 0)
        }

    def update_workout_summary(self, workout_id, completed_sets, duration, video_path):
        if not self.connection or not workout_id:
            return
        with self.connection.cursor() as cursor:
            cursor.execute("""
                UPDATE workouts
                SET sets = %s, duration_seconds = %s, end_time = CURRENT_TIMESTAMP, video_path = %s
                WHERE id = %s
            """, (completed_sets, duration, video_path, workout_id))
            self.connection.commit()
        print(f"Workout {workout_id} summary updated")

    def close(self):
        if self.connection:
            self.connection.close()
            print("MySQL connection closed")
