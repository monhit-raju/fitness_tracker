# 🏋️ AI Fitness Tracker

An AI-powered fitness tracking web app that uses **MediaPipe pose estimation** to analyse exercises in real time via webcam or uploaded video.

## Features

- 🎥 **Live webcam tracking** — real-time rep counting and form feedback
- 📹 **Video upload analysis** — upload a workout video and get it analysed
- 🏃 **3 exercises supported** — Squat, Push-Up, Hammer Curl
- 📊 **Dashboard** — workout history, weekly activity charts, exercise distribution
- ⚠️ **Form warnings** — real-time feedback on posture mistakes
- 🗄️ **MySQL logging** — all workouts saved to database

## Exercises & Form Checks

| Exercise | Rep Angle | Form Checks |
|----------|-----------|-------------|
| Squat | Hip → Knee → Ankle | Torso lean, knee symmetry, heel rise, squat depth |
| Push-Up | Shoulder → Elbow → Wrist | Hip sag/pike, elbow flare, head drop |
| Hammer Curl | Shoulder → Elbow → Wrist | Body sway, elbow swing, shoulder shrug |

## Setup

### 1. Clone the repo
```bash
git clone https://github.com/monhit-raju/fitness_tracker.git
cd fitness_tracker
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Set up environment variables
```bash
cp .env.example .env
```
Edit `.env` and fill in your MySQL credentials:
```
SECRET_KEY=your_random_secret_key
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=sports
```

### 4. Create the database
```sql
CREATE DATABASE IF NOT EXISTS sports;
```

### 5. Run the app
```bash
python app.py
```

Open **http://127.0.0.1:5000** in your browser.

## Project Structure

```
├── app.py                  # Flask application & routes
├── main.py                 # Standalone webcam script
├── requirements.txt
├── .env.example            # Environment variable template
├── db/
│   └── workout_logger.py   # MySQL workout logging
├── exercises/
│   ├── squat.py
│   ├── push_up.py
│   └── hammer_curl.py
├── pose_estimation/
│   ├── estimation.py       # MediaPipe pose estimator
│   └── angle_calculation.py
├── feedback/
│   ├── indicators.py       # On-frame UI indicators
│   ├── layout.py
│   └── information.py
├── utils/
│   ├── panel_utils.py      # Warning & info panels
│   ├── drawing_utils.py
│   └── draw_text_with_background.py
├── static/
│   ├── css/
│   ├── js/
│   ├── images/
│   └── videos/
└── templates/
    ├── index.html
    └── dashboard.html
```

## Requirements

- Python 3.8+
- Webcam (for live tracking)
- MySQL Server

## Tech Stack

- **Backend**: Flask, OpenCV, MediaPipe, PyMySQL
- **Frontend**: HTML, CSS, JavaScript, Chart.js
- **Database**: MySQL
