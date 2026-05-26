document.addEventListener('DOMContentLoaded', function () {
    let weeklyChart = null;
    let exerciseChart = null;

    function initCharts() {
        const weeklyCtx = document.getElementById('weeklyChart');
        const exerciseCtx = document.getElementById('exerciseChart');

        if (weeklyCtx) {
            weeklyChart = new Chart(weeklyCtx, {
                type: 'bar',
                data: {
                    labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
                    datasets: [{
                        label: 'Workout Minutes',
                        data: [0, 0, 0, 0, 0, 0, 0],
                        backgroundColor: 'rgba(52, 152, 219, 0.5)',
                        borderColor: 'rgba(52, 152, 219, 1)',
                        borderWidth: 1,
                        borderRadius: 4,
                    }]
                },
                options: {
                    responsive: true,
                    plugins: { legend: { display: false } },
                    scales: { y: { beginAtZero: true, title: { display: true, text: 'Minutes' } } }
                }
            });
        }

        if (exerciseCtx) {
            exerciseChart = new Chart(exerciseCtx, {
                type: 'doughnut',
                data: {
                    labels: [],
                    datasets: [{
                        data: [],
                        backgroundColor: [
                            'rgba(52, 152, 219, 0.8)',
                            'rgba(46, 204, 113, 0.8)',
                            'rgba(155, 89, 182, 0.8)',
                            'rgba(230, 126, 34, 0.8)'
                        ],
                        borderWidth: 2
                    }]
                },
                options: {
                    responsive: true,
                    plugins: { legend: { position: 'bottom' } }
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
            })
            .catch(err => console.error('Dashboard data fetch error:', err));
    }

    initCharts();

    const refreshBtn = document.getElementById('refresh-stats');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', fetchDashboardData);
    }
});
