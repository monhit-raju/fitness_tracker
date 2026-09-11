# 🏋️ Kinetic AI — Real-Time Biomechanical Computer Vision & Fitness Platform

**Kinetic AI** is a production-grade, edge & cloud-powered Computer Vision fitness intelligence platform that turns any smartphone, laptop webcam, or recorded video into a 24/7 personal biomechanical trainer.

[![Live Demo](https://img.shields.io/badge/Live%20Demo-Render%20Cloud-00f2fe?style=for-the-badge&logo=render)](https://fitness-tracker-bat1.onrender.com/)
[![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.14-3776AB?style=for-the-badge&logo=python)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-2.3.3-000000?style=for-the-badge&logo=flask)](https://flask.palletsprojects.com/)
[![MediaPipe](https://img.shields.io/badge/MediaPipe-Pose%20Tasks%20API-FF6F00?style=for-the-badge&logo=google)](https://mediapipe.dev)
[![Docker](https://img.shields.io/badge/Docker-Containerized-2496ED?style=for-the-badge&logo=docker)](https://docker.com)

---

## 🌟 Key Features

- 🎥 **HTML5 Live Camera & Cloud Streaming**: Real-time pose estimation on local devices and cloud deployments (Render) via HTML5 client streaming.
- 👥 **Multi-Person Lock-On (`PrimaryPoseTracker`)**: Proprietary spatial memory tracking that locks onto the primary athlete, eliminating interference in crowded gym settings.
- 🏃 **5 Supported Exercise Models**:
  - **Squat**: Hip-Knee-Ankle angle, torso lean, knee symmetry, depth compliance.
  - **Push-Up**: Shoulder-Elbow-Wrist angle, hip alignment, elbow flare, head position.
  - **Hammer Curl**: Dual arm tracking, body sway, shoulder shrug detection.
  - **Lunge**: Lead knee flex, torso uprightness, knee-over-toe safety checks.
  - **Overhead Press**: Arm lockout, asymmetry detection, back arch checks.
- 📊 **Kinetic Form Index (KFI) & ROM Analytics**: Real-time Range-of-Motion (ROM %) percentage tracking and composite KFI form quality grades (S, A, B, C).
- 🎮 **Gamification & XP Leveling Engine**: Earn XP for reps, sets, and clean form. Unlock level titles from *Level 1 Rookie* to *Level 10 Cyber Athlete*.
- 🔊 **Web Audio SFX Sound Engine**: Pure Web Audio API synthesized chimes for reps, countdown beeps, posture warning alerts, and level-up fanfare.
- 🔥 **Real-Time Calorie Estimator**: MET-based caloric burn calculation based on user weight, exercise type, rep volume, and duration.
- 👤 **Athlete Profile & Target Preferences**: Customizable user name, weight (kg), height (cm), daily rep targets, and sound options.
- 📷 **Pre-Workout Camera Calibration Tester**: Live framing test modal to check webcam feed, lighting quality, and tracking confidence.
- 🔍 **Interactive Session Breakdown Inspector**: Click any historical workout in `/dashboard` to view rep-by-rep angle depth logs and form error timelines.
- 📥 **Data Export**: Download complete workout history logs as raw CSV files.
- 🗄️ **Dual Database Failover**: Automatic MySQL connection with seamless built-in SQLite fallback (`db/fitness_tracker.db`).

---

## 🏋️ Exercise Matrix & Form Checks

| Exercise | Rep Angle Focus | Posture & Safety Checks | Target ROM Benchmark |
| :--- | :--- | :--- | :--- |
| **Squat** | Hip → Knee → Ankle | Torso lean, knee symmetry, heel rise | 95° Depth |
| **Push-Up** | Shoulder → Elbow → Wrist | Hip sag/pike, elbow flare, head drop | 90° Elbow Flexion |
| **Hammer Curl** | Shoulder → Elbow → Wrist | Torso sway, elbow drift, shoulder shrug | 120° Flexion |
| **Lunge** | Hip → Knee → Ankle | Torso uprightness, knee-over-toe overextension | 100° Knee Flexion |
| **Overhead Press** | Shoulder → Elbow → Wrist | Arm lockout, arm asymmetry, back arching | 155° Overhead Lockout |

---

## 🚀 Cloud Deployment & Sharing

Live cloud instance is deployed on **Render**:
👉 **[https://fitness-tracker-bat1.onrender.com/](https://fitness-tracker-bat1.onrender.com/)**

### 1-Click Docker Cloud Deployment:
The project includes containerization files:
- [`Dockerfile`](file:///c:/Users/Administrator/fitness_tracker/Dockerfile) (with FFmpeg H.264 video encoding & OpenGL GLES libraries)
- [`render.yaml`](file:///c:/Users/Administrator/fitness_tracker/render.yaml)
- [`railway.toml`](file:///c:/Users/Administrator/fitness_tracker/railway.toml)
- [`Procfile`](file:///c:/Users/Administrator/fitness_tracker/Procfile)

---

## 🛠️ Local Installation & Setup

### 1. Clone the repository
```bash
git clone https://github.com/monhit-raju/fitness_tracker.git
cd fitness_tracker
```

### 2. Create virtual environment & install dependencies
```bash
python -m venv myenv
.\myenv\Scripts\activate
pip install -r requirements.txt
```

### 3. (Optional) Configure environment variables
```bash
cp .env.example .env
```
*(If MySQL credentials are empty, the system automatically runs on local SQLite fallback).*

### 4. Run the application
```bash
python app.py
```

Open **[http://127.0.0.1:5000](http://127.0.0.1:5000)** in your web browser.

---

## 📂 Project Structure

```
├── app.py                  # Flask web application, API routes, frame generators
├── main.py                 # Standalone OpenCV webcam execution script
├── Dockerfile              # Production Docker image configuration (FFmpeg + OpenCV + GLES)
├── Procfile                # Heroku / Render WSGI entrypoint
├── render.yaml             # 1-Click Render cloud service definition
├── railway.toml            # Railway container definition
├── requirements.txt        # Python package dependencies
├── DEPLOYMENT.md           # Step-by-step deployment guide
├── db/
│   ├── workout_logger.py   # Dual MySQL / SQLite DB logger with auto migration
│   └── fitness_tracker.db  # SQLite fallback database
├── exercises/
│   ├── squat.py            # Squat pose tracker & form checker
│   ├── push_up.py          # Push-Up pose tracker & form checker
│   ├── hammer_curl.py      # Hammer Curl dual arm tracker
│   ├── lunge.py            # Lunge single-leg balance tracker
│   └── shoulder_press.py   # Overhead Press lockout tracker
├── pose_estimation/
│   ├── estimation.py       # Dual MediaPipe Solutions & Tasks API + PrimaryPoseTracker
│   └── angle_calculation.py# 3D vector angle calculation helper
├── feedback/
│   ├── indicators.py       # HUD gauges & progress meters
│   ├── layout.py           # HUD overlay router
│   └── information.py      # Exercise MET factors & benefits metadata
├── static/
│   ├── css/                # Style sheets (Glassmorphism cyberpunk theme)
│   ├── js/
│   │   ├── script.js       # Main frontend UI state machine & camera streaming
│   │   ├── dashboard.js    # Chart.js analytics & Inspector Modal
│   │   └── sfx.js          # Web Audio API Synthesizer sound engine
│   └── videos/             # Processed workout video output directory
└── templates/
    ├── index.html          # Main Workout Studio UI
    └── dashboard.html      # Analytics Dashboard & Personal Records
```

---

## 🔬 Tech Stack

- **Computer Vision & AI**: MediaPipe Pose (Tasks & Solutions API), OpenCV Headless, Custom Spatial Vector Angle Calculation
- **Backend Core**: Python 3.10/3.14, Flask, Gunicorn WSGI Server, FFmpeg H.264 Encoder
- **Frontend & Audio**: HTML5, CSS3 (Glassmorphism), JavaScript (ES6+), Web Audio API Synthesizer, Web Speech API SpeechSynthesis, Chart.js
- **Database Architecture**: MySQL + Built-in SQLite Fallback
- **DevOps & Cloud**: Docker, Render, Railway, Git

---

## 📜 License

Distributed under the MIT License. See `LICENSE` for more information.
