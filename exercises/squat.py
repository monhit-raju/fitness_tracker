import cv2
import numpy as np
from collections import deque
from pose_estimation.angle_calculation import calculate_angle
from utils.panel_utils import draw_warning_panel, draw_info_panel


class Squat:
    def __init__(self):
        self.counter = 0
        self.stage   = None          # None -> "up" -> "down" -> "up"

        # ── Knee flexion thresholds (hip → knee → ankle) ───────────────────────
        # Standing straight: ~170°+   Parallel squat: ~90°   Deep squat: <90°
        self.angle_up   = 165        # above this = standing
        self.angle_down = 95         # below this = squat depth reached

        # ── Form thresholds ────────────────────────────────────────────────────
        # Torso lean: shoulder → hip → knee
        # Normal squat allows some forward lean (~140°+). Flag only excessive lean.
        self.torso_lean_min = 130

        # Knee symmetry: difference between L and R knee angles
        # >25° difference suggests one knee caving or uneven weight
        self.knee_symmetry_threshold = 25

        # Heel rise: ankle visibility — if ankle y-coord rises significantly
        # compared to knee, heels are lifting
        self.heel_rise_threshold = 0.15  # fraction of frame height

        # Angle smoothing buffer (reduces jitter from MediaPipe noise)
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

        # ── 2. Torso lean — shoulder → hip → knee ─────────────────────────────
        torso_l = calculate_angle(shoulder_l, hip_l, knee_l)
        torso_r = calculate_angle(shoulder_r, hip_r, knee_r)
        torso_avg = (torso_l + torso_r) / 2.0

        # ── 3. Knee symmetry ───────────────────────────────────────────────────
        knee_diff = abs(knee_angle_l - knee_angle_r)

        # ── 4. Heel rise — compare ankle y vs knee y ──────────────────────────
        _, ankle_y_l = raw(27);  _, knee_y_l = raw(25)
        _, ankle_y_r = raw(28);  _, knee_y_r = raw(26)
        # In image coords y increases downward, so ankle should be BELOW knee
        # If ankle_y < knee_y the heel has risen
        heel_rise_l = (knee_y_l - ankle_y_l) > self.heel_rise_threshold
        heel_rise_r = (knee_y_r - ankle_y_r) > self.heel_rise_threshold

        # ── Draw skeleton ──────────────────────────────────────────────────────
        torso_ok    = torso_avg >= self.torso_lean_min
        torso_color = (0, 220, 0) if torso_ok else (0, 140, 255)

        # Torso lines
        cv2.line(frame, tuple(shoulder_l), tuple(hip_l),   torso_color,    2, cv2.LINE_AA)
        cv2.line(frame, tuple(shoulder_r), tuple(hip_r),   torso_color,    2, cv2.LINE_AA)

        # Left leg — purple
        cv2.line(frame, tuple(hip_l),  tuple(knee_l),  (178, 102, 255), 2, cv2.LINE_AA)
        cv2.line(frame, tuple(knee_l), tuple(ankle_l), (178, 102, 255), 2, cv2.LINE_AA)

        # Right leg — sky blue
        cv2.line(frame, tuple(hip_r),  tuple(knee_r),  (51, 153, 255), 2, cv2.LINE_AA)
        cv2.line(frame, tuple(knee_r), tuple(ankle_r), (51, 153, 255), 2, cv2.LINE_AA)

        # Joints
        for coord, color in [
            (shoulder_l, torso_color), (shoulder_r, torso_color),
            (hip_l,      torso_color), (hip_r,      torso_color),
            (knee_l,  (178, 102, 255)),(knee_r,  (51, 153, 255)),
            (ankle_l, (178, 102, 255)),(ankle_r, (51, 153, 255)),
        ]:
            cv2.circle(frame, tuple(coord), 7, color, -1)
            cv2.circle(frame, tuple(coord), 7, (255,255,255), 1)  # white ring

        # Angle labels near knees
        cv2.putText(frame, f'{int(knee_angle_l)}',
                    (knee_l[0] + 10, knee_l[1] - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 0), 2, cv2.LINE_AA)
        cv2.putText(frame, f'{int(knee_angle_r)}',
                    (knee_r[0] + 10, knee_r[1] - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 0), 2, cv2.LINE_AA)

        # ── Stage machine — up → down → up ────────────────────────────────────
        # Rep counted when returning to standing (down → up transition)
        if smooth_angle > self.angle_up:
            if self.stage == "down":
                self.counter += 1
            self.stage = "up"
        elif smooth_angle < self.angle_down:
            self.stage = "down"

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
        ], x_offset=10, y_start=160)

        return self.counter, smooth_angle, stage_label

    def draw_line_with_style(self, frame, start_point, end_point, color, thickness):
        cv2.line(frame, start_point, end_point, color, thickness, lineType=cv2.LINE_AA)

    def draw_circle(self, frame, center, color, radius):
        cv2.circle(frame, center, radius, color, -1)
