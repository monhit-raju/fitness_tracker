import cv2
from pose_estimation.estimation import PoseEstimator
from exercises.squat import Squat
from exercises.hammer_curl import HammerCurl
from exercises.push_up import PushUp
from feedback.layout import layout_indicators
from feedback.information import get_exercise_info
from utils.draw_text_with_background import draw_text_with_background

def main():
    # Change to "squat", "push_up", or "hammer_curl"
    exercise_type = "hammer_curl"

    # Use webcam (index 0). Change to a file path string to use a video file instead.
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Could not open camera/video source.")
        return

    pose_estimator = PoseEstimator()

    if exercise_type == "hammer_curl":
        exercise = HammerCurl()
    elif exercise_type == "squat":
        exercise = Squat()
    elif exercise_type == "push_up":
        exercise = PushUp()
    else:
        print("Invalid exercise type.")
        return

    exercise_info = get_exercise_info(exercise_type)

    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    # Output saved in the current working directory
    output_file = f"{exercise_type}_output.avi"
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    out = cv2.VideoWriter(output_file, fourcc, fps, (frame_width, frame_height))

    window_title = f"{exercise_type.replace('_', ' ').title()} Tracker"

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        results = pose_estimator.estimate_pose(frame, exercise_type)
        if results.pose_landmarks:
            if exercise_type == "squat":
                counter, angle, stage = exercise.track_squat(results.pose_landmarks.landmark, frame)
                layout_indicators(frame, exercise_type, (counter, angle, stage))
            elif exercise_type == "hammer_curl":
                (cr, ar, cl, al, wr, wl, pr, pl, sr, sl) = exercise.track_hammer_curl(
                    results.pose_landmarks.landmark, frame)
                layout_indicators(frame, exercise_type, (cr, ar, cl, al, wr, wl, pr, pl, sr, sl))
            elif exercise_type == "push_up":
                counter, angle, stage = exercise.track_push_up(results.pose_landmarks.landmark, frame)
                layout_indicators(frame, exercise_type, (counter, angle, stage))

        draw_text_with_background(frame, f"Exercise: {exercise_info.get('name', 'N/A')}", (40, 50),
                                  cv2.FONT_HERSHEY_DUPLEX, 0.7, (255, 255, 255), (118, 29, 14), 1)
        draw_text_with_background(frame, f"Reps: {exercise_info.get('reps', 0)}", (40, 80),
                                  cv2.FONT_HERSHEY_DUPLEX, 0.7, (255, 255, 255), (118, 29, 14), 1)
        draw_text_with_background(frame, f"Sets: {exercise_info.get('sets', 0)}", (40, 110),
                                  cv2.FONT_HERSHEY_DUPLEX, 0.7, (255, 255, 255), (118, 29, 14), 1)

        out.write(frame)

        cv2.namedWindow(window_title, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(window_title, 1280, 720)
        cv2.imshow(window_title, frame)

        if cv2.waitKey(10) & 0xFF == ord('q'):
            break

    cap.release()
    out.release()
    cv2.destroyAllWindows()
    print(f"Output saved to: {output_file}")


if __name__ == '__main__':
    main()
