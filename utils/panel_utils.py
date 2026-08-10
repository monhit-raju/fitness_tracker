import cv2
import numpy as np

def draw_warning_panel(frame, warnings):
    """
    Draw all form warnings on the RIGHT side of the frame, dynamically scaled with bounds.
    Uses a semi-transparent dark background panel for readability.
    Each warning is shown with a red bullet and white text.
    """
    if not warnings:
        return

    h, w = frame.shape[:2]
    scale = max(1.0, min(1.8, h / 960.0))

    font       = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.52 * scale
    thickness  = max(1, int(1 * scale))
    padding    = int(10 * scale)
    line_h     = int(28 * scale)

    # Measure widest warning to size the panel
    max_text_w = max(
        cv2.getTextSize(f"  {warn}", font, font_scale, thickness)[0][0]
        for warn in warnings
    )

    panel_w = max_text_w + padding * 2 + int(14 * scale)   # 14 for bullet
    panel_h = len(warnings) * line_h + padding * 2

    # Position: top-right corner with a small margin
    margin  = int(10 * scale)
    x_start = w - panel_w - margin
    y_start = margin

    # Draw semi-transparent background
    overlay = frame.copy()
    cv2.rectangle(overlay,
                  (x_start - padding, y_start),
                  (x_start + panel_w, y_start + panel_h),
                  (20, 20, 20), -1)
    cv2.addWeighted(overlay, 0.65, frame, 0.35, 0, frame)

    # Draw red border
    cv2.rectangle(frame,
                  (x_start - padding, y_start),
                  (x_start + panel_w, y_start + panel_h),
                  (0, 0, 220), max(1, int(2 * scale)))

    # Header
    cv2.putText(frame, "! Form Warnings",
                (x_start, y_start + padding + int(12 * scale)),
                font, 0.55 * scale, (0, 100, 255), max(1, int(2 * scale)), cv2.LINE_AA)

    # Each warning line
    for i, warn in enumerate(warnings):
        y = y_start + padding + (i + 1) * line_h + int(10 * scale)
        # Red bullet dot
        cv2.circle(frame, (x_start + int(5 * scale), y - int(4 * scale)), int(4 * scale), (0, 60, 255), -1)
        # Warning text in white
        cv2.putText(frame, warn,
                    (x_start + int(16 * scale), y),
                    font, font_scale, (255, 255, 255), thickness, cv2.LINE_AA)


def draw_info_panel(frame, lines, x_offset=10, y_start=10, alpha=0.6):
    """
    Draw a semi-transparent info panel on the LEFT side, dynamically scaled with bounds.
    lines: list of (label, value, color) tuples.
    """
    h, w = frame.shape[:2]
    scale = max(1.0, min(1.8, h / 960.0))

    font       = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.6 * scale
    thickness  = max(1, int(1 * scale))
    padding    = int(10 * scale)
    line_h     = int(30 * scale)

    scaled_x_offset = int(x_offset * scale)
    scaled_y_start = int(y_start * scale)

    max_w = max(
        cv2.getTextSize(f"{lbl}: {val}", font, font_scale, thickness)[0][0]
        for lbl, val, _ in lines
    ) + padding * 2

    panel_h = len(lines) * line_h + padding * 2

    overlay = frame.copy()
    cv2.rectangle(overlay,
                  (scaled_x_offset, scaled_y_start),
                  (scaled_x_offset + max_w, scaled_y_start + panel_h),
                  (20, 20, 20), -1)
    cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)

    cv2.rectangle(frame,
                  (scaled_x_offset, scaled_y_start),
                  (scaled_x_offset + max_w, scaled_y_start + panel_h),
                  (80, 80, 80), max(1, int(1 * scale)))

    for i, (label, value, color) in enumerate(lines):
        y = scaled_y_start + padding + (i + 1) * line_h - int(4 * scale)
        cv2.putText(frame, f"{label}:", (scaled_x_offset + padding, y),
                    font, font_scale, (180, 180, 180), thickness, cv2.LINE_AA)
        label_w = cv2.getTextSize(f"{label}: ", font, font_scale, thickness)[0][0]
        cv2.putText(frame, str(value),
                    (scaled_x_offset + padding + label_w, y),
                    font, font_scale, color, thickness + 1, cv2.LINE_AA)
