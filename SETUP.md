# AI Sports Talent App - Setup Guide

## Prerequisites
- Python 3.8 or higher
- Webcam (for live tracking)
- MySQL (optional, only for web app with database features)

## Installation Steps

### 1. Install Python Dependencies
```bash
cd ai-sports-talent-platform
pip install -r requirements.txt
```

### 2. Database Setup (Optional - Only for Web App)
If you want to use the web application with workout logging:

1. Install MySQL Server
2. Create the database:
```sql
CREATE DATABASE sports;
```
3. Update credentials in `db/workout_logger.py`:
   - Change `user='root'` to your MySQL username
   - Change `password=''` to your MySQL password

## Running the Application

### Option 1: Web Application (Full Features)
```bash
python app.py
```
- Open browser: http://127.0.0.1:5000
- Features: Live camera, video upload, dashboard, workout history

### Option 2: Standalone Script (Simple)
```bash
python main.py
```
- Opens webcam window directly
- Press 'q' to quit
- Change `exercise_type` in main.py to switch exercises

## Configuration

### Change Exercise Type (main.py)
Edit line 14:
```python
exercise_type = "squat"  # Options: "squat", "push_up", "hammer_curl"
```

### Enable Video Recording (main.py)
Uncomment lines 32-37 and line 67:
```python
fourcc = cv2.VideoWriter_fourcc(*'XVID')
output_file = f"{exercise_type}_output.avi"
# ... rest of video writer setup
out.write(frame)  # In the main loop
```

## Troubleshooting

### Camera Not Working
- Check if another application is using the webcam
- Try changing `cv2.VideoCapture(0)` to `cv2.VideoCapture(1)`

### MySQL Connection Error
- Verify MySQL is running
- Check credentials in `db/workout_logger.py`
- Ensure 'sports' database exists

### Import Errors
- Reinstall dependencies: `pip install -r requirements.txt`
- Check Python version: `python --version`

## Exercise Types

1. **Squat**: Tracks hip-knee-shoulder angles
2. **Push-Up**: Tracks shoulder-elbow-wrist angles  
3. **Hammer Curl**: Tracks both arms with misalignment detection

## Controls

- **Web App**: Use browser interface
- **Standalone**: Press 'q' to quit

## Notes

- Ensure good lighting for accurate pose detection
- Stand/position yourself so full body is visible
- Wear contrasting clothing for better tracking
