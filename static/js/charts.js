/* Interview Insights — Chart Components */

// Chart.js global defaults for dark theme
Chart.defaults.color = '#a0a0b0';
Chart.defaults.borderColor = '#1a1a2e';
Chart.defaults.font.family = "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif";

const ACCENT = {
  blue: '#4f8fff',
  green: '#34d399',
  red: '#ef4444',
  yellow: '#fbbf24',
  purple: '#a78bfa',
  cyan: '#22d3ee',
  pink: '#f472b6',
  orange: '#fb923c',
};

const DECISION_COLORS = {
  strong_hire: '#34d399',
  hire: '#6ee7b7',
  maybe: '#fbbf24',
  no_hire: '#fca5a5',
  strong_no_hire: '#ef4444',
};

const INTERVIEWER_COLORS = [
  ACCENT.blue, ACCENT.green, ACCENT.purple, ACCENT.yellow,
  ACCENT.cyan, ACCENT.pink, ACCENT.orange, ACCENT.red,
];

// --- Calibration Heatmap (HTML table) ---
function renderCalibrationHeatmap(data) {
  const container = document.getElementById('calibration-heatmap');
  if (!data.calibration || Object.keys(data.calibration).length === 0) {
    container.innerHTML = '<p class="text-muted text-center">No calibration data available</p>';
    return;
  }

  const interviewers = Object.keys(data.calibration).sort();
  const roles = [...new Set(Object.values(data.calibration).flatMap(r => Object.keys(r)))].sort();

  let html = '<table class="heatmap-table"><thead><tr><th></th>';
  roles.forEach(r => { html += `<th>${r.replace(' Engineer', '').replace(' ', '<br>')}</th>`; });
  html += '</tr></thead><tbody>';

  interviewers.forEach(interviewer => {
    html += `<tr><th style="white-space:nowrap;font-size:0.8rem;">${interviewer}</th>`;
    roles.forEach(role => {
      const val = data.calibration[interviewer][role];
      if (val !== undefined) {
        const hue = val * 1.2; // 0=red(0), 100=green(120)
        const bg = `hsl(${hue}, 70%, 25%)`;
        const textColor = '#fff';
        html += `<td class="heatmap-cell" style="background:${bg};color:${textColor};" data-interviewer="${interviewer}" data-role="${role}" onclick="heatmapClick(this)">${val}%</td>`;
      } else {
        html += '<td class="heatmap-cell empty">—</td>';
      }
    });
    html += '</tr>';
  });

  html += '</tbody></table>';
  container.innerHTML = html;
}

// Click handler for heatmap cells
function heatmapClick(cell) {
  const interviewer = cell.dataset.interviewer;
  const role = cell.dataset.role;
  if (!appData) return;
  const entries = appData.entries.filter(e => e.interviewer === interviewer && e.role === role);
  showModal(`${interviewer} — ${role}`, entries);
}

// --- Decision Distribution (Stacked Horizontal Bar) ---
function renderDecisionDistribution(canvasId, data) {
  const canvas = document.getElementById(canvasId);
  if (!canvas || !data.per_role) return null;

  const roles = Object.keys(data.per_role).sort();
  const decisions = ['strong_hire', 'hire', 'maybe', 'no_hire', 'strong_no_hire'];

  const datasets = decisions.map(d => ({
    label: d.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()),
    data: roles.map(r => (data.per_role[r].decisions[d] || 0)),
    backgroundColor: DECISION_COLORS[d],
    borderRadius: 3,
    borderSkipped: false,
  }));

  return new Chart(canvas, {
    type: 'bar',
    data: { labels: roles, datasets },
    options: {
      indexAxis: 'y',
      responsive: true,
      maintainAspectRatio: false,
      animation: { duration: 800 },
      plugins: {
        legend: { position: 'bottom', labels: { padding: 16, usePointStyle: true, pointStyle: 'rectRounded' } },
      },
      scales: {
        x: { stacked: true, grid: { color: '#1a1a2e' }, ticks: { color: '#a0a0b0' } },
        y: { stacked: true, grid: { display: false }, ticks: { color: '#a0a0b0' } },
      },
      onClick: (evt, elements) => {
        if (elements.length > 0) {
          const idx = elements[0].index;
          const role = roles[idx];
          const entries = data.entries.filter(e => e.role === role);
          showModal(`${role} — All Feedback`, entries);
        }
      },
    },
  });
}

