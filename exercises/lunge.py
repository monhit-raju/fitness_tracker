import cv2
import numpy as np
from collections import deque
from pose_estimation.angle_calculation import calculate_angle
from utils.panel_utils import draw_warning_panel, draw_info_panel


class Lunge:
    def __init__(self):
        self.counter = 0
        self.stage = None  # None -> "up" -> "down" -> "up"

        # Calibration state
        self.calibrated = False
        self.calibration_frames = []
        self.calibration_limit = 25
        self.standing_baseline = 165.0

        # Angle thresholds (hip -> knee -> ankle)
        self.angle_up = 155.0
        self.angle_down = 100.0

        # Hysteresis frame counts
        self._up_frames_count = 0
        self._down_frames_count = 0

        # Form thresholds
        self.torso_lean_min = 135.0  # Shoulder-Hip-Knee angle

        # Angle smoothing buffer
        self._angle_buf = deque(maxlen=5)
        self.form_warnings = []

    def track_lunge(self, landmarks, frame):
        h, w = frame.shape[:2]

        def pt(idx):
            return [int(landmarks[idx].x * w), int(landmarks[idx].y * h)]

        # Landmarks
        shoulder_l = pt(11); shoulder_r = pt(12)
        hip_l = pt(23);      hip_r = pt(24)
        knee_l = pt(25);     knee_r = pt(26)
        ankle_l = pt(27);    ankle_r = pt(28)
        foot_l = pt(31);     foot_r = pt(32)

        # Calculate knee angles for both legs
        knee_angle_l = calculate_angle(hip_l, knee_l, ankle_l)
        knee_angle_r = calculate_angle(hip_r, knee_r, ankle_r)

        # Primary leg is the one bent lower (smaller angle)
        if knee_angle_l < knee_angle_r:
            primary_angle = knee_angle_l
            lead_knee = knee_l
            lead_ankle = ankle_l
            lead_foot = foot_l
        else:
            primary_angle = knee_angle_r
            lead_knee = knee_r
            lead_ankle = ankle_r
            lead_foot = foot_r

        self._angle_buf.append(primary_angle)
        smooth_angle = float(np.mean(self._angle_buf))

        # Dynamic Calibration
        if not self.calibrated:
            self.calibration_frames.append(smooth_angle)
            self.form_warnings = ["Calibrating... Stand in Lunge starting position"]
            draw_warning_panel(frame, self.form_warnings)

            draw_info_panel(frame, [
                ("Reps", "Calibrating", (200, 200, 200)),
                ("Stage", "Calibrating", (200, 200, 200)),
                ("Progress", f"{len(self.calibration_frames) * 4}%", (0, 220, 255)),
            ], x_offset=10, y_start=220)

            if len(self.calibration_frames) >= self.calibration_limit:
                self.standing_baseline = float(np.mean(self.calibration_frames))
                self.angle_up = min(160.0, self.standing_baseline - 10.0)
                self.angle_down = 105.0
                self.calibrated = True

            return self.counter, smooth_angle, "Calibrating"

        # Torso lean check: shoulder -> hip -> knee
        torso_l = calculate_angle(shoulder_l, hip_l, knee_l)
        torso_r = calculate_angle(shoulder_r, hip_r, knee_r)
        torso_avg = (torso_l + torso_r) / 2.0

        # Form check: Knee past toe (knee X beyond foot X)
        knee_over_toe = abs(lead_knee[0] - lead_foot[0]) > (w * 0.12) and (lead_knee[1] > lead_hip_y if 'lead_hip_y' in locals() else True)

        warnings = []
        if torso_avg < self.torso_lean_min:
            warnings.append("TORSO LEAN: Keep chest upright!")
        if knee_over_toe:
            warnings.append("KNEE OVER TOE: Step longer!")

        if self.stage == "down" and smooth_angle > 115:
            warnings.append("GO DEEPER: Bend knee to 90°")

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

        # Draw skeleton highlights
        scale = max(1.0, min(1.8, h / 960.0))
        thickness_skeleton = max(1, int(2 * scale))
        joint_radius = max(3, int(7 * scale))

        cv2.line(frame, tuple(hip_l), tuple(knee_l), (255, 200, 0), thickness_skeleton, cv2.LINE_AA)
        cv2.line(frame, tuple(knee_l), tuple(ankle_l), (255, 200, 0), thickness_skeleton, cv2.LINE_AA)
        cv2.line(frame, tuple(hip_r), tuple(knee_r), (0, 200, 255), thickness_skeleton, cv2.LINE_AA)
        cv2.line(frame, tuple(knee_r), tuple(ankle_r), (0, 200, 255), thickness_skeleton, cv2.LINE_AA)

        cv2.circle(frame, tuple(knee_l), joint_radius, (255, 255, 255), -1)
        cv2.circle(frame, tuple(knee_r), joint_radius, (255, 255, 255), -1)

        # Draw angle text
        cv2.putText(frame, f"{int(smooth_angle)}deg", (lead_knee[0] + 15, lead_knee[1]),
                    cv2.FONT_HERSHEY_DUPLEX, 0.6 * scale, (255, 255, 255), 2, cv2.LINE_AA)

        draw_info_panel(frame, [
            ("Reps", str(self.counter), (0, 255, 128)),
            ("Knee Angle", f"{int(smooth_angle)}deg", (0, 220, 255)),
            ("Stage", self.stage if self.stage else "Ready", (255, 200, 0)),
        ], x_offset=10, y_start=220)

        return self.counter, smooth_angle, self.stage or "ready"
