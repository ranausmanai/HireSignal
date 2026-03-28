/* HireSignal — Chart Components */

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

// --- Comparison: Mirrored Pass Rate Bar ---
function renderComparisonPassRate(canvasId, dataA, dataB, nameA, nameB) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return null;

  // Get all roles from both interviewers
  const allRoles = [...new Set([
    ...Object.keys(dataA.roles || {}),
    ...Object.keys(dataB.roles || {})
  ])].sort();

  // Compute pass rate per role for each interviewer
  function getRolePassRates(entries, roles) {
    const result = {};
    roles.forEach(role => {
      const roleEntries = entries.filter(e => e.role === role);
      if (roleEntries.length > 0) {
        const hires = roleEntries.filter(e => e.decision === 'hire' || e.decision === 'strong_hire').length;
        result[role] = Math.round(hires / roleEntries.length * 100);
      } else {
        result[role] = 0;
      }
    });
    return result;
  }

  const entriesA = appData.entries.filter(e => e.interviewer === nameA);
  const entriesB = appData.entries.filter(e => e.interviewer === nameB);
  const ratesA = getRolePassRates(entriesA, allRoles);
  const ratesB = getRolePassRates(entriesB, allRoles);

  return new Chart(canvas, {
    type: 'bar',
    data: {
      labels: allRoles,
      datasets: [
        {
          label: nameA,
          data: allRoles.map(r => -(ratesA[r] || 0)),
          backgroundColor: ACCENT.blue,
          borderRadius: 3,
        },
        {
          label: nameB,
          data: allRoles.map(r => ratesB[r] || 0),
          backgroundColor: ACCENT.green,
          borderRadius: 3,
        }
      ]
    },
    options: {
      indexAxis: 'y',
      responsive: true,
      maintainAspectRatio: false,
      animation: { duration: 800 },
      plugins: {
        legend: { position: 'bottom', labels: { padding: 16, usePointStyle: true, pointStyle: 'rectRounded' } },
        tooltip: {
          callbacks: {
            label: ctx => `${ctx.dataset.label}: ${Math.abs(ctx.raw)}%`
          }
        }
      },
      scales: {
        x: {
          grid: { color: '#1a1a2e' },
          ticks: {
            color: '#a0a0b0',
            callback: v => Math.abs(v) + '%'
          },
          suggestedMin: -100,
          suggestedMax: 100,
        },
        y: { grid: { display: false }, ticks: { color: '#a0a0b0' } },
      },
    },
  });
}

// --- Comparison: Score Distribution Grouped Bar ---
function renderComparisonScores(canvasId, statsA, statsB, nameA, nameB) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return null;

  const scores = ['1', '2', '3', '4', '5'];
  return new Chart(canvas, {
    type: 'bar',
    data: {
      labels: scores.map(s => 'Score ' + s),
      datasets: [
        {
          label: nameA,
          data: scores.map(s => (statsA.score_distribution || {})[s] || 0),
          backgroundColor: ACCENT.blue,
          borderRadius: 3,
        },
        {
          label: nameB,
          data: scores.map(s => (statsB.score_distribution || {})[s] || 0),
          backgroundColor: ACCENT.green,
          borderRadius: 3,
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: { duration: 800 },
      plugins: {
        legend: { position: 'bottom', labels: { padding: 12, usePointStyle: true, pointStyle: 'rectRounded' } },
      },
      scales: {
        x: { grid: { display: false }, ticks: { color: '#a0a0b0' } },
        y: { grid: { color: '#1a1a2e' }, ticks: { color: '#a0a0b0', stepSize: 1 }, beginAtZero: true },
      },
    },
  });
}

// --- Comparison: Decision Donut ---
function renderComparisonDonut(canvasId, stats, name) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return null;

  const decisions = ['strong_hire', 'hire', 'maybe', 'no_hire', 'strong_no_hire'];
  const labels = decisions.map(d => d.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()));
  const values = decisions.map(d => (stats.decisions || {})[d] || 0);
  const colors = decisions.map(d => DECISION_COLORS[d]);

  return new Chart(canvas, {
    type: 'doughnut',
    data: {
      labels,
      datasets: [{
        data: values,
        backgroundColor: colors,
        borderWidth: 0,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: '60%',
      animation: { duration: 800 },
      plugins: {
        legend: { position: 'bottom', labels: { padding: 10, usePointStyle: true, pointStyle: 'rectRounded', font: { size: 10 } } },
      },
    },
  });
}

// --- Comparison: Theme Radar ---
function renderComparisonRadar(canvasId, stats, name, color) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return null;

  const themes = Object.keys(stats.themes || {}).sort();
  if (themes.length === 0) {
    canvas.parentElement.querySelector('.card-title').insertAdjacentHTML('afterend',
      '<p class="text-muted text-center" style="padding:20px;">No theme data</p>');
    return null;
  }
  const values = themes.map(t => stats.themes[t]);
  const labels = themes.map(t => t.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()));

  return new Chart(canvas, {
    type: 'radar',
    data: {
      labels,
      datasets: [{
        label: name,
        data: values,
        backgroundColor: color + '25',
        borderColor: color,
        borderWidth: 2,
        pointBackgroundColor: color,
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
          pointLabels: { color: '#a0a0b0', font: { size: 10 } },
        },
      },
    },
  });
}

