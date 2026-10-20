/**
 * API Sentinel — Dashboard & Analytics Charts
 * Visualizes Latency Trends and Pass/Fail Distribution with dynamic theme adaptation.
 */

window.renderDashboardCharts = function (labels, latencies, passedCount, failedCount) {
  if (typeof Chart === 'undefined') {
    console.warn('Chart.js library not detected. Skipping chart rendering.');
    return;
  }

  const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
  const textColor = isDark ? '#94a3b8' : '#64748b';
  const gridColor = isDark ? '#1e293b' : '#f1f5f9';

  // 1. Latency Trend Chart
  const trendCanvas = document.getElementById('latencyTrendChart');
  if (trendCanvas && labels && labels.length > 0) {
    new Chart(trendCanvas, {
      type: 'line',
      data: {
        labels: labels,
        datasets: [{
          label: 'Total Duration (ms)',
          data: latencies,
          borderColor: '#3b82f6',
          backgroundColor: 'rgba(59, 130, 246, 0.1)',
          fill: true,
          tension: 0.3,
          pointRadius: 4,
          pointHoverRadius: 6,
          pointBackgroundColor: '#3b82f6',
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: function (ctx) {
                return `Duration: ${ctx.parsed.y} ms`;
              }
            }
          }
        },
        scales: {
          x: {
            grid: { color: gridColor },
            ticks: { color: textColor, font: { size: 11 } }
          },
          y: {
            beginAtZero: true,
            grid: { color: gridColor },
            ticks: {
              color: textColor,
              font: { size: 11 },
              callback: function (val) { return val + ' ms'; }
            }
          }
        }
      }
    });
  }

  // 2. Pass/Fail Distribution Donut Chart
  const donutCanvas = document.getElementById('passFailDonutChart');
  if (donutCanvas && (passedCount > 0 || failedCount > 0)) {
    new Chart(donutCanvas, {
      type: 'doughnut',
      data: {
        labels: ['Passed', 'Failed / Error'],
        datasets: [{
          data: [passedCount, failedCount],
          backgroundColor: ['#16a34a', '#dc2626'],
          hoverOffset: 4,
          borderWidth: 0,
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: '70%',
        plugins: {
          legend: {
            position: 'bottom',
            labels: { color: textColor, boxWidth: 12, padding: 14 }
          }
        }
      }
    });
  }
};
