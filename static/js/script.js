document.addEventListener('DOMContentLoaded', function () {
    const exerciseOptions = document.querySelectorAll('.exercise-option');
    const startBtn = document.getElementById('start-btn');
    const stopBtn = document.getElementById('stop-btn');
    const uploadBtn = document.getElementById('upload-btn');
    const setsInput = document.getElementById('sets');
    const repsInput = document.getElementById('reps');
    const currentExerciseEl = document.getElementById('current-exercise');
    const currentSetEl = document.getElementById('current-set');
    const currentRepsEl = document.getElementById('current-reps');
    const modeRadios = document.querySelectorAll('input[name="mode"]');
    const uploadSection = document.querySelector('.upload-section');
    const liveVideo = document.getElementById('live-video');
    const processedVideo = document.getElementById('processed-video');
    const videoFileInput = document.getElementById('video-file');
    const videoOverlay = document.getElementById('video-overlay');
    const videoWrapper = document.getElementById('video-wrapper');
    const statusExBox = document.getElementById('status-ex-box');
    const statusSetBox = document.getElementById('status-set-box');
    const statusRepBox = document.getElementById('status-rep-box');
    const recIndicator = document.getElementById('rec-indicator');
    
    // Progress Bar Elements
    const progressContainer = document.getElementById('telemetry-progress-container');
    const progressFill = document.getElementById('telemetry-progress-fill');
    const progressPercentLabel = document.getElementById('progress-percent-label');

    let selectedExercise = null;
    let workoutRunning = false;
    let statusInterval = null;
    let currentMode = 'live';

    // Voice Coaching state variables
    let lastRepCount = 0;
    let lastWarningSpoken = '';
    let lastWarningTime = 0;

    function speak(text) {
        if ('speechSynthesis' in window) {
            window.speechSynthesis.cancel();
            const utterance = new SpeechSynthesisUtterance(text);
            utterance.rate = 1.1;
            utterance.pitch = 1.0;
            window.speechSynthesis.speak(utterance);
        }
    }

    // ── Toast helper ──────────────────────────────────────────────────────────
    const toast = document.getElementById('toast');
    let toastTimer = null;

    function showToast(msg, type = '') {
        let icon = '<i class="fa-solid fa-circle-info"></i>';
        if (type === 'success') {
            icon = '<i class="fa-solid fa-circle-check"></i>';
        } else if (type === 'error') {
            icon = '<i class="fa-solid fa-circle-exclamation"></i>';
        }
        
        toast.innerHTML = `${icon} <span>${msg}</span>`;
        toast.className = 'toast show ' + type;
        clearTimeout(toastTimer);
        toastTimer = setTimeout(() => { toast.className = 'toast'; }, 3500);
    }

    // ── Mode toggle ───────────────────────────────────────────────────────────
    modeRadios.forEach(radio => {
        radio.addEventListener('change', function () {
            currentMode = this.value;
            if (currentMode === 'live') {
                uploadSection.style.display = 'none';
                liveVideo.style.display = 'block';
                processedVideo.style.display = 'none';
                startBtn.style.display = '';
                uploadBtn.style.display = 'none';
                videoFileInput.value = '';
                const fileNameDisplay = document.getElementById('file-name-display');
                if (fileNameDisplay) fileNameDisplay.textContent = '';
            } else {
                uploadSection.style.display = 'block';
                liveVideo.style.display = 'none';
                processedVideo.style.display = 'none';
                startBtn.style.display = 'none';
                uploadBtn.style.display = '';
            }
        });
    });

    // ── Exercise selection ────────────────────────────────────────────────────
    exerciseOptions.forEach(opt => {
        opt.addEventListener('click', function () {
            exerciseOptions.forEach(o => o.classList.remove('selected'));
            this.classList.add('selected');
            selectedExercise = this.getAttribute('data-exercise');
        });
    });

    // ── File input listener for filename display ──
    if (videoFileInput) {
        videoFileInput.addEventListener('change', function () {
            const fileNameDisplay = document.getElementById('file-name-display');
            if (fileNameDisplay) {
                if (this.files && this.files[0]) {
                    fileNameDisplay.innerHTML = `<i class="fa-solid fa-file-video"></i> Selected: <strong>${this.files[0].name}</strong>`;
                } else {
                    fileNameDisplay.textContent = '';
                }
            }
        });
    }

    // ── Start workout ─────────────────────────────────────────────────────────
    startBtn.addEventListener('click', function () {
        if (!selectedExercise) {
            showToast('Please select an exercise first!', 'error');
            return;
        }

        const sets = parseInt(setsInput.value);
        const reps = parseInt(repsInput.value);

        if (!sets || sets < 1 || !reps || reps < 1) {
            showToast('Please enter valid sets and reps.', 'error');
            return;
        }

        fetch('/start_exercise', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ exercise_type: selectedExercise, sets, reps })
        })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    workoutRunning = true;
                    startBtn.disabled = true;
                    stopBtn.disabled = false;
                    
                    // Reset voice tracking
                    lastRepCount = 0;
                    lastWarningSpoken = '';
                    lastWarningTime = 0;
                    
                    // Activate live visual feedback
                    if (videoWrapper) videoWrapper.classList.add('active');
                    if (statusExBox) statusExBox.classList.add('active');
                    if (statusSetBox) statusSetBox.classList.add('active');
                    if (statusRepBox) statusRepBox.classList.add('active');
                    if (recIndicator) recIndicator.style.display = 'flex';
                    if (progressContainer) {
                        progressContainer.style.display = 'block';
                        if (progressFill) progressFill.style.width = '0%';
                        if (progressPercentLabel) progressPercentLabel.textContent = '0%';
                    }

                    currentExerciseEl.textContent = selectedExercise.replace(/_/g, ' ').toUpperCase();
                    currentSetEl.textContent = `1 / ${sets}`;
                    currentRepsEl.textContent = `0 / ${reps}`;
                    statusInterval = setInterval(checkStatus, 1000);
                    showToast('Workout started! Get moving 💪', 'success');
                } else {
                    showToast('Failed to start: ' + (data.error || 'Unknown error'), 'error');
                }
            })
            .catch(() => showToast('Network error. Is the server running?', 'error'));
    });

    // ── Stop workout ──────────────────────────────────────────────────────────
    stopBtn.addEventListener('click', function () {
        fetch('/stop_exercise', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    resetWorkoutUI();
                    showToast('Workout stopped and saved.', 'success');
                }
            })
            .catch(() => showToast('Error stopping workout.', 'error'));
    });

    // ── Upload & analyze ──────────────────────────────────────────────────────
    uploadBtn.addEventListener('click', function () {
        if (!selectedExercise) {
            showToast('Please select an exercise first!', 'error');
            return;
        }
        if (!videoFileInput.files[0]) {
            showToast('Please select a video file!', 'error');
            return;
        }

        const sets = parseInt(setsInput.value);
        const reps = parseInt(repsInput.value);
        if (!sets || sets < 1 || !reps || reps < 1) {
            showToast('Please enter valid sets and reps.', 'error');
            return;
        }

        const formData = new FormData();
        formData.append('video', videoFileInput.files[0]);
        formData.append('exercise_type', selectedExercise);
        formData.append('sets', sets);
        formData.append('reps', reps);

        uploadBtn.disabled = true;
        uploadBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Processing…';
        if (videoOverlay) videoOverlay.style.display = 'flex';

        fetch('/upload_video', { method: 'POST', body: formData })
            .then(r => r.json())
            .then(data => {
                uploadBtn.disabled = false;
                uploadBtn.innerHTML = '<i class="fa-solid fa-wand-magic-sparkles"></i> Process Workout';
                if (videoOverlay) videoOverlay.style.display = 'none';

                if (data.success) {
                    processedVideo.src = data.video_url;
                    processedVideo.load();
                    processedVideo.play().catch(() => {});
                    processedVideo.style.display = 'block';
                    liveVideo.style.display = 'none';
                    
                    // Activate live visual feedback briefly
                    if (videoWrapper) videoWrapper.classList.add('active');

                    currentExerciseEl.textContent = selectedExercise.replace(/_/g, ' ').toUpperCase();
                    currentSetEl.textContent = 'Done';
                    currentRepsEl.textContent = 'Done';
                    showToast('Video processed successfully! ✅', 'success');
                } else {
                    showToast('Processing failed: ' + (data.error || 'Unknown error'), 'error');
                }
            })
            .catch(() => {
                uploadBtn.disabled = false;
                uploadBtn.innerHTML = '<i class="fa-solid fa-wand-magic-sparkles"></i> Process Workout';
                if (videoOverlay) videoOverlay.style.display = 'none';
                showToast('Network error during upload.', 'error');
            });
    });

    // ── Status polling ────────────────────────────────────────────────────────
    function checkStatus() {
        fetch('/get_status')
            .then(r => r.json())
            .then(data => {
                if (!data.exercise_running && workoutRunning) {
                    resetWorkoutUI();
                    speak("Workout complete. Great job!");
                    showToast('Workout complete! Great job 🎉', 'success');
                    return;
                }
                currentSetEl.textContent = `${data.current_set} / ${data.total_sets}`;
                currentRepsEl.textContent = `${data.current_reps} / ${data.rep_goal}`;

                // Voice announcement of rep increments
                if (data.current_reps > lastRepCount && workoutRunning) {
                    lastRepCount = data.current_reps;
                    speak(data.current_reps.toString());
                }

                // Voice coaching for form warnings
                if (data.warnings && data.warnings.length > 0 && workoutRunning) {
                    const activeWarning = data.warnings[0];
                    const currentTime = Date.now();
                    // Announce warning if it is new, or if 4 seconds have passed since last spoken
                    if (activeWarning !== lastWarningSpoken || (currentTime - lastWarningTime > 4000)) {
                        lastWarningSpoken = activeWarning;
                        lastWarningTime = currentTime;
                        // Strip prefix/formatting tags for clear audio
                        let speechText = activeWarning.split('-')[0].trim().replace(/⚠|!/g, '');
                        speak(speechText);
                    }
                }

                // Calculate progress percentages
                if (data.rep_goal > 0 && progressFill && progressPercentLabel) {
                    const progressPct = Math.min(Math.round((data.current_reps / data.rep_goal) * 100), 100);
                    progressFill.style.width = progressPct + '%';
                    progressPercentLabel.textContent = progressPct + '%';
                }
            })
            .catch(() => {});
    }

    // ── Reset UI ──────────────────────────────────────────────────────────────
    function resetWorkoutUI() {
        workoutRunning = false;
        startBtn.disabled = false;
        stopBtn.disabled = true;
        clearInterval(statusInterval);
        statusInterval = null;

        // Reset visual status classes
        if (videoWrapper) videoWrapper.classList.remove('active');
        if (statusExBox) statusExBox.classList.remove('active');
        if (statusSetBox) statusSetBox.classList.remove('active');
        if (statusRepBox) statusRepBox.classList.remove('active');
        if (recIndicator) recIndicator.style.display = 'none';
        if (progressContainer) progressContainer.style.display = 'none';

        currentExerciseEl.textContent = '—';
        currentSetEl.textContent = '0 / 0';
        currentRepsEl.textContent = '0 / 0';
    }
});