// --- Interviewer Pass Rates (Horizontal Bar) ---
function renderInterviewerPassRates(canvasId, data) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return null;

  const leaderboard = data.interviewer_leaderboard || [];
  if (leaderboard.length === 0) {
    canvas.parentElement.querySelector('.card-title').insertAdjacentHTML('afterend',
      '<p class="text-muted text-center" style="padding:20px;">No interviewer data</p>');
    return null;
  }

  // Sort by pass_rate ascending for horizontal bars (top = highest)
  const sorted = [...leaderboard].sort((a, b) => a.pass_rate - b.pass_rate);
  const names = sorted.map(i => {
    let label = i.name;
    if (i.label) label += ` (${i.label})`;
    return label;
  });
  const values = sorted.map(i => i.pass_rate);
  const colors = sorted.map(i => {
    if (i.pass_rate >= 60) return ACCENT.green;
    if (i.pass_rate >= 30) return ACCENT.yellow;
    return ACCENT.red;
  });

  return new Chart(canvas, {
    type: 'bar',
    data: {
      labels: names,
      datasets: [{
        label: 'Pass Rate %',
        data: values,
        backgroundColor: colors,
        borderRadius: 4,
        borderSkipped: false,
        barThickness: 28,
      }],
    },
    options: {
      indexAxis: 'y',
      responsive: true,
      maintainAspectRatio: false,
      animation: { duration: 800 },
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: ctx => `Pass Rate: ${ctx.raw}%`
          }
        }
      },
      scales: {
        x: {
          grid: { color: '#1a1a2e' },
          ticks: { color: '#a0a0b0', callback: v => v + '%' },
          min: 0,
          max: 100,
        },
        y: {
          grid: { display: false },
          ticks: { color: '#a0a0b0', font: { size: 12 } },
        },
      },
      onClick: (evt, elements) => {
        if (elements.length > 0) {
          const idx = elements[0].index;
          const interviewer = sorted[idx].name;
          const entries = data.entries.filter(e => e.interviewer === interviewer);
          showModal(`${interviewer} - All Feedback`, entries);
        }
      },
    },
  });
}