// --- Agreement Matrix (HTML table heatmap) ---
function renderAgreementMatrix(data) {
  const container = document.getElementById('agreement-heatmap');
  if (!data.agreement_matrix || Object.keys(data.agreement_matrix).length === 0) {
    container.innerHTML = '<p class="text-muted text-center">Need interviews with shared candidates to compute agreement</p>';
    return;
  }

  // Build unique interviewers from pairs
  const interviewerSet = new Set();
  Object.values(data.agreement_matrix).forEach(v => {
    interviewerSet.add(v.interviewer_a);
    interviewerSet.add(v.interviewer_b);
  });
  const interviewers = [...interviewerSet].sort();

  // Build lookup
  const lookup = {};
  Object.values(data.agreement_matrix).forEach(v => {
    const key = [v.interviewer_a, v.interviewer_b].sort().join('|');
    lookup[key] = v.rate;
  });

  let html = '<table class="heatmap-table"><thead><tr><th></th>';
  interviewers.forEach(i => {
    const short = i.split(' ').map(w => w[0]).join('');
    html += `<th title="${i}">${short}</th>`;
  });
  html += '</tr></thead><tbody>';

  interviewers.forEach(a => {
    html += `<tr><th style="white-space:nowrap;font-size:0.8rem;">${a}</th>`;
    interviewers.forEach(b => {
      if (a === b) {
        html += '<td class="heatmap-cell" style="background:#1a1a2e;color:#6b6b7b;">—</td>';
      } else {
        const key = [a, b].sort().join('|');
        const val = lookup[key];
        if (val !== undefined) {
          const hue = val * 1.2;
          const bg = `hsl(${hue}, 70%, 25%)`;
          const aEsc = a.replace(/'/g, "\\'");
          const bEsc = b.replace(/'/g, "\\'");
          html += `<td class="heatmap-cell" style="background:${bg};color:#fff;" onclick="agreementClick('${aEsc}','${bEsc}')">${val}%</td>`;
        } else {
          html += '<td class="heatmap-cell empty">—</td>';
        }
      }
    });
    html += '</tr>';
  });

  html += '</tbody></table>';
  container.innerHTML = html;
}

function agreementClick(a, b) {
  if (!appData) return;
  // Find shared candidates
  const candidatesA = new Set(appData.entries.filter(e => e.interviewer === a).map(e => e.candidate));
  const entries = appData.entries.filter(e =>
    (e.interviewer === a || e.interviewer === b) && candidatesA.has(e.candidate) &&
    appData.entries.some(x => x.candidate === e.candidate && x.interviewer === (e.interviewer === a ? b : a))
  );
  showModal(`${a} vs ${b} — Shared Candidates`, entries);
}

// --- Score Distribution (Grouped Bar) ---
function renderScoreDistribution(canvasId, data) {
  const canvas = document.getElementById(canvasId);
  if (!canvas || !data.per_interviewer) return null;

  const interviewers = Object.keys(data.per_interviewer).sort();
  const scores = ['1', '2', '3', '4', '5'];

  const datasets = interviewers.map((name, i) => ({
    label: name,
    data: scores.map(s => data.per_interviewer[name].score_distribution[s] || 0),
    backgroundColor: INTERVIEWER_COLORS[i % INTERVIEWER_COLORS.length],
    borderRadius: 3,
  }));

  return new Chart(canvas, {
    type: 'bar',
    data: { labels: scores.map(s => 'Score ' + s), datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: { duration: 800 },
      plugins: {
        legend: { position: 'bottom', labels: { padding: 12, usePointStyle: true, pointStyle: 'rectRounded', font: { size: 10 } } },
      },
      scales: {
        x: { grid: { display: false }, ticks: { color: '#a0a0b0' } },
        y: { grid: { color: '#1a1a2e' }, ticks: { color: '#a0a0b0', stepSize: 1 }, beginAtZero: true },
      },
      onClick: (evt, elements) => {
        if (elements.length > 0) {
          const dsIndex = elements[0].datasetIndex;
          const scoreIndex = elements[0].index;
          const name = interviewers[dsIndex];
          const score = parseInt(scores[scoreIndex]);
          const entries = data.entries.filter(e => e.interviewer === name && e.score === score);
          showModal(`${name} — Score ${score}`, entries);
        }
      },
    },
  });
}

// --- Theme Radar ---
function renderThemeRadar(canvasId, data) {
  const canvas = document.getElementById(canvasId);
  if (!canvas || !data.theme_frequencies) return null;

  const themes = Object.keys(data.theme_frequencies).sort();
  const values = themes.map(t => data.theme_frequencies[t]);
  const labels = themes.map(t => t.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()));

  return new Chart(canvas, {
    type: 'radar',
    data: {
      labels,
      datasets: [{
        label: 'Frequency',
        data: values,
        backgroundColor: 'rgba(79, 143, 255, 0.15)',
        borderColor: ACCENT.blue,
        borderWidth: 2,
        pointBackgroundColor: ACCENT.blue,
        pointBorderColor: '#fff',
        pointRadius: 4,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: { duration: 800 },
      plugins: { legend: { display: false } },
      scales: {
        r: {
          grid: { color: '#1a1a2e' },
          angleLines: { color: '#1a1a2e' },
          ticks: { color: '#6b6b7b', backdropColor: 'transparent' },
          pointLabels: { color: '#a0a0b0', font: { size: 11 } },
        },
      },
    },
  });
}

// --- Sentiment Timeline ---
function renderSentimentTimeline(canvasId, data) {
  const canvas = document.getElementById(canvasId);
  if (!canvas || !data.sentiment_timeline) return null;

  const months = Object.keys(data.sentiment_timeline).sort();
  const values = months.map(m => data.sentiment_timeline[m]);

  const labels = months.map(m => {
    const [y, mo] = m.split('-');
    const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    return monthNames[parseInt(mo) - 1] + ' ' + y.slice(2);
  });

  return new Chart(canvas, {
    type: 'line',
    data: {
      labels,
      datasets: [{
        label: 'Avg Sentiment',
        data: values,
        borderColor: ACCENT.blue,
        backgroundColor: (ctx) => {
          const gradient = ctx.chart.ctx.createLinearGradient(0, 0, 0, ctx.chart.height);
          gradient.addColorStop(0, 'rgba(79, 143, 255, 0.2)');
          gradient.addColorStop(1, 'rgba(79, 143, 255, 0)');
          return gradient;
        },
        fill: true,
        tension: 0.4,
        borderWidth: 2,
        pointBackgroundColor: ACCENT.blue,
        pointBorderColor: '#12121a',
        pointBorderWidth: 2,
        pointRadius: 5,
        pointHoverRadius: 7,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: { duration: 800 },
      plugins: { legend: { display: false } },
      scales: {
        x: { grid: { color: '#1a1a2e' }, ticks: { color: '#a0a0b0' } },
        y: {
          grid: { color: '#1a1a2e' },
          ticks: { color: '#a0a0b0' },
          suggestedMin: -1,
          suggestedMax: 1,
        },
      },
    },
  });
}

// --- Consistency Gauge (Doughnut) ---
function renderConsistencyGauge(canvasId, data) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return null;

  const score = data.consistency_score || 0;
  let color = ACCENT.red;
  if (score >= 70) color = ACCENT.green;
  else if (score >= 40) color = ACCENT.yellow;

  return new Chart(canvas, {
    type: 'doughnut',
    data: {
      labels: ['Consistency', 'Remaining'],
      datasets: [{
        data: [score, 100 - score],
        backgroundColor: [color, 'rgba(255,255,255,0.04)'],
        borderWidth: 0,
        circumference: 270,
        rotation: 225,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: '80%',
      animation: { duration: 1200, easing: 'easeOutQuart' },
      plugins: {
        legend: { display: false },
        tooltip: { enabled: false },
      },
    },
    plugins: [{
      id: 'gaugeText',
      afterDraw(chart) {
        const { ctx, chartArea: { top, bottom, left, right } } = chart;
        const centerX = (left + right) / 2;
        const centerY = (top + bottom) / 2 + 15;
        ctx.save();
        ctx.textAlign = 'center';
        ctx.fillStyle = color;
        ctx.font = 'bold 2.5rem -apple-system, sans-serif';
        ctx.fillText(Math.round(score), centerX, centerY);
        ctx.fillStyle = '#a0a0b0';
        ctx.font = '0.75rem -apple-system, sans-serif';
        ctx.fillText('out of 100', centerX, centerY + 24);
        ctx.restore();
      },
    }],
  });
}

// --- Word Cloud (HTML) ---
function renderWordCloud(containerId, data) {
  const container = document.getElementById(containerId);
  if (!container || !data.word_frequencies) return;

  container.innerHTML = '';
  const words = Object.entries(data.word_frequencies);
  if (words.length === 0) {
    container.innerHTML = '<p class="text-muted">No word data available</p>';
    return;
  }

  const maxFreq = Math.max(...words.map(([, v]) => v));
  const minFreq = Math.min(...words.map(([, v]) => v));
  const colors = [ACCENT.blue, ACCENT.green, ACCENT.purple, ACCENT.yellow, ACCENT.cyan, ACCENT.pink, ACCENT.orange];

  // Shuffle for visual variety
  const shuffled = words.sort(() => Math.random() - 0.5);

  shuffled.forEach(([word, freq], i) => {
    const span = document.createElement('span');
    span.className = 'word-cloud-word';
    span.textContent = word;
    const normalized = minFreq === maxFreq ? 0.5 : (freq - minFreq) / (maxFreq - minFreq);
    const size = 0.65 + normalized * 1.6;
    const opacity = 0.4 + normalized * 0.6;
    span.style.fontSize = size + 'rem';
    span.style.fontWeight = normalized > 0.5 ? '600' : '400';
    span.style.color = colors[i % colors.length];
    span.style.opacity = opacity;
    span.title = `${word}: ${freq} occurrences`;
    container.appendChild(span);
  });
}

// --- Red Flags (HTML List) ---
function renderRedFlags(containerId, data) {
  const container = document.getElementById(containerId);
  if (!container) return;

  container.innerHTML = '';
  const flags = data.red_flags || [];

  if (flags.length === 0) {
    container.innerHTML = '<li class="text-muted" style="padding:20px;text-align:center;">No red flags detected — hiring calibration looks healthy</li>';
    return;
  }

  flags.forEach(flag => {
    const li = document.createElement('li');
    li.className = `red-flag-item severity-${flag.severity}`;
    const icon = flag.severity === 'high' ? '&#9888;' : '&#9432;';
    li.innerHTML = `
      <span class="red-flag-icon">${icon}</span>
      <span class="red-flag-text">${flag.description}</span>
      <span class="red-flag-severity ${flag.severity}">${flag.severity}</span>
    `;

    if (flag.interviewer) {
      li.style.cursor = 'pointer';
      li.addEventListener('click', () => {
        const entries = appData.entries.filter(e => e.interviewer === flag.interviewer);
        showModal(`${flag.interviewer} — All Feedback`, entries);
      });
    }

    container.appendChild(li);
  });
}
