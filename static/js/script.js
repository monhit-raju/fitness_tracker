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

    let selectedExercise = null;
    let workoutRunning = false;
    let statusInterval = null;
    let currentMode = 'live';

    // ── Toast helper ──────────────────────────────────────────────────────────
    const toast = document.getElementById('toast');
    let toastTimer = null;

    function showToast(msg, type = '') {
        toast.textContent = msg;
        toast.className = 'toast show ' + type;
        clearTimeout(toastTimer);
        toastTimer = setTimeout(() => { toast.className = 'toast'; }, 3500);
    }

    // ── Mode toggle ───────────────────────────────────────────────────────────
    // On cloud IS_CLOUD=true so mode radios don't exist — skip
    if (!IS_CLOUD) {
        modeRadios.forEach(radio => {
            radio.addEventListener('change', function () {
                currentMode = this.value;
                if (currentMode === 'live') {
                    uploadSection.style.display = 'none';
                    if (liveVideo) liveVideo.style.display = 'block';
                    if (processedVideo) processedVideo.style.display = 'none';
                    if (startBtn) startBtn.style.display = '';
                    if (uploadBtn) uploadBtn.style.display = 'none';
                    videoFileInput.value = '';
                } else {
                    uploadSection.style.display = 'block';
                    if (liveVideo) liveVideo.style.display = 'none';
                    if (processedVideo) processedVideo.style.display = 'none';
                    if (startBtn) startBtn.style.display = 'none';
                    if (uploadBtn) uploadBtn.style.display = '';
                }
            });
        });
    } else {
        // Cloud: always in upload mode
        currentMode = 'upload';
    }

    // ── Exercise selection ────────────────────────────────────────────────────
    exerciseOptions.forEach(opt => {
        opt.addEventListener('click', function () {
            exerciseOptions.forEach(o => o.classList.remove('selected'));
            this.classList.add('selected');
            selectedExercise = this.getAttribute('data-exercise');
        });
    });

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
        uploadBtn.textContent = '⏳ Processing…';
        if (videoOverlay) videoOverlay.style.display = 'flex';

        fetch('/upload_video', { method: 'POST', body: formData })
            .then(r => r.json())
            .then(data => {
                uploadBtn.disabled = false;
                uploadBtn.textContent = '⬆ Analyze Video';
                if (videoOverlay) videoOverlay.style.display = 'none';

                if (data.success) {
                    const cloudPlaceholder = document.getElementById('cloud-placeholder');
                    if (cloudPlaceholder) cloudPlaceholder.style.display = 'none';
                    processedVideo.src = data.video_url;
                    processedVideo.load();
                    processedVideo.play().catch(() => {});
                    processedVideo.style.display = 'block';
                    if (liveVideo) liveVideo.style.display = 'none';
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
                uploadBtn.textContent = '⬆ Analyze Video';
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
                    showToast('Workout complete! Great job 🎉', 'success');
                    return;
                }
                currentSetEl.textContent = `${data.current_set} / ${data.total_sets}`;
                currentRepsEl.textContent = `${data.current_reps} / ${data.rep_goal}`;
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
        currentExerciseEl.textContent = '—';
        currentSetEl.textContent = '0 / 0';
        currentRepsEl.textContent = '0 / 0';
    }
});
