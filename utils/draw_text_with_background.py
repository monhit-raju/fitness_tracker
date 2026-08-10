import cv2

def draw_text_with_background(frame, text, position, font, font_scale, text_color, bg_color, thickness=2):
    # Dynamically scale font properties and coordinates based on frame height (bounded scale factor)
    h = frame.shape[0]
    scale = max(1.0, min(1.8, h / 960.0))
    
    scaled_font_scale = font_scale * scale
    scaled_thickness = max(1, int(thickness * scale))
    scaled_position = (int(position[0] * scale), int(position[1] * scale))
    
    # Text size
    (text_width, text_height), _ = cv2.getTextSize(text, font, scaled_font_scale, scaled_thickness)

    # Calculate background coordinates
    x, y = scaled_position
    background_top_left = (x, y - text_height - int(6 * scale))
    background_bottom_right = (x + text_width, y + int(6 * scale))

    # Draw background rectangle
    cv2.rectangle(frame, background_top_left, background_bottom_right, bg_color, cv2.FILLED)

    # Draw text over the background
    cv2.putText(frame, text, (x, y), font, scaled_font_scale, text_color, scaled_thickness, cv2.LINE_AA)