// --- Hiring Bar Chart ---
function renderHiringBarChart(canvasId, data) {
  const canvas = document.getElementById(canvasId);
  if (!canvas || !data || !data.entries) return null;

  // Group entries by score and calculate hire rate
  const scoreGroups = {};
  for (let s = 1; s <= 5; s++) scoreGroups[s] = { total: 0, hires: 0 };

  data.entries.forEach(e => {
    const score = e.score;
    if (score >= 1 && score <= 5) {
      scoreGroups[score].total++;
      if (e.decision === 'hire' || e.decision === 'strong_hire') {
        scoreGroups[score].hires++;
      }
    }
  });

  const labels = ['1', '2', '3', '4', '5'];
  const hireRates = labels.map(s => {
    const g = scoreGroups[parseInt(s)];
    return g.total > 0 ? Math.round((g.hires / g.total) * 100) : 0;
  });

  const barColors = hireRates.map(rate => {
    if (rate >= 60) return ACCENT.green;
    if (rate >= 30) return ACCENT.yellow;
    return ACCENT.red;
  });

  return new Chart(canvas, {
    type: 'bar',
    data: {
      labels: labels.map(s => 'Score ' + s),
      datasets: [{
        label: 'Hire Rate %',
        data: hireRates,
        backgroundColor: barColors,
        borderRadius: 4,
        borderSkipped: false,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: { duration: 800 },
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: ctx => `Hire Rate: ${ctx.raw}%`
          }
        },
      },
      scales: {
        x: { grid: { display: false }, ticks: { color: '#a0a0b0' } },
        y: {
          grid: { color: '#1a1a2e' },
          ticks: { color: '#a0a0b0', callback: v => v + '%' },
          min: 0,
          max: 100,
        },
      },
    },
    plugins: [{
      id: 'thresholdLine',
      afterDraw(chart) {
        const { ctx, chartArea, scales } = chart;
        const yPos = scales.y.getPixelForValue(50);
        ctx.save();
        ctx.beginPath();
        ctx.setLineDash([6, 4]);
        ctx.strokeStyle = 'rgba(251, 191, 36, 0.6)';
        ctx.lineWidth = 2;
        ctx.moveTo(chartArea.left, yPos);
        ctx.lineTo(chartArea.right, yPos);
        ctx.stroke();
        ctx.fillStyle = 'rgba(251, 191, 36, 0.8)';
        ctx.font = '11px -apple-system, sans-serif';
        ctx.fillText('50% threshold', chartArea.right - 90, yPos - 6);
        ctx.restore();
      },
    }],
  });
}

// --- Score Decisions Stacked Bar Chart ---
function renderScoreDecisionsChart(canvasId, data) {
  const canvas = document.getElementById(canvasId);
  if (!canvas || !data || !data.entries) return null;

  const scoreGroups = {};
  for (let s = 1; s <= 5; s++) {
    scoreGroups[s] = { strong_hire: 0, hire: 0, maybe: 0, no_hire: 0, strong_no_hire: 0 };
  }

  data.entries.forEach(e => {
    const score = e.score;
    if (score >= 1 && score <= 5 && scoreGroups[score][e.decision] !== undefined) {
      scoreGroups[score][e.decision]++;
    }
  });

  const labels = ['1', '2', '3', '4', '5'].map(s => 'Score ' + s);
  const decisions = ['strong_hire', 'hire', 'maybe', 'no_hire', 'strong_no_hire'];

  const datasets = decisions.map(d => ({
    label: d.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()),
    data: [1, 2, 3, 4, 5].map(s => scoreGroups[s][d]),
    backgroundColor: DECISION_COLORS[d],
    borderRadius: 3,
    borderSkipped: false,
  }));

  return new Chart(canvas, {
    type: 'bar',
    data: { labels, datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: { duration: 800 },
      plugins: {
        legend: { position: 'bottom', labels: { padding: 12, usePointStyle: true, pointStyle: 'rectRounded', font: { size: 10 } } },
      },
      scales: {
        x: { stacked: true, grid: { display: false }, ticks: { color: '#a0a0b0' } },
        y: { stacked: true, grid: { color: '#1a1a2e' }, ticks: { color: '#a0a0b0', stepSize: 1 }, beginAtZero: true },
      },
    },
  });
}

