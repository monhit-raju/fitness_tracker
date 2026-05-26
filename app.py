from dotenv import load_dotenv
load_dotenv()  # Load .env file before anything else reads os.environ

from flask import Flask, render_template, Response, request, jsonify, redirect, url_for
import cv2
import threading
import time
import sys
import traceback
import logging
import os
import uuid

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    handlers=[logging.StreamHandler()])
logger = logging.getLogger(__name__)

try:
    from pose_estimation.estimation import PoseEstimator
    from exercises.squat import Squat
    from exercises.hammer_curl import HammerCurl
    from exercises.push_up import PushUp
    from feedback.information import get_exercise_info
    from feedback.layout import layout_indicators
    from utils.draw_text_with_background import draw_text_with_background
    logger.info("Successfully imported pose estimation modules")
except ImportError as e:
    logger.error(f"Failed to import required modules: {e}")
    traceback.print_exc()
    sys.exit(1)

from db.workout_logger import WorkoutLogger
workout_logger = WorkoutLogger()

app = Flask(__name__)
# Load secret key from environment variable; fall back to a random key for dev
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24))

ALLOWED_VIDEO_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv', 'webm'}

# ── Shared state protected by a lock ──────────────────────────────────────────
_state_lock = threading.Lock()
_state = {
    'camera': None,
    'output_frame': None,
    'exercise_running': False,
    'current_exercise': None,
    'current_exercise_data': None,
    'exercise_counter': 0,
    'exercise_goal': 0,
    'sets_completed': 0,
    'sets_goal': 0,
    'workout_start_time': None,
    'current_workout_id': None,
    'video_writer': None,
    'video_path': None,
    'last_logged_rep': 0,
}

def _get(key):
    with _state_lock:
        return _state[key]

def _set(**kwargs):
    with _state_lock:
        _state.update(kwargs)

# ── Camera helpers ─────────────────────────────────────────────────────────────
# On Railway/cloud there is no webcam — detect this gracefully
IS_CLOUD = os.environ.get('RAILWAY_ENVIRONMENT') or os.environ.get('RENDER') or not os.environ.get('DISPLAY', True)

def initialize_camera():
    if IS_CLOUD:
        return None
    with _state_lock:
        if _state['camera'] is None:
            cam = cv2.VideoCapture(0)
            if cam.isOpened():
                _state['camera'] = cam
    return _get('camera')

def release_camera():
    with _state_lock:
        if _state['camera'] is not None:
            _state['camera'].release()
            _state['camera'] = None

