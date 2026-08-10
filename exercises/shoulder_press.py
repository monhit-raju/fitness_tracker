import cv2
import numpy as np
from collections import deque
from pose_estimation.angle_calculation import calculate_angle
from utils.panel_utils import draw_warning_panel, draw_info_panel


class ShoulderPress:
    def __init__(self):
        self.counter = 0
        self.stage = None  # None -> "down" -> "up" -> "down"

        # Calibration state
        self.calibrated = False
        self.calibration_frames = []
        self.calibration_limit = 25

        # Arm extension thresholds (Shoulder -> Elbow -> Wrist)
        self.angle_down = 90.0   # Elbows bent at shoulder level
        self.angle_up = 155.0    # Overhead lockout

        # Hysteresis frame counts
        self._up_frames_count = 0
        self._down_frames_count = 0

        # Angle smoothing buffer
        self._angle_buf = deque(maxlen=5)
        self.form_warnings = []

    def track_shoulder_press(self, landmarks, frame):
        h, w = frame.shape[:2]

        def pt(idx):
            return [int(landmarks[idx].x * w), int(landmarks[idx].y * h)]

        # Landmarks
        shoulder_l = pt(11); shoulder_r = pt(12)
        elbow_l = pt(13);    elbow_r = pt(14)
        wrist_l = pt(15);    wrist_r = pt(16)
        hip_l = pt(23);      hip_r = pt(24)

        # Elbow flexion angle (Shoulder -> Elbow -> Wrist)
        angle_l = calculate_angle(shoulder_l, elbow_l, wrist_l)
        angle_r = calculate_angle(shoulder_r, elbow_r, wrist_r)
        avg_angle = (angle_l + angle_r) / 2.0

        self._angle_buf.append(avg_angle)
        smooth_angle = float(np.mean(self._angle_buf))

        # Dynamic Calibration
        if not self.calibrated:
            self.calibration_frames.append(smooth_angle)
            self.form_warnings = ["Calibrating... Hold dumbbells at shoulder level"]
            draw_warning_panel(frame, self.form_warnings)

            draw_info_panel(frame, [
                ("Reps", "Calibrating", (200, 200, 200)),
                ("Stage", "Calibrating", (200, 200, 200)),
                ("Progress", f"{len(self.calibration_frames) * 4}%", (0, 220, 255)),
            ], x_offset=10, y_start=220)

            if len(self.calibration_frames) >= self.calibration_limit:
                self.calibrated = True

            return self.counter, smooth_angle, "Calibrating"

        # Form checks
        warnings = []
        # Asymmetrical press check
        arm_diff = abs(angle_l - angle_r)
        if arm_diff > 25:
            warnings.append("ASYMMETRICAL PRESS: Push evenly!")

        # Elbow flare / low press check
        if self.stage == "up" and smooth_angle < 145:
            warnings.append("FULL LOCKOUT: Extend arms higher!")

        self.form_warnings = warnings
        draw_warning_panel(frame, self.form_warnings)

        # Rep counting logic
        if smooth_angle <= self.angle_down:
            self._down_frames_count += 1
            self._up_frames_count = 0
            if self._down_frames_count >= 2 and self.stage != "down":
                self.stage = "down"
        elif smooth_angle >= self.angle_up:
            self._up_frames_count += 1
            self._down_frames_count = 0
            if self._up_frames_count >= 2 and self.stage == "down":
                self.stage = "up"
                self.counter += 1

        # Draw skeleton
        scale = max(1.0, min(1.8, h / 960.0))
        thickness_skeleton = max(1, int(2 * scale))
        joint_radius = max(3, int(7 * scale))

        # Left arm
        cv2.line(frame, tuple(shoulder_l), tuple(elbow_l), (0, 255, 128), thickness_skeleton, cv2.LINE_AA)
        cv2.line(frame, tuple(elbow_l), tuple(wrist_l), (0, 255, 128), thickness_skeleton, cv2.LINE_AA)

        # Right arm
        cv2.line(frame, tuple(shoulder_r), tuple(elbow_r), (0, 220, 255), thickness_skeleton, cv2.LINE_AA)
        cv2.line(frame, tuple(elbow_r), tuple(wrist_r), (0, 220, 255), thickness_skeleton, cv2.LINE_AA)

        cv2.circle(frame, tuple(elbow_l), joint_radius, (255, 255, 255), -1)
        cv2.circle(frame, tuple(elbow_r), joint_radius, (255, 255, 255), -1)

        draw_info_panel(frame, [
            ("Reps", str(self.counter), (0, 255, 128)),
            ("Arm Angle", f"{int(smooth_angle)}deg", (0, 220, 255)),
            ("Stage", self.stage if self.stage else "Ready", (255, 200, 0)),
        ], x_offset=10, y_start=220)

        return self.counter, smooth_angle, self.stage or "ready"
