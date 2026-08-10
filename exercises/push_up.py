import cv2
import numpy as np
from collections import deque
from pose_estimation.angle_calculation import calculate_angle
from utils.panel_utils import draw_warning_panel, draw_info_panel


class PushUp:
    def __init__(self):
        self.counter = 0
        self.stage   = None          # None -> "up" -> "down" -> "up"

        # Calibration state variables
        self.calibrated = False
        self.calibration_frames = []
        self.calibration_limit = 25
        self.standing_baseline = 160.0

        # Elbow flexion thresholds
        self.angle_up   = 155        # straight (calibrated dynamically)
        self.angle_down = 90         # bent (calibrated dynamically)

        # Hysteresis frame counts
        self._up_frames_count = 0
        self._down_frames_count = 0

        # ── Form thresholds ────────────────────────────────────────────────────
        self.align_min = 160
        self.align_max = 195
        self.flare_threshold = 50
        self.head_drop_threshold = 0.06

        # Angle smoothing
        self._angle_buf = deque(maxlen=5)

        self.form_warnings = []

    # ── Main tracking ──────────────────────────────────────────────────────────
    def track_push_up(self, landmarks, frame):
        h, w = frame.shape[:2]

        def pt(idx):
            return [int(landmarks[idx].x * w), int(landmarks[idx].y * h)]

        def raw(idx):
            return landmarks[idx].x, landmarks[idx].y

        # ── Landmarks ─────────────────────────────────────────────────────────
        nose       = pt(0)
        shoulder_l = pt(11);  shoulder_r = pt(12)
        elbow_l    = pt(13);  elbow_r    = pt(14)
        wrist_l    = pt(15);  wrist_r    = pt(16)
        hip_l      = pt(23);  hip_r      = pt(24)
        ankle_l    = pt(27);  ankle_r    = pt(28)

        # ── 1. Elbow angle — shoulder → elbow → wrist ─────────────────────────
        angle_l = calculate_angle(shoulder_l, elbow_l, wrist_l)
        angle_r = calculate_angle(shoulder_r, elbow_r, wrist_r)

        # Use the more visible side
        vis_l = landmarks[13].visibility
        vis_r = landmarks[14].visibility
        primary_angle = angle_l if vis_l >= vis_r else angle_r

        # Smooth
        self._angle_buf.append(primary_angle)
        smooth_angle = float(np.mean(self._angle_buf))

        # ── Dynamic Posture Calibration ────────────────────────────────────────
        if not self.calibrated:
            self.calibration_frames.append(smooth_angle)
            scale = max(1.0, min(1.8, h / 960.0))
            
            # Show calibration warning overlay
            self.form_warnings = ["Calibrating... Get in Plank"]
            draw_warning_panel(frame, self.form_warnings)
            
            # Left-side calibration info
            draw_info_panel(frame, [
                ("Reps",  "Calibrating",  (200, 200, 200)),
                ("Stage", "Calibrating",  (200, 200, 200)),
                ("Progress", f"{len(self.calibration_frames) * 4}%", (0, 220, 255)),
            ], x_offset=10, y_start=220)
            
            if len(self.calibration_frames) >= self.calibration_limit:
                self.standing_baseline = float(np.mean(self.calibration_frames))
                self.angle_up = min(168.0, self.standing_baseline - 5.0)
                self.angle_down = self.standing_baseline - 65.0
                self.calibrated = True
            
            return self.counter, smooth_angle, "Calibrating"

        # ── 2. Body alignment — shoulder → hip → ankle ────────────────────────
        align_l = calculate_angle(shoulder_l, hip_l, ankle_l)
        align_r = calculate_angle(shoulder_r, hip_r, ankle_r)
        align_avg = (align_l + align_r) / 2.0

        # ── 3. Elbow flare — hip → shoulder → elbow ───────────────────────────
        flare_l = calculate_angle(hip_l, shoulder_l, elbow_l)
        flare_r = calculate_angle(hip_r, shoulder_r, elbow_r)

        # ── 4. Head position — nose vs shoulder y ─────────────────────────────
        _, nose_y      = raw(0)
        _, shoulder_y  = raw(11)
        head_drop = (nose_y - shoulder_y) > self.head_drop_threshold

        # ── Draw skeleton (dynamically scaled) ──────────────────────────────────
        scale = max(1.0, min(1.8, h / 960.0))
        thickness_skeleton = max(1, int(2 * scale))
        joint_radius = max(3, int(7 * scale))
        ring_thickness = max(1, int(1 * scale))
        text_scale = 0.55 * scale
        text_thickness = max(1, int(2 * scale))

        body_ok    = self.align_min <= align_avg <= self.align_max
        body_color = (0, 220, 0) if body_ok else (0, 140, 255)

        # Arms
        cv2.line(frame, tuple(shoulder_l), tuple(elbow_l), (0, 60, 255),  thickness_skeleton, cv2.LINE_AA)
        cv2.line(frame, tuple(elbow_l),    tuple(wrist_l), (0, 60, 255),  thickness_skeleton, cv2.LINE_AA)
        cv2.line(frame, tuple(shoulder_r), tuple(elbow_r), (180, 30, 30), thickness_skeleton, cv2.LINE_AA)
        cv2.line(frame, tuple(elbow_r),    tuple(wrist_r), (180, 30, 30), thickness_skeleton, cv2.LINE_AA)

        # Body plank line
        cv2.line(frame, tuple(shoulder_l), tuple(hip_l),   body_color, thickness_skeleton, cv2.LINE_AA)
        cv2.line(frame, tuple(hip_l),      tuple(ankle_l), body_color, thickness_skeleton, cv2.LINE_AA)
        cv2.line(frame, tuple(shoulder_r), tuple(hip_r),   body_color, thickness_skeleton, cv2.LINE_AA)
        cv2.line(frame, tuple(hip_r),      tuple(ankle_r), body_color, thickness_skeleton, cv2.LINE_AA)

        # Joints
        for coord, color in [
            (shoulder_l, (0, 60, 255)),   (elbow_l, (0, 60, 255)),   (wrist_l, (0, 60, 255)),
            (shoulder_r, (180, 30, 30)),  (elbow_r, (180, 30, 30)),  (wrist_r, (180, 30, 30)),
            (hip_l,      body_color),     (hip_r,   body_color),
            (ankle_l,    body_color),     (ankle_r,  body_color),
        ]:
            cv2.circle(frame, tuple(coord), joint_radius, color, -1, cv2.LINE_AA)
            cv2.circle(frame, tuple(coord), joint_radius, (255, 255, 255), ring_thickness, cv2.LINE_AA)

        # Elbow angle labels
        cv2.putText(frame, f'{int(angle_l)}',
                    (elbow_l[0] + int(10 * scale), elbow_l[1] - int(10 * scale)),
                    cv2.FONT_HERSHEY_SIMPLEX, text_scale, (255, 255, 0), text_thickness, cv2.LINE_AA)
        cv2.putText(frame, f'{int(angle_r)}',
                    (elbow_r[0] + int(10 * scale), elbow_r[1] - int(10 * scale)),
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
            "up":   "Up",
            "down": "Down",
        }.get(self.stage, self.stage)

        # ── Form warnings (right side) ─────────────────────────────────────────
        self.form_warnings = []

        if align_avg < self.align_min:
            self.form_warnings.append("Hips sagging - keep body straight")
        elif align_avg > self.align_max:
            self.form_warnings.append("Hips too high - lower your hips")

        if flare_l > self.flare_threshold or flare_r > self.flare_threshold:
            self.form_warnings.append("Elbows flaring - tuck elbows in")

        if head_drop:
            self.form_warnings.append("Head dropping - keep neck neutral")

        draw_warning_panel(frame, self.form_warnings)

        # Left-side info panel
        stage_color = (0, 100, 255) if self.stage == "down" else (0, 220, 0)
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
