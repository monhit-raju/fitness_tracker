import cv2
import numpy as np
import math
from utils.draw_text_with_background import draw_text_with_background

def display_counter(frame, counter, position=(40, 240), color=(0, 0, 0), background_color=(192, 192, 192)):
    """Display the repetition counter."""
    text = f"Count: {counter}"
    draw_text_with_background(frame, text, position, 
                             cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, background_color, 1)

def display_stage(frame, stage, label="Stage", position=(40, 270), color=(0, 0, 0), background_color=(192, 192, 192)):
    """Display the current exercise stage."""
    text = f"{label}: {stage}"
    draw_text_with_background(frame, text, position, 
                             cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, background_color, 1)

def draw_progress_bar(frame, exercise, value, position, size=(200, 20), color=(0, 255, 0), background_color=(255, 255, 255), max_value=None):
    """Draw a progress bar for tracking exercise repetitions, scaled to frame resolution with bounds."""
    h = frame.shape[0]
    scale = max(1.0, min(1.8, h / 960.0))

    # Scale positions and dimensions
    x, y = int(position[0] * scale), int(position[1] * scale)
    width, height = int(size[0] * scale), int(size[1] * scale)
    thickness = max(1, int(1 * scale))

    # Use provided max_value, or fall back to sensible defaults
    if max_value is None:
        if exercise == "squat":
            max_value = 15
        elif exercise == "push_up":
            max_value = 10
        elif exercise == "hammer_curl":
            max_value = 12
        else:
            max_value = 10
    
    # Calculate fill width
    fill_width = int((value / max_value) * width)
    fill_width = min(fill_width, width)  # Ensure it doesn't exceed max width
    
    # Draw background
    cv2.rectangle(frame, (x, y), (x + width, y + height), background_color, -1)
    cv2.rectangle(frame, (x, y), (x + width, y + height), (0, 0, 0), thickness)
    
    # Draw fill
    if fill_width > 0:
        cv2.rectangle(frame, (x, y), (x + fill_width, y + height), color, -1)
    
    # Draw text inside bar (scaled)
    text = f"{value}/{max_value}"
    scaled_font_scale = 0.5 * scale
    text_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, scaled_font_scale, thickness)[0]
    text_x = x + (width - text_size[0]) // 2
    text_y = y + (height + text_size[1]) // 2
    cv2.putText(frame, text, (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX, scaled_font_scale, (0, 0, 0), thickness, cv2.LINE_AA)
    
    # Draw label above the progress bar
    label = f"{exercise.replace('_', ' ').title()} Progress"
    draw_text_with_background(frame, label, (position[0], position[1] - 10), 
                             cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), (118, 29, 14), 1)

def draw_gauge_meter(frame, angle, text, position, radius=50, color=(0, 0, 255)):
    """Draw a gauge meter visualization showing the angle, scaled to frame resolution with bounds."""
    h = frame.shape[0]
    scale = max(1.0, min(1.8, h / 960.0))

    # Scale properties
    x, y = int(position[0] * scale), int(position[1] * scale)
    scaled_radius = int(radius * scale)
    scaled_thickness = max(1, int(2 * scale))
    font_thickness = max(1, int(1 * scale))

    start_angle = 180
    end_angle = 0
    
    # Draw outer circle
    cv2.circle(frame, (x, y), scaled_radius, (200, 200, 200), scaled_thickness, cv2.LINE_AA)
    
    # Calculate the angle position on the gauge
    gauge_angle = start_angle - (angle * (start_angle - end_angle) / 180)
    gauge_angle = max(min(gauge_angle, start_angle), end_angle) # Constrain angle
    
    # Convert to radians
    gauge_angle_rad = math.radians(gauge_angle)
    
    # Calculate point on circle
    gauge_x = int(x + scaled_radius * math.cos(gauge_angle_rad))
    gauge_y = int(y - scaled_radius * math.sin(gauge_angle_rad))
    
    # Draw line from center to angle point
    cv2.line(frame, (x, y), (gauge_x, gauge_y), color, scaled_thickness, cv2.LINE_AA)
    
    # Draw center circle
    cv2.circle(frame, (x, y), max(3, int(5 * scale)), color, -1)
    
    # Draw angle text (scaled)
    angle_text = f"{int(angle)}°"
    scaled_font_scale_num = 0.6 * scale
    cv2.putText(frame, angle_text, (x - int(20 * scale), y + scaled_radius + int(20 * scale)), 
                cv2.FONT_HERSHEY_SIMPLEX, scaled_font_scale_num, color, scaled_thickness, cv2.LINE_AA)
    
    # Draw title (scaled)
    scaled_font_scale_lbl = 0.5 * scale
    cv2.putText(frame, text, (x - scaled_radius, y - scaled_radius - int(10 * scale)),
                cv2.FONT_HERSHEY_SIMPLEX, scaled_font_scale_lbl, (0, 0, 0), font_thickness, cv2.LINE_AA)
