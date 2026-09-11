document.addEventListener('DOMContentLoaded', function () {
    let weeklyChart = null;
    let exerciseChart = null;

    function initCharts() {
        const weeklyCtx = document.getElementById('weeklyChart');
        const exerciseCtx = document.getElementById('exerciseChart');

        if (weeklyCtx) {
            // Adjust canvas height programmatically if needed
            weeklyCtx.parentElement.style.position = 'relative';
            weeklyCtx.parentElement.style.height = '300px';

            weeklyChart = new Chart(weeklyCtx, {
                type: 'bar',
                data: {
                    labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
                    datasets: [{
                        label: 'Workout Minutes',
                        data: [0, 0, 0, 0, 0, 0, 0],
                        backgroundColor: 'rgba(0, 242, 254, 0.6)',
                        borderColor: '#00f2fe',
                        borderWidth: 1.5,
                        borderRadius: 6,
                        hoverBackgroundColor: 'rgba(0, 242, 254, 0.95)',
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            backgroundColor: 'rgba(17, 24, 39, 0.95)',
                            titleFont: { family: 'Outfit', size: 13 },
                            bodyFont: { family: 'Outfit', size: 13 },
                            borderColor: 'rgba(255, 255, 255, 0.1)',
                            borderWidth: 1,
                            padding: 10
                        }
                    },
                    scales: {
                        x: {
                            grid: { color: 'rgba(255, 255, 255, 0.04)' },
                            ticks: { color: '#9ca3af', font: { family: 'Outfit', size: 12 } }
                        },
                        y: {
                            beginAtZero: true,
                            grid: { color: 'rgba(255, 255, 255, 0.04)' },
                            ticks: { color: '#9ca3af', font: { family: 'Outfit', size: 12 } },
                            title: { display: true, text: 'Minutes', color: '#9ca3af', font: { family: 'Outfit', size: 12 } }
                        }
                    }
                }
            });
        }

        if (exerciseCtx) {
            exerciseCtx.parentElement.style.position = 'relative';
            exerciseCtx.parentElement.style.height = '300px';

            exerciseChart = new Chart(exerciseCtx, {
                type: 'doughnut',
                data: {
                    labels: [],
                    datasets: [{
                        data: [],
                        backgroundColor: [
                            'rgba(0, 242, 254, 0.85)',   // Neon Cyan (Squats)
                            'rgba(56, 239, 125, 0.85)',   // Neon Mint (Push-ups)
                            'rgba(255, 65, 108, 0.85)',   // Neon Rose (Hammer Curl)
                            'rgba(185, 43, 39, 0.85)'     // Accent Red
                        ],
                        borderColor: '#111827',
                        borderWidth: 2
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'bottom',
                            labels: {
                                color: '#f3f4f6',
                                font: { family: 'Outfit', size: 12, weight: '500' },
                                padding: 15
                            }
                        },
                        tooltip: {
                            backgroundColor: 'rgba(17, 24, 39, 0.95)',
                            titleFont: { family: 'Outfit', size: 13 },
                            bodyFont: { family: 'Outfit', size: 13 },
                            borderColor: 'rgba(255, 255, 255, 0.1)',
                            borderWidth: 1,
                            padding: 10
                        }
                    }
                }
            });
        }

        fetchDashboardData();
    }

    function fetchDashboardData() {
        fetch('/dashboard_data')
            .then(r => r.json())
            .then(data => {
                if (!data.success) return;

                if (weeklyChart && data.weekly_activity) {
                    weeklyChart.data.labels = data.weekly_activity.labels;
                    weeklyChart.data.datasets[0].data = data.weekly_activity.values;
                    weeklyChart.update();
                }

                if (exerciseChart && data.exercise_distribution) {
                    exerciseChart.data.labels = data.exercise_distribution.labels;
                    exerciseChart.data.datasets[0].data = data.exercise_distribution.values;
                    exerciseChart.update();
                }

                if (data.yearly_activity) {
                    renderYearlyHeatmap(data.yearly_activity);
                }
            })
            .catch(err => console.error('Dashboard data fetch error:', err));
    }

    function renderYearlyHeatmap(activityList) {
        const container = document.getElementById('contribution-calendar');
        if (!container) return;
        
        container.innerHTML = '';
        
        const activityMap = {};
        if (activityList) {
            activityList.forEach(item => {
                activityMap[item.day] = item.count;
            });
        }
        
        const today = new Date();
        const startDate = new Date();
        startDate.setDate(today.getDate() - 364);
        
        container.style.gridAutoFlow = 'column';
        
        let startDayOfWeek = startDate.getDay() - 1;
        if (startDayOfWeek < 0) startDayOfWeek = 6;
        
        for (let i = 0; i < startDayOfWeek; i++) {
            const spacer = document.createElement('div');
            spacer.style.visibility = 'hidden';
            spacer.className = 'calendar-day';
            container.appendChild(spacer);
        }
        
        const tempDate = new Date(startDate);
        for (let i = 0; i < 365; i++) {
            const dateStr = tempDate.toISOString().split('T')[0];
            const count = activityMap[dateStr] || 0;
            
            const cell = document.createElement('div');
            cell.className = 'calendar-day';
            
            let level = 0;
            if (count === 1) level = 1;
            else if (count === 2) level = 2;
            else if (count >= 3) level = 3;
            
            cell.classList.add(`level-${level}`);
            
            const formattedDate = tempDate.toLocaleDateString('en-US', {
                month: 'short',
                day: 'numeric',
                year: 'numeric'
            });
            cell.title = `${count} workout${count !== 1 ? 's' : ''} on ${formattedDate}`;
            
            container.appendChild(cell);
            tempDate.setDate(tempDate.getDate() + 1);
        }
    }

    initCharts();

    const refreshBtn = document.getElementById('refresh-stats');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', fetchDashboardData);
    }

    // Workout Session Inspector Modal Handlers
    const inspectorModal = document.getElementById('inspector-modal');
    const closeInspectorBtn = document.getElementById('close-inspector-btn');
    const inspectorCloseBtn = document.getElementById('inspector-close-btn');

    if (closeInspectorBtn) closeInspectorBtn.addEventListener('click', () => inspectorModal.style.display = 'none');
    if (inspectorCloseBtn) inspectorCloseBtn.addEventListener('click', () => inspectorModal.style.display = 'none');

    document.querySelectorAll('.workout-row').forEach(row => {
        row.style.cursor = 'pointer';
        row.addEventListener('click', function () {
            const workoutId = this.getAttribute('data-id');
            if (!workoutId) return;

            document.getElementById('insp-rep-table-body').innerHTML = '<tr><td colspan="4" style="text-align:center;"><i class="fa-solid fa-spinner fa-spin"></i> Loading rep analysis...</td></tr>';
            inspectorModal.style.display = 'flex';

            fetch(`/api/workout_detail/${workoutId}`)
                .then(r => r.json())
                .then(res => {
                    if (res.success && res.data) {
                        const w = res.data.workout;
                        const details = res.data.details || [];

                        document.getElementById('insp-exercise').textContent = (w.exercise_type || '').replace(/_/g, ' ').toUpperCase();
                        const dur = w.duration_seconds || 0;
                        document.getElementById('insp-duration').textContent = `${Math.floor(dur / 60)}:${(dur % 60).toString().padStart(2, '0')}`;
                        document.getElementById('insp-kfi').textContent = w.kfi_score || 95;
                        document.getElementById('insp-calories').textContent = `${w.calories_burned || 0} kcal`;

                        const tbody = document.getElementById('insp-rep-table-body');
                        tbody.innerHTML = '';

                        if (details.length > 0) {
                            details.forEach(d => {
                                const tr = document.createElement('tr');
                                const angleStr = d.angle ? `${Math.round(d.angle)}°` : 'N/A';
                                const stageStr = d.stage || '—';
                                const detailsObj = d.details ? (typeof d.details === 'string' ? JSON.parse(d.details) : d.details) : null;
                                let note = 'Clean Rep';
                                if (detailsObj && (detailsObj.warning || detailsObj.right?.warning || detailsObj.left?.warning)) {
                                    note = `<span style="color:var(--neon-rose);"><i class="fa-solid fa-triangle-exclamation"></i> ${detailsObj.warning || detailsObj.right?.warning || detailsObj.left?.warning}</span>`;
                                } else {
                                    note = '<span style="color:var(--neon-mint);"><i class="fa-solid fa-check"></i> Good Form</span>';
                                }

                                tr.innerHTML = `
                                    <td><strong>Rep ${d.rep_count}</strong></td>
                                    <td>${angleStr}</td>
                                    <td><span class="badge">${stageStr}</span></td>
                                    <td>${note}</td>
                                `;
                                tbody.appendChild(tr);
                            });
                        } else {
                            tbody.innerHTML = '<tr><td colspan="4" style="text-align:center; color:var(--text-muted);">No rep-by-rep breakdown recorded for this session.</td></tr>';
                        }
                    } else {
                        document.getElementById('insp-rep-table-body').innerHTML = '<tr><td colspan="4" style="text-align:center; color:var(--neon-rose);">Failed to load workout details.</td></tr>';
                    }
                })
                .catch(() => {
                    document.getElementById('insp-rep-table-body').innerHTML = '<tr><td colspan="4" style="text-align:center; color:var(--neon-rose);">Network error loading details.</td></tr>';
                });
        });
    });
});

