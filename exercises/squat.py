import cv2
import numpy as np
from collections import deque
from pose_estimation.angle_calculation import calculate_angle
from utils.panel_utils import draw_warning_panel, draw_info_panel


class Squat:
    def __init__(self):
        self.counter = 0
        self.stage   = None          # None -> "up" -> "down" -> "up"

        # Calibration state variables
        self.calibrated = False
        self.calibration_frames = []
        self.calibration_limit = 25
        self.standing_baseline = 170.0

        # Flexion thresholds (hip → knee → ankle)
        self.angle_up   = 165        # standing (calibrated dynamically)
        self.angle_down = 95         # squat target depth (calibrated dynamically)

        # Hysteresis frame counts
        self._up_frames_count = 0
        self._down_frames_count = 0

        # ── Form thresholds ────────────────────────────────────────────────────
        # Torso lean: shoulder → hip → knee
        self.torso_lean_min = 130

        # Knee symmetry
        self.knee_symmetry_threshold = 25

        # Heel rise
        self.heel_rise_threshold = 0.15

        # Angle smoothing buffer
        self._angle_buf = deque(maxlen=5)

        self.form_warnings = []

    # ── Main tracking ──────────────────────────────────────────────────────────
    def track_squat(self, landmarks, frame):
        h, w = frame.shape[:2]

        def pt(idx):
            return [int(landmarks[idx].x * w), int(landmarks[idx].y * h)]

        def raw(idx):
            """Return raw normalised coords for ratio checks."""
            return landmarks[idx].x, landmarks[idx].y

        # ── Landmarks ─────────────────────────────────────────────────────────
        shoulder_l = pt(11);  shoulder_r = pt(12)
        hip_l      = pt(23);  hip_r      = pt(24)
        knee_l     = pt(25);  knee_r     = pt(26)
        ankle_l    = pt(27);  ankle_r    = pt(28)

        # ── 1. Knee flexion — hip → knee → ankle ──────────────────────────────
        knee_angle_l = calculate_angle(hip_l, knee_l, ankle_l)
        knee_angle_r = calculate_angle(hip_r, knee_r, ankle_r)

        # Use the side with better visibility (higher landmark confidence)
        vis_l = landmarks[25].visibility
        vis_r = landmarks[26].visibility
        if vis_l >= vis_r:
            primary_angle = knee_angle_l
        else:
            primary_angle = knee_angle_r

        # Smooth angle to reduce jitter
        self._angle_buf.append(primary_angle)
        smooth_angle = float(np.mean(self._angle_buf))

        # ── Dynamic Posture Calibration ────────────────────────────────────────
        if not self.calibrated:
            self.calibration_frames.append(smooth_angle)
            scale = max(1.0, min(1.8, h / 960.0))
            
            # Show calibration warning overlay
            self.form_warnings = ["Calibrating... Stand straight"]
            draw_warning_panel(frame, self.form_warnings)
            
            # Left-side calibration info
            draw_info_panel(frame, [
                ("Reps",  "Calibrating",  (200, 200, 200)),
                ("Stage", "Calibrating",  (200, 200, 200)),
                ("Progress", f"{len(self.calibration_frames) * 4}%", (0, 220, 255)),
            ], x_offset=10, y_start=220)
            
            if len(self.calibration_frames) >= self.calibration_limit:
                self.standing_baseline = float(np.mean(self.calibration_frames))
                self.angle_up = min(170.0, self.standing_baseline - 10.0)
                self.angle_down = self.standing_baseline - 70.0
                self.calibrated = True
            
            return self.counter, smooth_angle, "Calibrating"

        # ── 2. Torso lean — shoulder → hip → knee ─────────────────────────────
        torso_l = calculate_angle(shoulder_l, hip_l, knee_l)
        torso_r = calculate_angle(shoulder_r, hip_r, knee_r)
        torso_avg = (torso_l + torso_r) / 2.0

        # ── 3. Knee symmetry ───────────────────────────────────────────────────
        knee_diff = abs(knee_angle_l - knee_angle_r)

        # ── 4. Heel rise — compare ankle y vs knee y ──────────────────────────
        _, ankle_y_l = raw(27);  _, knee_y_l = raw(25)
        _, ankle_y_r = raw(28);  _, knee_y_r = raw(26)
        heel_rise_l = (knee_y_l - ankle_y_l) > self.heel_rise_threshold
        heel_rise_r = (knee_y_r - ankle_y_r) > self.heel_rise_threshold

        # ── Draw skeleton (dynamically scaled) ──────────────────────────────────
        scale = max(1.0, min(1.8, h / 960.0))
        thickness_skeleton = max(1, int(2 * scale))
        joint_radius = max(3, int(7 * scale))
        ring_thickness = max(1, int(1 * scale))
        text_scale = 0.55 * scale
        text_thickness = max(1, int(2 * scale))

        torso_ok    = torso_avg >= self.torso_lean_min
        torso_color = (0, 220, 0) if torso_ok else (0, 140, 255)

        # Torso lines
        cv2.line(frame, tuple(shoulder_l), tuple(hip_l),   torso_color,    thickness_skeleton, cv2.LINE_AA)
        cv2.line(frame, tuple(shoulder_r), tuple(hip_r),   torso_color,    thickness_skeleton, cv2.LINE_AA)

        # Left leg — purple
        cv2.line(frame, tuple(hip_l),  tuple(knee_l),  (178, 102, 255), thickness_skeleton, cv2.LINE_AA)
        cv2.line(frame, tuple(knee_l), tuple(ankle_l), (178, 102, 255), thickness_skeleton, cv2.LINE_AA)

        # Right leg — sky blue
        cv2.line(frame, tuple(hip_r),  tuple(knee_r),  (51, 153, 255), thickness_skeleton, cv2.LINE_AA)
        cv2.line(frame, tuple(knee_r), tuple(ankle_r), (51, 153, 255), thickness_skeleton, cv2.LINE_AA)

        # Joints
        for coord, color in [
            (shoulder_l, torso_color), (shoulder_r, torso_color),
            (hip_l,      torso_color), (hip_r,      torso_color),
            (knee_l,  (178, 102, 255)),(knee_r,  (51, 153, 255)),
            (ankle_l, (178, 102, 255)),(ankle_r, (51, 153, 255)),
        ]:
            cv2.circle(frame, tuple(coord), joint_radius, color, -1, cv2.LINE_AA)
            cv2.circle(frame, tuple(coord), joint_radius, (255,255,255), ring_thickness, cv2.LINE_AA)  # white ring

        # Angle labels near knees
        cv2.putText(frame, f'{int(knee_angle_l)}',
                    (knee_l[0] + int(10 * scale), knee_l[1] - int(10 * scale)),
                    cv2.FONT_HERSHEY_SIMPLEX, text_scale, (255, 255, 0), text_thickness, cv2.LINE_AA)
        cv2.putText(frame, f'{int(knee_angle_r)}',
                    (knee_r[0] + int(10 * scale), knee_r[1] - int(10 * scale)),
                    cv2.FONT_HERSHEY_SIMPLEX, text_scale, (255, 255, 0), text_thickness, cv2.LINE_AA)

        # ── Stage machine with Hysteresis ─────────────────────────────────────
        if smooth_angle > self.angle_up:
            self._up_frames_count += 1
            self._down_frames_count = 0
            if self._up_frames_count >= 3:
                if self.stage == "down":
                    self.counter += 1
                self.stage = "up"
        elif smooth_angle < self.angle_down:
            self._down_frames_count += 1
            self._up_frames_count = 0
            if self._down_frames_count >= 3:
                self.stage = "down"
        else:
            self._up_frames_count = 0
            self._down_frames_count = 0

        stage_label = {
            None:   "Get Ready",
            "up":   "Standing",
            "down": "Squat",
        }.get(self.stage, self.stage)

        # ── Form warnings (right side panel) ──────────────────────────────────
        self.form_warnings = []

        if not torso_ok:
            self.form_warnings.append("Lean forward too much!")

        if knee_diff > self.knee_symmetry_threshold:
            self.form_warnings.append("Knees uneven - check alignment")

        if heel_rise_l or heel_rise_r:
            self.form_warnings.append("Heels rising - keep feet flat")

        # Depth hint only while descending (between up and down thresholds)
        if self.stage == "up" and smooth_angle < self.angle_up and smooth_angle > self.angle_down + 20:
            self.form_warnings.append("Go deeper - aim for 90 deg")

        draw_warning_panel(frame, self.form_warnings)

        # Left-side info panel
        stage_color = (0, 220, 0) if self.stage == "down" else (200, 200, 200)
        draw_info_panel(frame, [
            ("Reps",  self.counter,  (0, 220, 255)),
            ("Stage", stage_label,   stage_color),
            ("Angle", f"{int(smooth_angle)}", (255, 255, 0)),
        ], x_offset=10, y_start=220)

        return self.counter, smooth_angle, stage_label

    def draw_line_with_style(self, frame, start_point, end_point, color, thickness):
        cv2.line(frame, start_point, end_point, color, thickness, lineType=cv2.LINE_AA)

    def draw_circle(self, frame, center, color, radius):
        cv2.circle(frame, center, radius, color, -1)
