import cv2
import numpy as np
from collections import deque
from pose_estimation.angle_calculation import calculate_angle
from utils.panel_utils import draw_warning_panel, draw_info_panel


class HammerCurl:
    def __init__(self):
        self.counter_right = 0
        self.counter_left  = 0
        self.stage_right   = None    # None -> "down" -> "up" -> "down"
        self.stage_left    = None

        # Calibration state variables
        self.calibrated = False
        self.calibration_frames = []
        self.calibration_limit = 25
        self.standing_baseline = 160.0

        # Elbow flexion thresholds
        self.angle_down = 155        # extended (calibrated dynamically)
        self.angle_up   = 50         # curled (calibrated dynamically)

        # Hysteresis frame counts
        self._up_frames_r = 0
        self._down_frames_r = 0
        self._up_frames_l = 0
        self._down_frames_l = 0

        # ── Form thresholds ────────────────────────────────────────────────────
        self.swing_threshold = 40
        self.sway_min = 155
        self.shrug_threshold = 0.04

        # Angle smoothing per arm
        self._buf_r = deque(maxlen=5)
        self._buf_l = deque(maxlen=5)

        # Shoulder baseline y
        self._shoulder_base_r = None
        self._shoulder_base_l = None

        self.form_warnings = []

    # ── Main tracking ──────────────────────────────────────────────────────────
    def track_hammer_curl(self, landmarks, frame):
        h, w = frame.shape[:2]

        def pt(idx):
            return [int(landmarks[idx].x * w), int(landmarks[idx].y * h)]

        def raw_y(idx):
            return landmarks[idx].y   # normalised 0-1

        # ── Landmarks ─────────────────────────────────────────────────────────
        # MediaPipe: 11=L-shoulder, 12=R-shoulder (from person's perspective)
        # We label them as they appear on screen for the user
        shoulder_r = pt(11);  shoulder_l = pt(12)
        elbow_r    = pt(13);  elbow_l    = pt(14)
        wrist_r    = pt(15);  wrist_l    = pt(16)
        hip_r      = pt(23);  hip_l      = pt(24)
        knee_r     = pt(25);  knee_l     = pt(26)

        # ── 1. Elbow flexion — shoulder → elbow → wrist ───────────────────────
        raw_angle_r = calculate_angle(shoulder_r, elbow_r, wrist_r)
        raw_angle_l = calculate_angle(shoulder_l, elbow_l, wrist_l)

        self._buf_r.append(raw_angle_r)
        self._buf_l.append(raw_angle_l)
        angle_r = float(np.mean(self._buf_r))
        angle_l = float(np.mean(self._buf_l))

        # ── Dynamic Posture Calibration ────────────────────────────────────────
        if not self.calibrated:
            self.calibration_frames.append((angle_r + angle_l) / 2.0)
            scale = max(1.0, min(1.8, h / 960.0))
            
            # Show calibration warning overlay
            self.form_warnings = ["Calibrating... Let arms hang"]
            draw_warning_panel(frame, self.form_warnings)
            
            # Left-side calibration info
            draw_info_panel(frame, [
                ("R Reps",  "Calibrating",  (200, 200, 200)),
                ("L Reps",  "Calibrating",  (200, 200, 200)),
                ("Progress", f"{len(self.calibration_frames) * 4}%", (0, 220, 255)),
            ], x_offset=10, y_start=220)
            
            if len(self.calibration_frames) >= self.calibration_limit:
                self.standing_baseline = float(np.mean(self.calibration_frames))
                self.angle_down = min(168.0, self.standing_baseline - 5.0)
                self.angle_up = 50.0  # curl depth is fixed at 50 degrees
                self.calibrated = True
                
                # Calibrate shoulder base heights
                self._shoulder_base_r = raw_y(11)
                self._shoulder_base_l = raw_y(12)
            
            # Return dummy values for calibration frame
            return (0, angle_r, 0, angle_l, None, None, 0, 0, "Calibrating", "Calibrating")

        # ── 2. Upper arm swing — hip → shoulder → elbow ───────────────────────
        swing_r = calculate_angle(hip_r, shoulder_r, elbow_r)
        swing_l = calculate_angle(hip_l, shoulder_l, elbow_l)

        # ── 3. Body sway — shoulder → hip → knee ──────────────────────────────
        sway_r = calculate_angle(shoulder_r, hip_r, knee_r)
        sway_l = calculate_angle(shoulder_l, hip_l, knee_l)
        sway_avg = (sway_r + sway_l) / 2.0

        # ── 4. Shoulder shrug — track y movement ──────────────────────────────
        sy_r = raw_y(11);  sy_l = raw_y(12)
        if self._shoulder_base_r is None:
            self._shoulder_base_r = sy_r
            self._shoulder_base_l = sy_l
        shrug_r = (self._shoulder_base_r - sy_r) > self.shrug_threshold
        shrug_l = (self._shoulder_base_l - sy_l) > self.shrug_threshold

        # ── Draw skeleton (dynamically scaled) ──────────────────────────────────
        scale = max(1.0, min(1.8, h / 960.0))
        thickness_skeleton = max(1, int(2 * scale))
        joint_radius = max(3, int(7 * scale))
        ring_thickness = max(1, int(1 * scale))
        text_scale = 0.55 * scale
        text_thickness = max(1, int(2 * scale))

        body_ok    = sway_avg >= self.sway_min
        body_color = (0, 220, 0) if body_ok else (0, 140, 255)

        # Right arm — orange
        r_color = (0, 140, 255)
        cv2.line(frame, tuple(shoulder_r), tuple(elbow_r), r_color, thickness_skeleton, cv2.LINE_AA)
        cv2.line(frame, tuple(elbow_r),    tuple(wrist_r), r_color, thickness_skeleton, cv2.LINE_AA)

        # Left arm — cyan/yellow
        l_color = (0, 220, 180)
        cv2.line(frame, tuple(shoulder_l), tuple(elbow_l), l_color, thickness_skeleton, cv2.LINE_AA)
        cv2.line(frame, tuple(elbow_l),    tuple(wrist_l), l_color, thickness_skeleton, cv2.LINE_AA)

        # Body lines
        cv2.line(frame, tuple(shoulder_r), tuple(hip_r), body_color, thickness_skeleton, cv2.LINE_AA)
        cv2.line(frame, tuple(hip_r),      tuple(knee_r), body_color, thickness_skeleton, cv2.LINE_AA)
        cv2.line(frame, tuple(shoulder_l), tuple(hip_l), body_color, thickness_skeleton, cv2.LINE_AA)
        cv2.line(frame, tuple(hip_l),      tuple(knee_l), body_color, thickness_skeleton, cv2.LINE_AA)

        # Joints with white ring
        for coord, color in [
            (shoulder_r, r_color), (elbow_r, r_color), (wrist_r, r_color),
            (shoulder_l, l_color), (elbow_l, l_color), (wrist_l, l_color),
            (hip_r, body_color),   (hip_l,   body_color),
            (knee_r, body_color),  (knee_l,  body_color),
        ]:
            cv2.circle(frame, tuple(coord), joint_radius, color, -1, cv2.LINE_AA)
            cv2.circle(frame, tuple(coord), joint_radius, (255, 255, 255), ring_thickness, cv2.LINE_AA)

        # Angle labels
        cv2.putText(frame, f'R:{int(angle_r)}',
                    (elbow_r[0] + int(10 * scale), elbow_r[1] - int(10 * scale)),
                    cv2.FONT_HERSHEY_SIMPLEX, text_scale, (255, 255, 0), text_thickness, cv2.LINE_AA)
        cv2.putText(frame, f'L:{int(angle_l)}',
                    (elbow_l[0] + int(10 * scale), elbow_l[1] - int(10 * scale)),
                    cv2.FONT_HERSHEY_SIMPLEX, text_scale, (255, 255, 0), text_thickness, cv2.LINE_AA)

        # ── Stage machines with Hysteresis ──
        # Right arm
        if angle_r > self.angle_down:
            self._down_frames_r += 1
            self._up_frames_r = 0
            if self._down_frames_r >= 3:
                if self.stage_right == "up":
                    self.counter_right += 1
                self.stage_right = "down"
        elif angle_r < self.angle_up:
            self._up_frames_r += 1
            self._down_frames_r = 0
            if self._up_frames_r >= 3:
                self.stage_right = "up"
        else:
            self._up_frames_r = 0
            self._down_frames_r = 0

        # Left arm
        if angle_l > self.angle_down:
            self._down_frames_l += 1
            self._up_frames_l = 0
            if self._down_frames_l >= 3:
                if self.stage_left == "up":
                    self.counter_left += 1
                self.stage_left = "down"
        elif angle_l < self.angle_up:
            self._up_frames_l += 1
            self._down_frames_l = 0
            if self._up_frames_l >= 3:
                self.stage_left = "up"
        else:
            self._up_frames_l = 0
            self._down_frames_l = 0

        # ── Form warnings (right side panel) ──────────────────────────────────
        self.form_warnings = []

        if not body_ok:
            self.form_warnings.append("Body swaying - keep torso still")

        if swing_r > self.swing_threshold:
            self.form_warnings.append("Right elbow swinging forward")
        if swing_l > self.swing_threshold:
            self.form_warnings.append("Left elbow swinging forward")

        if shrug_r:
            self.form_warnings.append("Right shoulder shrugging up")
        if shrug_l:
            self.form_warnings.append("Left shoulder shrugging up")

        draw_warning_panel(frame, self.form_warnings)

        # Left-side info panel — show both arm counters and stages
        r_stage_color = (0, 140, 255) if self.stage_right == "up" else (200, 200, 200)
        l_stage_color = (0, 220, 180) if self.stage_left  == "up" else (200, 200, 200)
        draw_info_panel(frame, [
            ("R Reps",  self.counter_right, (0, 140, 255)),
            ("R Stage", self.stage_right or "Get Ready", r_stage_color),
            ("L Reps",  self.counter_left,  (0, 220, 180)),
            ("L Stage", self.stage_left  or "Get Ready", l_stage_color),
        ], x_offset=10, y_start=220)

        # Build warning messages for return value (used by layout indicators)
        warning_message_right = next(
            (w for w in self.form_warnings if "Right" in w or "Body" in w), None)
        warning_message_left = next(
            (w for w in self.form_warnings if "Left" in w), None)

        progress_right = 1 if self.stage_right == "up" else 0
        progress_left  = 1 if self.stage_left  == "up" else 0

        return (self.counter_right, angle_r,
                self.counter_left,  angle_l,
                warning_message_right, warning_message_left,
                progress_right, progress_left,
                self.stage_right, self.stage_left)

    def draw_line_with_style(self, frame, start_point, end_point, color, thickness):
        cv2.line(frame, start_point, end_point, color, thickness, lineType=cv2.LINE_AA)

    def draw_circle(self, frame, center, color, radius):
        cv2.circle(frame, center, radius, color, -1)
