import cv2
import os
import urllib.request
import logging
import mediapipe as mp

logger = logging.getLogger(__name__)


class PrimaryPoseTracker:
    def __init__(self):
        self.last_center = None
        self.last_area = None

    def get_primary_pose(self, landmarks_list):
        if not landmarks_list:
            return None
        if len(landmarks_list) == 1:
            pose = landmarks_list[0]
            self._update_tracking(pose)
            return pose

        # Multiple poses detected (e.g. 2+ persons)
        candidates = []
        for pose in landmarks_list:
            xs = [lm.x for lm in pose if hasattr(lm, 'visibility') and lm.visibility > 0.25]
            ys = [lm.y for lm in pose if hasattr(lm, 'visibility') and lm.visibility > 0.25]
            if not xs or not ys:
                xs = [lm.x for lm in pose]
                ys = [lm.y for lm in pose]
            
            min_x, max_x = min(xs), max(xs)
            min_y, max_y = min(ys), max(ys)
            cx = (min_x + max_x) / 2.0
            cy = (min_y + max_y) / 2.0
            area = max(0.001, (max_x - min_x) * (max_y - min_y))
            candidates.append({
                'pose': pose,
                'center': (cx, cy),
                'area': area
            })

        if self.last_center is None or self.last_area is None:
            best_candidate = max(candidates, key=lambda c: c['area'])
        else:
            def tracking_score(c):
                dx = c['center'][0] - self.last_center[0]
                dy = c['center'][1] - self.last_center[1]
                dist = (dx*dx + dy*dy) ** 0.5
                area_diff = abs(c['area'] - self.last_area)
                return dist * 0.7 + area_diff * 0.3

            best_candidate = min(candidates, key=tracking_score)

        self.last_center = best_candidate['center']
        self.last_area = best_candidate['area']
        return best_candidate['pose']

    def _update_tracking(self, pose):
        xs = [lm.x for lm in pose if hasattr(lm, 'visibility') and lm.visibility > 0.25]
        ys = [lm.y for lm in pose if hasattr(lm, 'visibility') and lm.visibility > 0.25]
        if xs and ys:
            self.last_center = ((min(xs) + max(xs)) / 2.0, (min(ys) + max(ys)) / 2.0)
            self.last_area = max(0.001, (max(xs) - min(xs)) * (max(ys) - min(ys)))


class PoseResultWrapper:
    def __init__(self, landmarks_list, pose_tracker=None):
        if landmarks_list and len(landmarks_list) > 0:
            if pose_tracker:
                primary_landmarks = pose_tracker.get_primary_pose(landmarks_list)
            else:
                primary_landmarks = landmarks_list[0]
            self.pose_landmarks = type('PoseLandmarks', (), {'landmark': primary_landmarks})()
        else:
            self.pose_landmarks = None


