# feedback/indicators.py
from utils.drawing_utils import draw_gauge_meter, draw_progress_bar

def draw_squat_indicators(frame, counter, angle, stage):
    # Progress Bar (positioned cleanly on the left below app.py details)
    draw_progress_bar(frame, exercise="squat", value=counter, position=(40, 175), size=(200, 20), color=(163, 245, 184, 1), background_color=(255, 255, 255))

    # Gauge Meter (positioned cleanly at the bottom)
    draw_gauge_meter(frame, angle=angle, text="Squat Gauge Meter", position=(135, 415), radius=75, color=(0, 0, 255))

def draw_pushup_indicators(frame, counter, angle, stage):
    # Progress Bar (positioned cleanly on the left below app.py details)
    draw_progress_bar(frame, exercise="push_up", value=counter, position=(40, 175), size=(200, 20), color=(163, 245, 184, 1), background_color=(255, 255, 255))

    # Gauge Meter
    text = "Push-Up Gauge Meter"
    draw_gauge_meter(frame, angle=angle, text=text, position=(350, 80), radius=50, color=(0, 102, 204))

def draw_hammercurl_indicators(frame, counter_right, angle_right, counter_left, angle_left, stage_right, stage_left):
    # Progress Bar
    draw_progress_bar(frame, exercise="hammer_curl", value=(counter_right + counter_left) / 2, position=(40, 175), size=(200, 20), color=(163, 245, 184, 1), background_color=(255, 255, 255))

    text_right = "Right Gauge Meter"
    text_left = "Left Gauge Meter"

    # Gauge Meters for Angles
    draw_gauge_meter(frame, angle=angle_right, text=text_right, position=(1200, 80), radius=50, color=(0, 102, 204))
    draw_gauge_meter(frame, angle=angle_left, text=text_left, position=(1200, 240), radius=50, color=(0, 102, 204))

def draw_lunge_indicators(frame, counter, angle, stage):
    draw_progress_bar(frame, exercise="lunge", value=counter, position=(40, 175), size=(200, 20), color=(163, 245, 184, 1), background_color=(255, 255, 255))
    draw_gauge_meter(frame, angle=angle, text="Lunge Depth Meter", position=(135, 415), radius=75, color=(255, 165, 0))

def draw_shoulderpress_indicators(frame, counter, angle, stage):
    draw_progress_bar(frame, exercise="shoulder_press", value=counter, position=(40, 175), size=(200, 20), color=(163, 245, 184, 1), background_color=(255, 255, 255))
    draw_gauge_meter(frame, angle=angle, text="Extension Gauge", position=(350, 80), radius=50, color=(0, 200, 255))

