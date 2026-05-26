from dotenv import load_dotenv
load_dotenv()

from flask import Flask, render_template, Response, request, jsonify, redirect, url_for, send_file
import cv2
import threading
import time
import sys
import traceback
import logging
import os
import uuid
import io
import numpy as np

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
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24))

# Increase max upload size to 200MB
app.config['MAX_CONTENT_LENGTH'] = 200 * 1024 * 1024

ALLOWED_VIDEO_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv', 'webm'}

# Detect cloud environment — no webcam available
IS_CLOUD = bool(
    os.environ.get('RAILWAY_ENVIRONMENT') or
    os.environ.get('RENDER') or
    os.environ.get('DYNO') or          # Heroku
    not os.path.exists('/dev/video0')  # No video device
)
logger.info(f"IS_CLOUD={IS_CLOUD}")

# ── Shared state ───────────────────────────────────────────────────────────────
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

# ── Placeholder frame for cloud ────────────────────────────────────────────────
def _make_placeholder():
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    cv2.putText(img, "Live camera unavailable", (90, 210),
                cv2.FONT_HERSHEY_DUPLEX, 0.8, (200, 200, 200), 2)
    cv2.putText(img, "Switch to Video Upload mode", (75, 260),
                cv2.FONT_HERSHEY_DUPLEX, 0.7, (100, 200, 255), 2)
    cv2.putText(img, "to analyse your workout", (130, 300),
                cv2.FONT_HERSHEY_DUPLEX, 0.65, (100, 200, 255), 2)
    _, buf = cv2.imencode('.jpg', img)
    return buf.tobytes()