def _allowed_video(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_VIDEO_EXTENSIONS

# ── Frame generator ────────────────────────────────────────────────────────────
def generate_frames():
    pose_estimator = PoseEstimator()

    while True:
        camera = _get('camera')
        if camera is None:
            time.sleep(0.05)
            continue

        success, frame = camera.read()
        if not success:
            time.sleep(0.05)
            continue

        with _state_lock:
            running = _state['exercise_running']
            ex_data = _state['current_exercise_data']
            exercise = _state['current_exercise']
            ex_goal = _state['exercise_goal']
            sets_goal = _state['sets_goal']
            sets_done = _state['sets_completed']
            workout_id = _state['current_workout_id']
            last_rep = _state['last_logged_rep']
            writer = _state['video_writer']

        if running and exercise and ex_data:
            results = pose_estimator.estimate_pose(frame, ex_data['type'])

            if results.pose_landmarks:
                ex_type = ex_data['type']

                if ex_type == "squat":
                    counter, angle, stage = exercise.track_squat(results.pose_landmarks.landmark, frame)
                    layout_indicators(frame, ex_type, (counter, angle, stage))
                    if counter > last_rep and workout_id:
                        workout_logger.log_analysis_detail(workout_id, counter, angle, stage)
                        _set(last_logged_rep=counter)
                    _set(exercise_counter=counter)

                elif ex_type == "push_up":
                    counter, angle, stage = exercise.track_push_up(results.pose_landmarks.landmark, frame)
                    layout_indicators(frame, ex_type, (counter, angle, stage))
                    if counter > last_rep and workout_id:
                        workout_logger.log_analysis_detail(workout_id, counter, angle, stage)
                        _set(last_logged_rep=counter)
                    _set(exercise_counter=counter)

                elif ex_type == "hammer_curl":
                    (cr, ar, cl, al, wr, wl, pr, pl, sr, sl) = exercise.track_hammer_curl(
                        results.pose_landmarks.landmark, frame)
                    layout_indicators(frame, ex_type, (cr, ar, cl, al, wr, wl, pr, pl, sr, sl))
                    new_counter = max(cr, cl)
                    if new_counter > last_rep and workout_id:
                        details = {
                            'right': {'counter': cr, 'angle': ar, 'stage': sr, 'warning': wr, 'progress': pr},
                            'left': {'counter': cl, 'angle': al, 'stage': sl, 'warning': wl, 'progress': pl}
                        }
                        workout_logger.log_analysis_detail(workout_id, new_counter, None, None, details)
                        _set(last_logged_rep=new_counter)
                    _set(exercise_counter=new_counter)

                exercise_info = get_exercise_info(ex_data['type'])
                draw_text_with_background(frame, f"Exercise: {exercise_info.get('name', 'N/A')}", (40, 50),
                                          cv2.FONT_HERSHEY_DUPLEX, 0.7, (255, 255, 255), (118, 29, 14), 1)
                draw_text_with_background(frame, f"Reps Goal: {ex_goal}", (40, 80),
                                          cv2.FONT_HERSHEY_DUPLEX, 0.7, (255, 255, 255), (118, 29, 14), 1)
                draw_text_with_background(frame, f"Sets Goal: {sets_goal}", (40, 110),
                                          cv2.FONT_HERSHEY_DUPLEX, 0.7, (255, 255, 255), (118, 29, 14), 1)
                draw_text_with_background(frame, f"Current Set: {sets_done + 1}", (40, 140),
                                          cv2.FONT_HERSHEY_DUPLEX, 0.7, (255, 255, 255), (118, 29, 14), 1)

                with _state_lock:
                    current_counter = _state['exercise_counter']
                    if current_counter >= ex_goal:
                        _state['sets_completed'] += 1
                        _state['exercise_counter'] = 0
                        _state['last_logged_rep'] = 0
                        ex_type = _state['current_exercise_data']['type']
                        ex_obj = _state['current_exercise']
                        if ex_type in ("squat", "push_up"):
                            ex_obj.counter = 0
                        elif ex_type == "hammer_curl":
                            ex_obj.counter_right = 0
                            ex_obj.counter_left = 0

                        if _state['sets_completed'] >= _state['sets_goal']:
                            _state['exercise_running'] = False
                            draw_text_with_background(frame, "WORKOUT COMPLETE!",
                                                      (frame.shape[1] // 2 - 150, frame.shape[0] // 2),
                                                      cv2.FONT_HERSHEY_DUPLEX, 1.2, (255, 255, 255), (0, 180, 0), 2)
                        else:
                            draw_text_with_background(
                                frame,
                                f"SET {_state['sets_completed']} COMPLETE! Rest 30s",
                                (frame.shape[1] // 2 - 200, frame.shape[0] // 2),
                                cv2.FONT_HERSHEY_DUPLEX, 1.0, (255, 255, 255), (0, 0, 200), 2)
        else:
            cv2.putText(frame, "Select an exercise to begin",
                        (frame.shape[1] // 2 - 150, frame.shape[0] // 2),
                        cv2.FONT_HERSHEY_DUPLEX, 0.8, (255, 255, 255), 1)

        if writer and writer.isOpened():
            writer.write(frame)

        with _state_lock:
            _state['output_frame'] = frame.copy()

        ret, buffer = cv2.imencode('.jpg', frame)
        if not ret:
            continue
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')


def process_video_file(input_path, exercise_type, reps_goal, sets_goal_val):
    pose_estimator = PoseEstimator()

    if exercise_type == "squat":
        exercise = Squat()
    elif exercise_type == "push_up":
        exercise = PushUp()
    elif exercise_type == "hammer_curl":
        exercise = HammerCurl()
    else:
        return None

    cap = cv2.VideoCapture(input_path)
    if not cap.isOpened():
        return None

    fps = int(cap.get(cv2.CAP_PROP_FPS)) or 30
    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    unique_id = str(uuid.uuid4())[:8]
    output_filename = f"processed_{exercise_type}_{unique_id}.mp4"
    output_path = os.path.join(app.root_path, 'static', 'videos', output_filename)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    fourcc = cv2.VideoWriter_fourcc(*'avc1')  # H.264 — browser-compatible
    out = cv2.VideoWriter(output_path, fourcc, fps, (frame_width, frame_height))
    if not out.isOpened():
        # Fallback to mp4v if avc1 not available
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, fps, (frame_width, frame_height))
    if not out.isOpened():
        cap.release()
        return None

    ex_counter = 0
    sets_done = 0
    ex_running = True
    exercise_info = get_exercise_info(exercise_type)
    frame_count = 0

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        frame_count += 1

        if ex_running:
            results = pose_estimator.estimate_pose(frame, exercise_type)
            if results.pose_landmarks:
                if exercise_type == "squat":
                    counter, angle, stage = exercise.track_squat(results.pose_landmarks.landmark, frame)
                    layout_indicators(frame, exercise_type, (counter, angle, stage))
                    ex_counter = counter
                elif exercise_type == "push_up":
                    counter, angle, stage = exercise.track_push_up(results.pose_landmarks.landmark, frame)
                    layout_indicators(frame, exercise_type, (counter, angle, stage))
                    ex_counter = counter
                elif exercise_type == "hammer_curl":
                    (cr, ar, cl, al, wr, wl, pr, pl, sr, sl) = exercise.track_hammer_curl(
                        results.pose_landmarks.landmark, frame)
                    layout_indicators(frame, exercise_type, (cr, ar, cl, al, wr, wl, pr, pl, sr, sl))
                    ex_counter = max(cr, cl)

                draw_text_with_background(frame, f"Exercise: {exercise_info.get('name', 'N/A')}", (40, 50),
                                          cv2.FONT_HERSHEY_DUPLEX, 0.7, (255, 255, 255), (118, 29, 14), 1)
                draw_text_with_background(frame, f"Reps Goal: {reps_goal}", (40, 80),
                                          cv2.FONT_HERSHEY_DUPLEX, 0.7, (255, 255, 255), (118, 29, 14), 1)
                draw_text_with_background(frame, f"Sets Goal: {sets_goal_val}", (40, 110),
                                          cv2.FONT_HERSHEY_DUPLEX, 0.7, (255, 255, 255), (118, 29, 14), 1)
                draw_text_with_background(frame, f"Current Set: {sets_done + 1}", (40, 140),
                                          cv2.FONT_HERSHEY_DUPLEX, 0.7, (255, 255, 255), (118, 29, 14), 1)

                if ex_counter >= reps_goal:
                    sets_done += 1
                    ex_counter = 0
                    if exercise_type in ("squat", "push_up"):
                        exercise.counter = 0
                    elif exercise_type == "hammer_curl":
                        exercise.counter_right = 0
                        exercise.counter_left = 0

                    if sets_done >= sets_goal_val:
                        ex_running = False
                        draw_text_with_background(frame, "WORKOUT COMPLETE!",
                                                  (frame.shape[1] // 2 - 150, frame.shape[0] // 2),
                                                  cv2.FONT_HERSHEY_DUPLEX, 1.2, (255, 255, 255), (0, 180, 0), 2)
                    else:
                        draw_text_with_background(frame, f"SET {sets_done} COMPLETE! Rest 30s",
                                                  (frame.shape[1] // 2 - 200, frame.shape[0] // 2),
                                                  cv2.FONT_HERSHEY_DUPLEX, 1.0, (255, 255, 255), (0, 0, 200), 2)
            else:
                draw_text_with_background(frame, "No pose detected", (40, 50),
                                          cv2.FONT_HERSHEY_DUPLEX, 0.7, (255, 255, 255), (118, 29, 14), 1)
        else:
            draw_text_with_background(frame, "WORKOUT COMPLETE!",
                                      (frame.shape[1] // 2 - 150, frame.shape[0] // 2),
                                      cv2.FONT_HERSHEY_DUPLEX, 1.2, (255, 255, 255), (0, 180, 0), 2)

        if total_frames > 0:
            progress = frame_count / total_frames * 100
            draw_text_with_background(frame, f"Processing: {progress:.1f}%",
                                      (frame.shape[1] - 220, 50),
                                      cv2.FONT_HERSHEY_DUPLEX, 0.5, (255, 255, 255), (118, 29, 14), 1)

        out.write(frame)

    cap.release()
    out.release()

    if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
        logger.warning(f"Processed video not created or empty: {output_path}")
        return None

    logger.info(f"Processed video saved: {output_path}")
    return output_path


# ── Routes ─────────────────────────────────────────────────────────────────────
@app.route('/health')
def health():
    return jsonify({'status': 'ok'}), 200


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/dashboard')
def dashboard():
    try:
        recent_workouts = workout_logger.get_recent_workouts(5)
        weekly_stats = workout_logger.get_weekly_stats()
        user_stats = workout_logger.get_user_stats()

        formatted_workouts = []
        for w in recent_workouts:
            dur = w.get('duration_seconds') or 0
            formatted_workouts.append({
                'date': str(w.get('date', w.get('start_time', 'N/A'))),
                'exercise': (w.get('exercise_type') or '').replace('_', ' ').title(),
                'sets': w.get('sets', 0),
                'reps': w.get('reps', 0),
                'duration': f"{dur // 60}:{dur % 60:02d}"
            })

        weekly_workout_count = sum(v['workout_count'] for v in weekly_stats.values())

        return render_template('dashboard.html',
                               recent_workouts=formatted_workouts,
                               weekly_workouts=weekly_workout_count,
                               total_workouts=user_stats['total_workouts'],
                               total_exercises=user_stats['total_exercises'],
                               streak_days=user_stats['streak_days'])
    except Exception as e:
        logger.error(f"Error in dashboard: {e}")
        traceback.print_exc()
        return f"Error loading dashboard: {str(e)}", 500


@app.route('/dashboard_data')
def dashboard_data():
    """JSON endpoint for real chart data used by dashboard.js."""
    try:
        weekly_stats = workout_logger.get_weekly_stats()
        exercise_dist = workout_logger.get_exercise_distribution()

        days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        weekly_values = [0] * 7
        for day_str, info in weekly_stats.items():
            try:
                import datetime
                d = datetime.date.fromisoformat(day_str)
                weekly_values[d.weekday()] = round((info['total_duration'] or 0) / 60, 1)
            except Exception:
                pass

        ex_labels = [r['exercise_type'].replace('_', ' ').title() for r in exercise_dist]
        ex_values = [r['count'] for r in exercise_dist]

        return jsonify({
            'success': True,
            'weekly_activity': {'labels': days, 'values': weekly_values},
            'exercise_distribution': {'labels': ex_labels, 'values': ex_values}
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/video_feed')
def video_feed():
    if IS_CLOUD:
        # No webcam on cloud — return a single placeholder JPEG
        import numpy as np
        placeholder = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.putText(placeholder, "Live camera not available", (80, 220),
                    cv2.FONT_HERSHEY_DUPLEX, 0.8, (200, 200, 200), 2)
        cv2.putText(placeholder, "Use Video Upload mode instead", (70, 270),
                    cv2.FONT_HERSHEY_DUPLEX, 0.7, (100, 200, 255), 2)
        _, buf = cv2.imencode('.jpg', placeholder)
        return Response(buf.tobytes(), mimetype='image/jpeg')
    initialize_camera()
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/start_exercise', methods=['POST'])
def start_exercise():
    data = request.json or {}
    exercise_type = data.get('exercise_type')
    sets_goal_val = int(data.get('sets', 3))
    ex_goal = int(data.get('reps', 10))

    initialize_camera()

    if exercise_type == "squat":
        exercise = Squat()
    elif exercise_type == "push_up":
        exercise = PushUp()
    elif exercise_type == "hammer_curl":
        exercise = HammerCurl()
    else:
        return jsonify({'success': False, 'error': 'Invalid exercise type'})

    workout_id = workout_logger.log_workout(exercise_type, sets_goal_val, ex_goal, 0)
    # DB logging is optional — don't block the workout if DB is unavailable
    if not workout_id:
        logger.warning("DB unavailable — workout will run without logging")

    # Set up video writer
    camera = _get('camera')
    video_writer = None
    vid_path = None
    if camera and camera.isOpened():
        fw = int(camera.get(cv2.CAP_PROP_FRAME_WIDTH))
        fh = int(camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
        uid = str(uuid.uuid4())[:8]
        out_filename = f"live_{exercise_type}_{uid}.avi"
        out_path = os.path.join(app.root_path, 'static', 'videos', out_filename)
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        fourcc = cv2.VideoWriter_fourcc(*'MJPG')
        video_writer = cv2.VideoWriter(out_path, fourcc, 30, (fw, fh))
        if video_writer.isOpened():
            vid_path = out_path
        else:
            video_writer = None

    _set(
        exercise_running=True,
        current_exercise=exercise,
        current_exercise_data={'type': exercise_type, 'sets': sets_goal_val, 'reps': ex_goal},
        exercise_counter=0,
        exercise_goal=ex_goal,
        sets_completed=0,
        sets_goal=sets_goal_val,
        workout_start_time=time.time(),
        current_workout_id=workout_id,
        video_writer=video_writer,
        video_path=vid_path,
        last_logged_rep=0,
    )

    return jsonify({'success': True})


@app.route('/stop_exercise', methods=['POST'])
def stop_exercise():
    with _state_lock:
        running = _state['exercise_running']
        ex_data = _state['current_exercise_data']
        workout_id = _state['current_workout_id']
        start_time = _state['workout_start_time']
        sets_done = _state['sets_completed']
        ex_counter = _state['exercise_counter']
        writer = _state['video_writer']
        vid_path = _state['video_path']

    if running and ex_data and workout_id:
        duration = int(time.time() - start_time) if start_time else 0
        if writer and writer.isOpened():
            writer.release()
        completed_sets = sets_done + (1 if ex_counter > 0 else 0)
        workout_logger.update_workout_summary(workout_id, completed_sets, duration, vid_path)

    _set(exercise_running=False, current_workout_id=None, video_path=None, video_writer=None)
    return jsonify({'success': True})


@app.route('/get_status', methods=['GET'])
def get_status():
    with _state_lock:
        return jsonify({
            'exercise_running': _state['exercise_running'],
            'current_reps': _state['exercise_counter'],
            'current_set': _state['sets_completed'] + 1 if _state['exercise_running'] else 0,
            'total_sets': _state['sets_goal'],
            'rep_goal': _state['exercise_goal'],
        })


@app.route('/upload_video', methods=['POST'])
def upload_video():
    try:
        exercise_type = request.form.get('exercise_type')
        sets_val = int(request.form.get('sets', 3))
        reps_val = int(request.form.get('reps', 10))

        if 'video' not in request.files:
            return jsonify({'success': False, 'error': 'No video file provided'})

        file = request.files['video']
        if not file.filename:
            return jsonify({'success': False, 'error': 'No video file selected'})

        # Validate file extension
        if not _allowed_video(file.filename):
            return jsonify({'success': False,
                            'error': f'Invalid file type. Allowed: {", ".join(ALLOWED_VIDEO_EXTENSIONS)}'})

        if exercise_type not in ('squat', 'push_up', 'hammer_curl'):
            return jsonify({'success': False, 'error': 'Invalid exercise type'})

        temp_filename = f"temp_{uuid.uuid4()}.mp4"
        temp_path = os.path.join(app.root_path, 'static', 'videos', temp_filename)
        os.makedirs(os.path.dirname(temp_path), exist_ok=True)
        file.save(temp_path)

        output_path = process_video_file(temp_path, exercise_type, reps_val, sets_val)

        if os.path.exists(temp_path):
            os.remove(temp_path)

        if output_path:
            # Build URL relative to the static folder
            rel = os.path.relpath(output_path, os.path.join(app.root_path, 'static'))
            video_url = url_for('static', filename=rel.replace(os.sep, '/'))
            return jsonify({'success': True, 'video_url': video_url})
        else:
            return jsonify({'success': False, 'error': 'Failed to process video'})

    except Exception as e:
        logger.error(f"Error in upload_video: {e}")
        return jsonify({'success': False, 'error': str(e)})


@app.route('/profile')
def profile():
    return redirect(url_for('dashboard'))


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = not IS_CLOUD
    logger.info(f"Starting app on port {port}")
    app.run(host='0.0.0.0', port=port, debug=debug, threaded=True)