class PoseEstimator:
    def __init__(self):
        self.use_tasks_api = False
        self.pose_tracker = PrimaryPoseTracker()

        if hasattr(mp, 'solutions') and hasattr(mp.solutions, 'pose'):
            try:
                self.mp_pose = mp.solutions.pose
                self.pose = self.mp_pose.Pose()
                self.mp_drawing = mp.solutions.drawing_utils
                logger.info("PoseEstimator using MediaPipe Solutions API")
                return
            except Exception as e:
                logger.warning(f"Failed to initialize MediaPipe Solutions API ({e}). Falling back to Tasks API...")

        # Tasks API Fallback for MediaPipe 0.10.30+ / 1.0.0+ on newer Python versions
        self.use_tasks_api = True
        model_dir = os.path.dirname(__file__)
        self.model_path = os.path.join(model_dir, 'pose_landmarker_lite.task')

        if not os.path.exists(self.model_path):
            logger.info("Downloading pose_landmarker_lite.task model file...")
            url = 'https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/latest/pose_landmarker_lite.task'
            os.makedirs(model_dir, exist_ok=True)
            urllib.request.urlretrieve(url, self.model_path)
            logger.info(f"Model downloaded successfully to {self.model_path}")

        from mediapipe.tasks.python import vision
        from mediapipe.tasks.python.core import base_options

        options = vision.PoseLandmarkerOptions(
            base_options=base_options.BaseOptions(model_asset_path=self.model_path),
            num_poses=4,
            running_mode=vision.RunningMode.IMAGE
        )
        self.detector = vision.PoseLandmarker.create_from_options(options)
        logger.info("PoseEstimator using MediaPipe Tasks API with multi-person tracking")

    def estimate_pose(self, frame, exercise_type):
        if not self.use_tasks_api:
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.pose.process(rgb_frame)
        else:
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
            detection_res = self.detector.detect(mp_image)
            results = PoseResultWrapper(detection_res.pose_landmarks, self.pose_tracker)


        # Draw landmarks and specific connections based on exercise type
        if results.pose_landmarks:
            if exercise_type == "squat":
                self.draw_squat_lines(frame, results.pose_landmarks.landmark)
            elif exercise_type == "push_up":
                self.draw_push_up_lines(frame, results.pose_landmarks.landmark)
            elif exercise_type == "hammer_curl":
                self.draw_hammerl_curl_lines(frame, results.pose_landmarks.landmark)
            elif exercise_type == "lunge":
                self.draw_lunge_lines(frame, results.pose_landmarks.landmark)
            elif exercise_type == "shoulder_press":
                self.draw_shoulder_press_lines(frame, results.pose_landmarks.landmark)

        return results

    def draw_lunge_lines(self, frame, landmarks):
        h, w = frame.shape[:2]
        scale = max(1.0, min(1.8, h / 960.0))
        thickness = max(2, int(3 * scale))

        hip_left = [int(landmarks[23].x * w), int(landmarks[23].y * h)]
        knee_left = [int(landmarks[25].x * w), int(landmarks[25].y * h)]
        ankle_left = [int(landmarks[27].x * w), int(landmarks[27].y * h)]

        hip_right = [int(landmarks[24].x * w), int(landmarks[24].y * h)]
        knee_right = [int(landmarks[26].x * w), int(landmarks[26].y * h)]
        ankle_right = [int(landmarks[28].x * w), int(landmarks[28].y * h)]

        cv2.line(frame, tuple(hip_left), tuple(knee_left), (255, 200, 0), thickness, cv2.LINE_AA)
        cv2.line(frame, tuple(knee_left), tuple(ankle_left), (255, 200, 0), thickness, cv2.LINE_AA)
        cv2.line(frame, tuple(hip_right), tuple(knee_right), (0, 200, 255), thickness, cv2.LINE_AA)
        cv2.line(frame, tuple(knee_right), tuple(ankle_right), (0, 200, 255), thickness, cv2.LINE_AA)

    def draw_shoulder_press_lines(self, frame, landmarks):
        h, w = frame.shape[:2]
        scale = max(1.0, min(1.8, h / 960.0))
        thickness = max(2, int(3 * scale))

        shoulder_left = [int(landmarks[11].x * w), int(landmarks[11].y * h)]
        elbow_left = [int(landmarks[13].x * w), int(landmarks[13].y * h)]
        wrist_left = [int(landmarks[15].x * w), int(landmarks[15].y * h)]

        shoulder_right = [int(landmarks[12].x * w), int(landmarks[12].y * h)]
        elbow_right = [int(landmarks[14].x * w), int(landmarks[14].y * h)]
        wrist_right = [int(landmarks[16].x * w), int(landmarks[16].y * h)]

        cv2.line(frame, tuple(shoulder_left), tuple(elbow_left), (0, 255, 128), thickness, cv2.LINE_AA)
        cv2.line(frame, tuple(elbow_left), tuple(wrist_left), (0, 255, 128), thickness, cv2.LINE_AA)
        cv2.line(frame, tuple(shoulder_right), tuple(elbow_right), (0, 220, 255), thickness, cv2.LINE_AA)
        cv2.line(frame, tuple(elbow_right), tuple(wrist_right), (0, 220, 255), thickness, cv2.LINE_AA)

    def draw_hammerl_curl_lines(self, frame, landmarks):
        h, w = frame.shape[:2]
        scale = max(1.0, min(1.8, h / 960.0))
        thickness = max(2, int(4 * scale))

        shoulder_right = [int(landmarks[11].x * w), int(landmarks[11].y * h)]
        elbow_right = [int(landmarks[13].x * w), int(landmarks[13].y * h)]
        hip_right = [int(landmarks[23].x * w), int(landmarks[23].y * h)]
        wrist_right = [int(landmarks[15].x * w), int(landmarks[15].y * h)]

        shoulder_left = [int(landmarks[12].x * w), int(landmarks[12].y * h)]
        elbow_left = [int(landmarks[14].x * w), int(landmarks[14].y * h)]
        hip_left = [int(landmarks[24].x * w), int(landmarks[24].y * h)]
        wrist_left = [int(landmarks[16].x * w), int(landmarks[16].y * h)]

        cv2.line(frame, tuple(shoulder_left), tuple(elbow_left), (0, 0, 255), thickness, cv2.LINE_AA)
        cv2.line(frame, tuple(elbow_left), tuple(wrist_left), (0, 0, 255), thickness, cv2.LINE_AA)
        cv2.line(frame, tuple(shoulder_right), tuple(elbow_right), (0, 0, 255), thickness, cv2.LINE_AA)
        cv2.line(frame, tuple(elbow_right), tuple(wrist_right), (0, 0, 255), thickness, cv2.LINE_AA)

    def draw_squat_lines(self, frame, landmarks):
        h, w = frame.shape[:2]
        scale = max(1.0, min(1.8, h / 960.0))
        thickness = max(1, int(2 * scale))

        hip = [int(landmarks[23].x * w), int(landmarks[23].y * h)]
        knee = [int(landmarks[25].x * w), int(landmarks[25].y * h)]
        shoulder = [int(landmarks[11].x * w), int(landmarks[11].y * h)]

        hip_right = [int(landmarks[24].x * w), int(landmarks[24].y * h)]
        knee_right = [int(landmarks[26].x * w), int(landmarks[26].y * h)]
        shoulder_right = [int(landmarks[12].x * w), int(landmarks[12].y * h)]

        cv2.line(frame, tuple(shoulder), tuple(hip), (178, 102, 255), thickness, cv2.LINE_AA)
        cv2.line(frame, tuple(hip), tuple(knee), (178, 102, 255), thickness, cv2.LINE_AA)
        cv2.line(frame, tuple(shoulder_right), tuple(hip_right), (51, 153, 255), thickness, cv2.LINE_AA)
        cv2.line(frame, tuple(hip_right), tuple(knee_right), (51, 153, 255), thickness, cv2.LINE_AA)

    def draw_push_up_lines(self, frame, landmarks):
        h, w = frame.shape[:2]
        scale = max(1.0, min(1.8, h / 960.0))
        thickness = max(1, int(2 * scale))

        shoulder_left = [int(landmarks[11].x * w), int(landmarks[11].y * h)]
        elbow_left = [int(landmarks[13].x * w), int(landmarks[13].y * h)]
        wrist_left = [int(landmarks[15].x * w), int(landmarks[15].y * h)]

        shoulder_right = [int(landmarks[12].x * w), int(landmarks[12].y * h)]
        elbow_right = [int(landmarks[14].x * w), int(landmarks[14].y * h)]
        wrist_right = [int(landmarks[16].x * w), int(landmarks[16].y * h)]

        cv2.line(frame, tuple(shoulder_left), tuple(elbow_left), (0, 0, 255), thickness, cv2.LINE_AA)
        cv2.line(frame, tuple(elbow_left), tuple(wrist_left), (0, 0, 255), thickness, cv2.LINE_AA)
        cv2.line(frame, tuple(shoulder_right), tuple(elbow_right), (102, 0, 0), thickness, cv2.LINE_AA)
        cv2.line(frame, tuple(elbow_right), tuple(wrist_right), (102, 0, 0), thickness, cv2.LINE_AA)