# ── Frame generator (local only) ──────────────────────────────────────────────
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
            running  = _state['exercise_running']
            ex_data  = _state['current_exercise_data']
            exercise = _state['current_exercise']
            ex_goal  = _state['exercise_goal']
            sets_goal = _state['sets_goal']
            sets_done = _state['sets_completed']
            workout_id = _state['current_workout_id']
            last_rep   = _state['last_logged_rep']
            writer     = _state['video_writer']

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
                            'left':  {'counter': cl, 'angle': al, 'stage': sl, 'warning': wl, 'progress': pl}
                        }
                        workout_logger.log_analysis_detail(workout_id, new_counter, None, None, details)
                        _set(last_logged_rep=new_counter)
                    _set(exercise_counter=new_counter)

                exercise_info = get_exercise_info(ex_data['type'])
                draw_text_with_background(frame, f"Exercise: {exercise_info.get('name','N/A')}", (40,50),
                                          cv2.FONT_HERSHEY_DUPLEX, 0.7, (255,255,255), (118,29,14), 1)
                draw_text_with_background(frame, f"Reps Goal: {ex_goal}", (40,80),
                                          cv2.FONT_HERSHEY_DUPLEX, 0.7, (255,255,255), (118,29,14), 1)
                draw_text_with_background(frame, f"Sets Goal: {sets_goal}", (40,110),
                                          cv2.FONT_HERSHEY_DUPLEX, 0.7, (255,255,255), (118,29,14), 1)
                draw_text_with_background(frame, f"Current Set: {sets_done+1}", (40,140),
                                          cv2.FONT_HERSHEY_DUPLEX, 0.7, (255,255,255), (118,29,14), 1)

                with _state_lock:
                    if _state['exercise_counter'] >= ex_goal:
                        _state['sets_completed'] += 1
                        _state['exercise_counter'] = 0
                        _state['last_logged_rep'] = 0
                        obj = _state['current_exercise']
                        t   = _state['current_exercise_data']['type']
                        if t in ("squat","push_up"):
                            obj.counter = 0
                        elif t == "hammer_curl":
                            obj.counter_right = 0
                            obj.counter_left  = 0
                        if _state['sets_completed'] >= _state['sets_goal']:
                            _state['exercise_running'] = False
                            draw_text_with_background(frame, "WORKOUT COMPLETE!",
                                (frame.shape[1]//2-150, frame.shape[0]//2),
                                cv2.FONT_HERSHEY_DUPLEX, 1.2, (255,255,255), (0,180,0), 2)
                        else:
                            draw_text_with_background(frame,
                                f"SET {_state['sets_completed']} COMPLETE! Rest 30s",
                                (frame.shape[1]//2-200, frame.shape[0]//2),
                                cv2.FONT_HERSHEY_DUPLEX, 1.0, (255,255,255), (0,0,200), 2)
        else:
            cv2.putText(frame, "Select an exercise to begin",
                        (frame.shape[1]//2-150, frame.shape[0]//2),
                        cv2.FONT_HERSHEY_DUPLEX, 0.8, (255,255,255), 1)

        if writer and writer.isOpened():
            writer.write(frame)

        with _state_lock:
            _state['output_frame'] = frame.copy()

        ret, buffer = cv2.imencode('.jpg', frame)
        if not ret:
            continue
        yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')


# ── Video processing — returns bytes in memory (works on ephemeral filesystems) ─
def process_video_file(input_path, exercise_type, reps_goal, sets_goal_val):
    pose_estimator = PoseEstimator()

    if exercise_type == "squat":
        exercise = Squat()
    elif exercise_type == "push_up":
        exercise = PushUp()
    elif exercise_type == "hammer_curl":
        exercise = HammerCurl()
    else:
        return None, None

    cap = cv2.VideoCapture(input_path)
    if not cap.isOpened():
        return None, None

    fps          = int(cap.get(cv2.CAP_PROP_FPS)) or 30
    frame_width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    # Write to a temp file first, then read back into memory
    unique_id       = str(uuid.uuid4())[:8]
    output_filename = f"processed_{exercise_type}_{unique_id}.mp4"
    output_path     = os.path.join(app.root_path, 'static', 'videos', output_filename)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Try H.264 first, fall back to mp4v
    for codec in ('avc1', 'mp4v', 'XVID'):
        fourcc = cv2.VideoWriter_fourcc(*codec)
        out    = cv2.VideoWriter(output_path, fourcc, fps, (frame_width, frame_height))
        if out.isOpened():
            break
    else:
        cap.release()
        return None, None

    ex_counter    = 0
    sets_done     = 0
    ex_running    = True
    exercise_info = get_exercise_info(exercise_type)
    frame_count   = 0

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

                draw_text_with_background(frame, f"Exercise: {exercise_info.get('name','N/A')}", (40,50),
                                          cv2.FONT_HERSHEY_DUPLEX, 0.7, (255,255,255), (118,29,14), 1)
                draw_text_with_background(frame, f"Reps Goal: {reps_goal}", (40,80),
                                          cv2.FONT_HERSHEY_DUPLEX, 0.7, (255,255,255), (118,29,14), 1)
                draw_text_with_background(frame, f"Sets Goal: {sets_goal_val}", (40,110),
                                          cv2.FONT_HERSHEY_DUPLEX, 0.7, (255,255,255), (118,29,14), 1)
                draw_text_with_background(frame, f"Current Set: {sets_done+1}", (40,140),
                                          cv2.FONT_HERSHEY_DUPLEX, 0.7, (255,255,255), (118,29,14), 1)

                if ex_counter >= reps_goal:
                    sets_done  += 1
                    ex_counter  = 0
                    if exercise_type in ("squat","push_up"):
                        exercise.counter = 0
                    elif exercise_type == "hammer_curl":
                        exercise.counter_right = 0
                        exercise.counter_left  = 0
                    if sets_done >= sets_goal_val:
                        ex_running = False
                        draw_text_with_background(frame, "WORKOUT COMPLETE!",
                            (frame.shape[1]//2-150, frame.shape[0]//2),
                            cv2.FONT_HERSHEY_DUPLEX, 1.2, (255,255,255), (0,180,0), 2)
                    else:
                        draw_text_with_background(frame, f"SET {sets_done} COMPLETE! Rest 30s",
                            (frame.shape[1]//2-200, frame.shape[0]//2),
                            cv2.FONT_HERSHEY_DUPLEX, 1.0, (255,255,255), (0,0,200), 2)
            else:
                draw_text_with_background(frame, "No pose detected", (40,50),
                                          cv2.FONT_HERSHEY_DUPLEX, 0.7, (255,255,255), (118,29,14), 1)
        else:
            draw_text_with_background(frame, "WORKOUT COMPLETE!",
                (frame.shape[1]//2-150, frame.shape[0]//2),
                cv2.FONT_HERSHEY_DUPLEX, 1.2, (255,255,255), (0,180,0), 2)

        if total_frames > 0:
            progress = frame_count / total_frames * 100
            draw_text_with_background(frame, f"Processing: {progress:.1f}%",
                (frame.shape[1]-220, 50),
                cv2.FONT_HERSHEY_DUPLEX, 0.5, (255,255,255), (118,29,14), 1)
        out.write(frame)

    cap.release()
    out.release()

    if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
        logger.warning(f"Output video empty or missing: {output_path}")
        return None, None

    logger.info(f"Processed video saved: {output_path} ({os.path.getsize(output_path)} bytes)")
    return output_path, output_filename


# ── Routes ─────────────────────────────────────────────────────────────────────
@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'cloud': IS_CLOUD}), 200


@app.route('/')
def index():
    return render_template('index.html', is_cloud=IS_CLOUD)


@app.route('/dashboard')
def dashboard():
    try:
        recent_workouts  = workout_logger.get_recent_workouts(5)
        weekly_stats     = workout_logger.get_weekly_stats()
        user_stats       = workout_logger.get_user_stats()

        formatted_workouts = []
        for w in recent_workouts:
            dur = w.get('duration_seconds') or 0
            formatted_workouts.append({
                'date':     str(w.get('date', w.get('start_time', 'N/A'))),
                'exercise': (w.get('exercise_type') or '').replace('_',' ').title(),
                'sets':     w.get('sets', 0),
                'reps':     w.get('reps', 0),
                'duration': f"{dur//60}:{dur%60:02d}"
            })

        weekly_workout_count = sum(v['workout_count'] for v in weekly_stats.values())
        return render_template('dashboard.html',
                               recent_workouts=formatted_workouts,
                               weekly_workouts=weekly_workout_count,
                               total_workouts=user_stats['total_workouts'],
                               total_exercises=user_stats['total_exercises'],
                               streak_days=user_stats['streak_days'])
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        traceback.print_exc()
        return f"Error loading dashboard: {str(e)}", 500


@app.route('/dashboard_data')
def dashboard_data():
    try:
        import datetime
        weekly_stats  = workout_logger.get_weekly_stats()
        exercise_dist = workout_logger.get_exercise_distribution()

        days         = ['Mon','Tue','Wed','Thu','Fri','Sat','Sun']
        weekly_values = [0] * 7
        for day_str, info in weekly_stats.items():
            try:
                d = datetime.date.fromisoformat(day_str)
                weekly_values[d.weekday()] = round((info['total_duration'] or 0) / 60, 1)
            except Exception:
                pass

        return jsonify({
            'success': True,
            'weekly_activity':      {'labels': days, 'values': weekly_values},
            'exercise_distribution': {
                'labels': [r['exercise_type'].replace('_',' ').title() for r in exercise_dist],
                'values': [r['count'] for r in exercise_dist]
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/video_feed')
def video_feed():
    if IS_CLOUD:
        return Response(_make_placeholder(), mimetype='image/jpeg')
    initialize_camera()
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/start_exercise', methods=['POST'])
def start_exercise():
    data          = request.json or {}
    exercise_type = data.get('exercise_type')
    sets_goal_val = int(data.get('sets', 3))
    ex_goal       = int(data.get('reps', 10))

    if IS_CLOUD:
        # On cloud, live exercise tracking is not available
        return jsonify({'success': False,
                        'error': 'Live camera not available on cloud. Please use Video Upload mode.'})

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
    if not workout_id:
        logger.warning("DB unavailable — workout will run without logging")

    camera      = _get('camera')
    video_writer = None
    vid_path    = None
    if camera and camera.isOpened():
        fw  = int(camera.get(cv2.CAP_PROP_FRAME_WIDTH))
        fh  = int(camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
        uid = str(uuid.uuid4())[:8]
        out_path = os.path.join(app.root_path, 'static', 'videos', f"live_{exercise_type}_{uid}.avi")
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        fourcc       = cv2.VideoWriter_fourcc(*'MJPG')
        video_writer = cv2.VideoWriter(out_path, fourcc, 30, (fw, fh))
        if video_writer.isOpened():
            vid_path = out_path
        else:
            video_writer = None

    _set(exercise_running=True, current_exercise=exercise,
         current_exercise_data={'type': exercise_type, 'sets': sets_goal_val, 'reps': ex_goal},
         exercise_counter=0, exercise_goal=ex_goal,
         sets_completed=0, sets_goal=sets_goal_val,
         workout_start_time=time.time(), current_workout_id=workout_id,
         video_writer=video_writer, video_path=vid_path, last_logged_rep=0)

    return jsonify({'success': True})


@app.route('/stop_exercise', methods=['POST'])
def stop_exercise():
    with _state_lock:
        running    = _state['exercise_running']
        ex_data    = _state['current_exercise_data']
        workout_id = _state['current_workout_id']
        start_time = _state['workout_start_time']
        sets_done  = _state['sets_completed']
        ex_counter = _state['exercise_counter']
        writer     = _state['video_writer']
        vid_path   = _state['video_path']

    if running and ex_data and workout_id:
        duration = int(time.time() - start_time) if start_time else 0
        if writer and writer.isOpened():
            writer.release()
        workout_logger.update_workout_summary(
            workout_id, sets_done + (1 if ex_counter > 0 else 0), duration, vid_path)

    _set(exercise_running=False, current_workout_id=None, video_path=None, video_writer=None)
    return jsonify({'success': True})


@app.route('/get_status')
def get_status():
    with _state_lock:
        return jsonify({
            'exercise_running': _state['exercise_running'],
            'current_reps':     _state['exercise_counter'],
            'current_set':      _state['sets_completed'] + 1 if _state['exercise_running'] else 0,
            'total_sets':       _state['sets_goal'],
            'rep_goal':         _state['exercise_goal'],
        })


@app.route('/upload_video', methods=['POST'])
def upload_video():
    try:
        exercise_type = request.form.get('exercise_type')
        sets_val      = int(request.form.get('sets', 3))
        reps_val      = int(request.form.get('reps', 10))

        if 'video' not in request.files:
            return jsonify({'success': False, 'error': 'No video file provided'})
        file = request.files['video']
        if not file.filename:
            return jsonify({'success': False, 'error': 'No video file selected'})
        if not _allowed_video(file.filename):
            return jsonify({'success': False,
                            'error': f'Invalid file type. Allowed: {", ".join(ALLOWED_VIDEO_EXTENSIONS)}'})
        if exercise_type not in ('squat', 'push_up', 'hammer_curl'):
            return jsonify({'success': False, 'error': 'Invalid exercise type'})

        # Save uploaded file to temp location
        temp_path = os.path.join(app.root_path, 'static', 'videos', f"temp_{uuid.uuid4()}.mp4")
        os.makedirs(os.path.dirname(temp_path), exist_ok=True)
        file.save(temp_path)
        logger.info(f"Saved upload: {temp_path} ({os.path.getsize(temp_path)} bytes)")

        output_path, output_filename = process_video_file(temp_path, exercise_type, reps_val, sets_val)

        # Clean up temp file
        if os.path.exists(temp_path):
            os.remove(temp_path)

        if not output_path:
            return jsonify({'success': False, 'error': 'Failed to process video. Check pose is visible.'})

        # Return URL — works on both local and Railway (ephemeral but valid for current session)
        video_url = url_for('serve_video', filename=output_filename)
        return jsonify({'success': True, 'video_url': video_url})

    except Exception as e:
        logger.error(f"upload_video error: {e}")
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)})


@app.route('/video/<filename>')
def serve_video(filename):
    """Serve processed video — works even on ephemeral Railway filesystem."""
    video_path = os.path.join(app.root_path, 'static', 'videos', filename)
    if not os.path.exists(video_path):
        return jsonify({'error': 'Video not found'}), 404
    return send_file(video_path, mimetype='video/mp4',
                     as_attachment=False,
                     download_name=filename)


@app.route('/profile')
def profile():
    return redirect(url_for('dashboard'))


if __name__ == '__main__':
    port  = int(os.environ.get('PORT', 5000))
    debug = not IS_CLOUD
    logger.info(f"Starting on port {port}, IS_CLOUD={IS_CLOUD}")
    app.run(host='0.0.0.0', port=port, debug=debug, threaded=True)
