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
});
