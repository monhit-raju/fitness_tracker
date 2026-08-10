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

    // Modals & Controls
    const voiceToggleBtn = document.getElementById('voice-toggle-btn');
    const guideToggleBtn = document.getElementById('guide-toggle-btn');
    const guideModal = document.getElementById('guide-modal');
    const closeGuideBtn = document.getElementById('close-guide-btn');
    const guideCloseBottom = document.getElementById('guide-close-bottom');

    const summaryModal = document.getElementById('summary-modal');
    const closeSummaryBtn = document.getElementById('close-summary-btn');
    const summaryDoneBtn = document.getElementById('summary-done-btn');

    // Rest Overlay
    const restOverlay = document.getElementById('rest-timer-overlay');
    const restCountdownNum = document.getElementById('rest-countdown-num');
    const skipRestBtn = document.getElementById('skip-rest-btn');

    // Progress Bar
    const progressContainer = document.getElementById('telemetry-progress-container');
    const progressFill = document.getElementById('telemetry-progress-fill');
    const progressPercentLabel = document.getElementById('progress-percent-label');

    let selectedExercise = null;
    let workoutRunning = false;
    let statusInterval = null;
    let currentMode = 'live';

    // Voice & Timer states
    let voiceEnabled = true;
    let lastRepCount = 0;
    let lastSetCompleted = 0;
    let lastWarningSpoken = '';
    let lastWarningTime = 0;
    let restTimerInterval = null;

    function speak(text) {
        if (!voiceEnabled) return;
        if ('speechSynthesis' in window) {
            window.speechSynthesis.cancel();
            const utterance = new SpeechSynthesisUtterance(text);
            utterance.rate = 1.15;
            utterance.pitch = 1.0;
            window.speechSynthesis.speak(utterance);
        }
    }

    // Voice Toggle Handler
    if (voiceToggleBtn) {
        voiceToggleBtn.addEventListener('click', function () {
            voiceEnabled = !voiceEnabled;
            if (voiceEnabled) {
                this.classList.add('active');
                this.innerHTML = '<i class="fa-solid fa-volume-high"></i> Voice ON';
                speak("Voice Assistant Enabled");
            } else {
                this.classList.remove('active');
                this.innerHTML = '<i class="fa-solid fa-volume-xmark"></i> Voice OFF';
                if ('speechSynthesis' in window) window.speechSynthesis.cancel();
            }
        });
    }

    // Technique Guide Modal Handlers
    if (guideToggleBtn) {
        guideToggleBtn.addEventListener('click', () => guideModal.style.display = 'flex');
    }
    if (closeGuideBtn) {
        closeGuideBtn.addEventListener('click', () => guideModal.style.display = 'none');
    }
    if (guideCloseBottom) {
        guideCloseBottom.addEventListener('click', () => guideModal.style.display = 'none');
    }

    // Guide Tab Switching
    const guideTabs = document.querySelectorAll('.guide-tab');
    const guideContents = document.querySelectorAll('.guide-tab-content');

    guideTabs.forEach(tab => {
        tab.addEventListener('click', function () {
            const target = this.getAttribute('data-tab');
            guideTabs.forEach(t => t.classList.remove('active'));
            guideContents.forEach(c => c.classList.remove('active'));

            this.classList.add('active');
            const targetEl = document.getElementById(target);
            if (targetEl) targetEl.classList.add('active');
        });
    });

    // Summary Modal Close Handlers
    if (closeSummaryBtn) {
        closeSummaryBtn.addEventListener('click', () => summaryModal.style.display = 'none');
    }
    if (summaryDoneBtn) {
        summaryDoneBtn.addEventListener('click', () => summaryModal.style.display = 'none');
    }

    // Toast helper
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

    // Mode toggle
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

    // Exercise selection
    exerciseOptions.forEach(opt => {
        opt.addEventListener('click', function () {
            exerciseOptions.forEach(o => o.classList.remove('selected'));
            this.classList.add('selected');
            selectedExercise = this.getAttribute('data-exercise');
        });
    });

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

    // Start workout
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
                    
                    lastRepCount = 0;
                    lastSetCompleted = 0;
                    lastWarningSpoken = '';
                    lastWarningTime = 0;
                    
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

                    speak(`Starting ${selectedExercise.replace(/_/g, ' ')}. Begin set 1!`);
                    showToast('Workout started! Get moving 💪', 'success');
                } else {
                    showToast('Failed to start: ' + (data.error || 'Unknown error'), 'error');
                }
            })
            .catch(() => showToast('Network error. Is the server running?', 'error'));
    });

    // Stop workout & display summary report card
    stopBtn.addEventListener('click', function () {
        fetch('/stop_exercise', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    resetWorkoutUI();
                    if (data.summary) {
                        displaySummaryReport(data.summary);
                    } else {
                        showToast('Workout stopped and saved.', 'success');
                    }
                }
            })
            .catch(() => showToast('Error stopping workout.', 'error'));
    });

    // Upload & analyze
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

    // Status polling
    function checkStatus() {
        fetch('/get_status')
            .then(r => r.json())
            .then(data => {
                if (!data.exercise_running && workoutRunning) {
                    fetch('/stop_exercise', { method: 'POST', headers: { 'Content-Type': 'application/json' } })
                        .then(res => res.json())
                        .then(sData => {
                            resetWorkoutUI();
                            speak("Workout complete. Fantastic effort!");
                            if (sData && sData.summary) {
                                displaySummaryReport(sData.summary);
                            }
                        })
                        .catch(() => resetWorkoutUI());
                    return;
                }

                currentSetEl.textContent = `${data.current_set} / ${data.total_sets}`;
                currentRepsEl.textContent = `${data.current_reps} / ${data.rep_goal}`;

                // Rep count voice announcement
                if (data.current_reps > lastRepCount && workoutRunning) {
                    lastRepCount = data.current_reps;
                    speak(data.current_reps.toString());
                }

                // Set completion rest timer trigger
                if (data.current_set > lastSetCompleted + 1 && lastSetCompleted > 0 && workoutRunning) {
                    lastSetCompleted = data.current_set - 1;
                    triggerRestTimer(30);
                }

                // Form warnings voice feedback
                if (data.warnings && data.warnings.length > 0 && workoutRunning) {
                    const activeWarning = data.warnings[0];
                    const currentTime = Date.now();
                    if (activeWarning !== lastWarningSpoken || (currentTime - lastWarningTime > 4500)) {
                        lastWarningSpoken = activeWarning;
                        lastWarningTime = currentTime;
                        let speechText = activeWarning.replace(/[:⚠!]/g, ' ').trim();
                        speak(speechText);
                    }
                }

                // Progress calculation
                if (data.rep_goal > 0 && progressFill && progressPercentLabel) {
                    const progressPct = Math.min(Math.round((data.current_reps / data.rep_goal) * 100), 100);
                    progressFill.style.width = progressPct + '%';
                    progressPercentLabel.textContent = progressPct + '%';
                }
            })
            .catch(() => {});
    }

    // Rest Countdown Overlay
    function triggerRestTimer(seconds) {
        if (!restOverlay) return;
        let count = seconds;
        restCountdownNum.textContent = count;
        restOverlay.style.display = 'flex';
        speak("Rest time! Take a breather.");

        clearInterval(restTimerInterval);
        restTimerInterval = setInterval(() => {
            count--;
            restCountdownNum.textContent = count;
            if (count <= 0) {
                clearInterval(restTimerInterval);
                restOverlay.style.display = 'none';
                speak("Rest finished! Next set starting now.");
            }
        }, 1000);
    }

    if (skipRestBtn) {
        skipRestBtn.addEventListener('click', function () {
            clearInterval(restTimerInterval);
            if (restOverlay) restOverlay.style.display = 'none';
            speak("Rest skipped. Let's go!");
        });
    }

    // Post-Workout Summary Modal
    function displaySummaryReport(summary) {
        document.getElementById('summary-exercise').textContent = summary.exercise || 'Workout';
        document.getElementById('summary-duration').textContent = summary.duration_formatted || '00:00';
        document.getElementById('summary-sets').textContent = summary.completed_sets || 0;
        document.getElementById('summary-reps').textContent = summary.total_reps || 0;
        
        const accuracyEl = document.getElementById('summary-accuracy');
        if (accuracyEl) {
            accuracyEl.textContent = `${summary.form_accuracy}%`;
            if (summary.form_accuracy >= 85) {
                accuracyEl.style.color = 'var(--neon-green)';
            } else if (summary.form_accuracy >= 65) {
                accuracyEl.style.color = '#ffaa00';
            } else {
                accuracyEl.style.color = '#ff3366';
            }
        }

        const listEl = document.getElementById('summary-warnings-list');
        if (listEl) {
            listEl.innerHTML = '';
            if (summary.warnings_log && summary.warnings_log.length > 0) {
                summary.warnings_log.forEach(w => {
                    const li = document.createElement('li');
                    li.innerHTML = `<i class="fa-solid fa-triangle-exclamation" style="color:var(--neon-rose); margin-right:8px;"></i> ${w}`;
                    listEl.appendChild(li);
                });
            } else {
                const li = document.createElement('li');
                li.innerHTML = `<i class="fa-solid fa-circle-check" style="color:var(--neon-green); margin-right:8px;"></i> Perfect posture maintained throughout the workout session!`;
                listEl.appendChild(li);
            }
        }

        if (summaryModal) summaryModal.style.display = 'flex';
    }

    // Reset UI
    function resetWorkoutUI() {
        workoutRunning = false;
        startBtn.disabled = false;
        stopBtn.disabled = true;
        clearInterval(statusInterval);
        clearInterval(restTimerInterval);
        statusInterval = null;

        if (restOverlay) restOverlay.style.display = 'none';
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