// --- Round Distribution Doughnut ---
function renderRoundDistChart(canvasId, data) {
  const canvas = document.getElementById(canvasId);
  if (!canvas || !data || !data.entries) return null;

  const roundCounts = {};
  data.entries.forEach(e => {
    const rt = e.round_type || 'unknown';
    roundCounts[rt] = (roundCounts[rt] || 0) + 1;
  });

  const roundTypes = Object.keys(roundCounts).sort();
  const counts = roundTypes.map(r => roundCounts[r]);
  const colors = [ACCENT.blue, ACCENT.green, ACCENT.purple, ACCENT.yellow, ACCENT.cyan, ACCENT.pink, ACCENT.orange, ACCENT.red];

  return new Chart(canvas, {
    type: 'doughnut',
    data: {
      labels: roundTypes.map(r => r.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())),
      datasets: [{
        data: counts,
        backgroundColor: roundTypes.map((_, i) => colors[i % colors.length]),
        borderWidth: 0,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: '55%',
      animation: { duration: 800 },
      plugins: {
        legend: { position: 'bottom', labels: { padding: 12, usePointStyle: true, pointStyle: 'rectRounded', font: { size: 10 } } },
      },
    },
  });
}

// --- Round Scores Horizontal Bar (avg score per round type) ---
function renderRoundScoresChart(canvasId, data) {
  const canvas = document.getElementById(canvasId);
  if (!canvas || !data || !data.entries) return null;

  const roundTypes = [...new Set(data.entries.map(e => e.round_type || 'unknown'))].sort();

  const avgScores = roundTypes.map(rt => {
    const entries = data.entries.filter(e => (e.round_type || 'unknown') === rt);
    if (entries.length === 0) return 0;
    return parseFloat((entries.reduce((sum, e) => sum + e.score, 0) / entries.length).toFixed(2));
  });

  const passRates = roundTypes.map(rt => {
    const entries = data.entries.filter(e => (e.round_type || 'unknown') === rt);
    if (entries.length === 0) return 0;
    const hires = entries.filter(e => e.decision === 'hire' || e.decision === 'strong_hire').length;
    return Math.round((hires / entries.length) * 100);
  });

  const barColors = avgScores.map(s => {
    if (s >= 3.5) return ACCENT.green;
    if (s >= 2.5) return ACCENT.yellow;
    return ACCENT.red;
  });

  return new Chart(canvas, {
    type: 'bar',
    data: {
      labels: roundTypes.map(r => r.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())),
      datasets: [
        {
          label: 'Avg Score',
          data: avgScores,
          backgroundColor: barColors,
          borderRadius: 6,
          borderSkipped: false,
          yAxisID: 'y',
        },
        {
          label: 'Pass Rate %',
          data: passRates,
          type: 'line',
          borderColor: ACCENT.blue,
          backgroundColor: 'rgba(79,143,255,0.1)',
          borderWidth: 2,
          pointRadius: 5,
          pointBackgroundColor: ACCENT.blue,
          tension: 0.3,
          yAxisID: 'y1',
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: { duration: 800 },
      plugins: {
        legend: { position: 'bottom', labels: { padding: 14, usePointStyle: true, font: { size: 11 } } },
        tooltip: {
          callbacks: {
            label: ctx => ctx.dataset.label === 'Pass Rate %' ? `Pass Rate: ${ctx.raw}%` : `Avg Score: ${ctx.raw}/5`,
          },
        },
      },
      scales: {
        x: { grid: { display: false }, ticks: { color: '#a0a0b0', font: { size: 11 } } },
        y: { grid: { color: '#1a1a2e' }, ticks: { color: '#a0a0b0' }, beginAtZero: true, max: 5, title: { display: true, text: 'Avg Score', color: '#6b6b7b', font: { size: 10 } } },
        y1: { position: 'right', grid: { display: false }, ticks: { color: ACCENT.blue, callback: v => v + '%' }, min: 0, max: 100, title: { display: true, text: 'Pass Rate', color: ACCENT.blue, font: { size: 10 } } },
      },
    },
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
