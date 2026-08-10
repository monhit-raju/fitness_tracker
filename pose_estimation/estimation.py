import cv2
import mediapipe as mp
from exercises.hammer_curl import HammerCurl

class PoseEstimator:
    def __init__(self):
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose()
        self.mp_drawing = mp.solutions.drawing_utils

    def estimate_pose(self, frame, exercise_type):
        # BGR to RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Pose estimate
        results = self.pose.process(rgb_frame)

        # Draw landmarks and specific connections based on exercise type
        if results.pose_landmarks:
            # Draw specific landmarks and connections based on exercise_type
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

        # Left arm landmarks (shoulder, elbow, hip, wrist)
        shoulder_left = [int(landmarks[12].x * w), int(landmarks[12].y * h)]
        elbow_left = [int(landmarks[14].x * w), int(landmarks[14].y * h)]
        hip_left = [int(landmarks[24].x * w), int(landmarks[24].y * h)]
        wrist_left = [int(landmarks[16].x * w), int(landmarks[16].y * h)]

        # Draw lines with improved style (aliased and scaled)
        cv2.line(frame, tuple(shoulder_left), tuple(elbow_left), (0, 0, 255), thickness, cv2.LINE_AA)
        cv2.line(frame, tuple(elbow_left), tuple(wrist_left), (0, 0, 255), thickness, cv2.LINE_AA)

        cv2.line(frame, tuple(shoulder_right), tuple(elbow_right), (0, 0, 255), thickness, cv2.LINE_AA)
        cv2.line(frame, tuple(elbow_right), tuple(wrist_right), (0, 0, 255), thickness, cv2.LINE_AA)

    def draw_squat_lines(self, frame, landmarks):
        h, w = frame.shape[:2]
        scale = max(1.0, min(1.8, h / 960.0))
        thickness = max(1, int(2 * scale))

        # Squat specific lines (hip, knee, shoulder)
        hip = [int(landmarks[23].x * w), int(landmarks[23].y * h)]
        knee = [int(landmarks[25].x * w), int(landmarks[25].y * h)]
        shoulder = [int(landmarks[11].x * w), int(landmarks[11].y * h)]

        hip_right = [int(landmarks[24].x * w), int(landmarks[24].y * h)]
        knee_right = [int(landmarks[26].x * w), int(landmarks[26].y * h)]
        shoulder_right = [int(landmarks[12].x * w), int(landmarks[12].y * h)]

        # Draw lines for squat (aliased and scaled)
        cv2.line(frame, tuple(shoulder), tuple(hip), (178, 102, 255), thickness, cv2.LINE_AA)
        cv2.line(frame, tuple(hip), tuple(knee), (178, 102, 255), thickness, cv2.LINE_AA)
        cv2.line(frame, tuple(shoulder_right), tuple(hip_right), (51, 153, 255), thickness, cv2.LINE_AA)
        cv2.line(frame, tuple(hip_right), tuple(knee_right), (51, 153, 255), thickness, cv2.LINE_AA)

    def draw_push_up_lines(self, frame, landmarks):
        h, w = frame.shape[:2]
        scale = max(1.0, min(1.8, h / 960.0))
        thickness = max(1, int(2 * scale))

        # Push-up specific lines (shoulder, elbow, wrist)
        shoulder_left = [int(landmarks[11].x * w), int(landmarks[11].y * h)]
        elbow_left = [int(landmarks[13].x * w), int(landmarks[13].y * h)]
        wrist_left = [int(landmarks[15].x * w), int(landmarks[15].y * h)]

        shoulder_right = [int(landmarks[12].x * w), int(landmarks[12].y * h)]
        elbow_right = [int(landmarks[14].x * w), int(landmarks[14].y * h)]
        wrist_right = [int(landmarks[16].x * w), int(landmarks[16].y * h)]

        # Draw lines for push-up (aliased and scaled)
        cv2.line(frame, tuple(shoulder_left), tuple(elbow_left), (0, 0, 255), thickness, cv2.LINE_AA)
        cv2.line(frame, tuple(elbow_left), tuple(wrist_left), (0, 0, 255), thickness, cv2.LINE_AA)
        cv2.line(frame, tuple(shoulder_right), tuple(elbow_right), (102, 0, 0), thickness, cv2.LINE_AA)
        cv2.line(frame, tuple(elbow_right), tuple(wrist_right), (102, 0, 0), thickness, cv2.LINE_AA)
