import cv2
import numpy as np


def draw_warning_panel(frame, warnings):
    """
    Draw all form warnings on the RIGHT side of the frame.
    Uses a semi-transparent dark background panel for readability.
    Each warning is shown with a red bullet and white text.
    """
    if not warnings:
        return

    h, w = frame.shape[:2]

    font       = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.52
    thickness  = 1
    padding    = 10
    line_h     = 28

    # Measure widest warning to size the panel
    max_text_w = max(
        cv2.getTextSize(f"  {warn}", font, font_scale, thickness)[0][0]
        for warn in warnings
    )

    panel_w = max_text_w + padding * 2 + 14   # 14 for bullet
    panel_h = len(warnings) * line_h + padding * 2

    # Position: top-right corner with a small margin
    margin  = 10
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
                  (0, 0, 220), 2)

    # Header
    header = "⚠ Form Warnings"
    cv2.putText(frame, "! Form Warnings",
                (x_start, y_start + padding + 12),
                font, 0.55, (0, 100, 255), 2)

    # Each warning line
    for i, warn in enumerate(warnings):
        y = y_start + padding + (i + 1) * line_h + 10
        # Red bullet dot
        cv2.circle(frame, (x_start + 5, y - 4), 4, (0, 60, 255), -1)
        # Warning text in white
        cv2.putText(frame, warn,
                    (x_start + 16, y),
                    font, font_scale, (255, 255, 255), thickness, cv2.LINE_AA)


def draw_info_panel(frame, lines, x_offset=10, y_start=10, alpha=0.6):
    """
    Draw a semi-transparent info panel on the LEFT side.
    lines: list of (label, value, color) tuples.
    """
    font       = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.6
    thickness  = 1
    padding    = 10
    line_h     = 30

    max_w = max(
        cv2.getTextSize(f"{lbl}: {val}", font, font_scale, thickness)[0][0]
        for lbl, val, _ in lines
    ) + padding * 2

    panel_h = len(lines) * line_h + padding * 2

    overlay = frame.copy()
    cv2.rectangle(overlay,
                  (x_offset, y_start),
                  (x_offset + max_w, y_start + panel_h),
                  (20, 20, 20), -1)
    cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)

    cv2.rectangle(frame,
                  (x_offset, y_start),
                  (x_offset + max_w, y_start + panel_h),
                  (80, 80, 80), 1)

    for i, (label, value, color) in enumerate(lines):
        y = y_start + padding + (i + 1) * line_h - 4
        cv2.putText(frame, f"{label}:", (x_offset + padding, y),
                    font, font_scale, (180, 180, 180), thickness, cv2.LINE_AA)
        label_w = cv2.getTextSize(f"{label}: ", font, font_scale, thickness)[0][0]
        cv2.putText(frame, str(value),
                    (x_offset + padding + label_w, y),
                    font, font_scale, color, thickness + 1, cv2.LINE_AA)
