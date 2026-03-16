/* Interview Insights — Main Application Logic */

let appData = null;
let chartInstances = {};

// --- Page Routing ---
document.querySelectorAll('.sidebar-nav a').forEach(link => {
  link.addEventListener('click', e => {
    e.preventDefault();
    const page = link.dataset.page;
    document.querySelectorAll('.sidebar-nav a').forEach(l => l.classList.remove('active'));
    link.classList.add('active');
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    document.getElementById('page-' + page).classList.add('active');
    if (page === 'settings') renderSettingsPage();
    if (page === 'interviewers' && appData) renderInterviewersPage();
    if (page === 'roles' && appData) renderRolesPage();
  });
});

// --- Data Fetching ---
async function fetchData(params = {}) {
  const query = new URLSearchParams(params).toString();
  const url = '/api/data' + (query ? '?' + query : '');
  const res = await fetch(url);
  appData = await res.json();
  renderDashboard();
}

// --- Summary Panel ---
function renderSummary() {
  const s = appData.stats;
  document.getElementById('stat-total').textContent = s.total_interviews;
  document.getElementById('stat-interviewers').textContent = s.unique_interviewers;
  document.getElementById('stat-candidates').textContent = s.unique_candidates;
  document.getElementById('stat-pass-rate').textContent = s.overall_pass_rate + '%';

  const consistency = s.consistency_score;
  const consistencyEl = document.getElementById('stat-consistency');
  consistencyEl.textContent = Math.round(consistency);
  consistencyEl.className = 'stat-value';
  if (consistency >= 70) consistencyEl.classList.add('green');
  else if (consistency >= 40) consistencyEl.classList.add('yellow');
  else consistencyEl.classList.add('red');

  document.getElementById('exec-summary').textContent = appData.executive_summary;

  const insightsList = document.getElementById('insights-list');
  insightsList.innerHTML = '';
  appData.top_insights.forEach(insight => {
    const li = document.createElement('li');
    li.textContent = insight;
    insightsList.appendChild(li);
  });
}

// --- Populate Filters ---
function populateFilters() {
  const roleSelect = document.getElementById('filter-role');
  const interviewerSelect = document.getElementById('filter-interviewer');

  const roles = [...new Set(appData.entries.map(e => e.role))].sort();
  const interviewers = [...new Set(appData.entries.map(e => e.interviewer))].sort();

  // Keep current selection
  const currentRole = roleSelect.value;
  const currentInterviewer = interviewerSelect.value;

  roleSelect.innerHTML = '<option value="">All Roles</option>';
  roles.forEach(r => {
    const opt = document.createElement('option');
    opt.value = r;
    opt.textContent = r;
    if (r === currentRole) opt.selected = true;
    roleSelect.appendChild(opt);
  });

  interviewerSelect.innerHTML = '<option value="">All Interviewers</option>';
  interviewers.forEach(i => {
    const opt = document.createElement('option');
    opt.value = i;
    opt.textContent = i;
    if (i === currentInterviewer) opt.selected = true;
    interviewerSelect.appendChild(opt);
  });

  // Comparison dropdowns
  ['compare-a', 'compare-b'].forEach(id => {
    const sel = document.getElementById(id);
    const current = sel.value;
    sel.innerHTML = '<option value="">Select Interviewer</option>';
    interviewers.forEach(i => {
      const opt = document.createElement('option');
      opt.value = i;
      opt.textContent = i;
      if (i === current) opt.selected = true;
      sel.appendChild(opt);
    });
  });
}

// --- Render Dashboard ---
function renderDashboard() {
  renderSummary();
  populateFilters();

  // Destroy existing charts
  Object.values(chartInstances).forEach(c => { if (c && c.destroy) c.destroy(); });
  chartInstances = {};

  // Render all charts
  renderCalibrationHeatmap(appData);
  chartInstances.decisions = renderDecisionDistribution('chart-decisions', appData);
  renderAgreementMatrix(appData);
  chartInstances.scores = renderScoreDistribution('chart-scores', appData);
  chartInstances.themes = renderThemeRadar('chart-themes', appData);
  chartInstances.sentiment = renderSentimentTimeline('chart-sentiment', appData);
  chartInstances.gauge = renderConsistencyGauge('chart-gauge', appData);
  renderWordCloud('word-cloud', appData);
  renderRedFlags('red-flags', appData);
  renderInterviewersPage();
  renderRolesPage();
}

// --- Filter Handling ---
document.getElementById('applyFilters').addEventListener('click', () => {
  const params = {};
  const role = document.getElementById('filter-role').value;
  const interviewer = document.getElementById('filter-interviewer').value;
  const decision = document.getElementById('filter-decision').value;
  const dateFrom = document.getElementById('filter-date-from').value;
  const dateTo = document.getElementById('filter-date-to').value;
  if (role) params.role = role;
  if (interviewer) params.interviewer = interviewer;
  if (decision) params.decision = decision;
  if (dateFrom) params.date_from = dateFrom;
  if (dateTo) params.date_to = dateTo;
  fetchData(params);
});

document.getElementById('clearFilters').addEventListener('click', () => {
  document.getElementById('filter-role').value = '';
  document.getElementById('filter-interviewer').value = '';
  document.getElementById('filter-decision').value = '';
  document.getElementById('filter-date-from').value = '';
  document.getElementById('filter-date-to').value = '';
  fetchData();
});

// --- Upload Handling ---
const dropZone = document.getElementById('dropZone');
const fileInput = document.getElementById('fileInput');

['dragenter', 'dragover'].forEach(evt => {
  dropZone.addEventListener(evt, e => {
    e.preventDefault();
    dropZone.classList.add('dragover');
  });
});

['dragleave', 'drop'].forEach(evt => {
  dropZone.addEventListener(evt, e => {
    e.preventDefault();
    dropZone.classList.remove('dragover');
  });
});

dropZone.addEventListener('drop', e => {
  const files = e.dataTransfer.files;
  if (files.length) uploadFiles(files);
});

fileInput.addEventListener('change', () => {
  if (fileInput.files.length) uploadFiles(fileInput.files);
});

async function uploadFiles(files) {
  const formData = new FormData();
  for (const f of files) formData.append('files', f);

  showStatus('Uploading...', false);
  try {
    const res = await fetch('/api/upload', { method: 'POST', body: formData });
    const data = await res.json();
    if (res.ok) {
      showStatus(`Successfully added ${data.added} feedback entries. Total: ${data.total}`, false);
      fetchData();
    } else {
      showStatus(data.error || 'Upload failed', true);
    }
  } catch (err) {
    showStatus('Upload failed: ' + err.message, true);
  }
}

// --- Paste Handling ---
document.getElementById('submitPaste').addEventListener('click', async () => {
  const text = document.getElementById('pasteArea').value.trim();
  if (!text) return showStatus('Please paste some feedback text first', true);

  showStatus('Processing...', false);
  try {
    const res = await fetch('/api/paste', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text }),
    });
    const data = await res.json();
    if (res.ok) {
      showStatus(`Added ${data.added} feedback entries. Total: ${data.total}`, false);
      document.getElementById('pasteArea').value = '';
      fetchData();
    } else {
      showStatus(data.error || 'Processing failed', true);
    }
  } catch (err) {
    showStatus('Processing failed: ' + err.message, true);
  }
});

document.getElementById('clearPaste').addEventListener('click', () => {
  document.getElementById('pasteArea').value = '';
});

// --- Upload Tabs ---
document.querySelectorAll('.upload-tab').forEach(tab => {
  tab.addEventListener('click', () => {
    document.querySelectorAll('.upload-tab').forEach(t => t.classList.remove('active'));
    tab.classList.add('active');
    document.querySelectorAll('.upload-content').forEach(c => c.classList.remove('active'));
    document.getElementById('tab-' + tab.dataset.tab).classList.add('active');
  });
});

function showStatus(msg, isError) {
  const el = document.getElementById('uploadStatus');
  el.textContent = msg;
  el.className = 'upload-status visible' + (isError ? ' error' : '');
  setTimeout(() => el.classList.remove('visible'), 5000);
}

// --- Reset ---
document.getElementById('resetBtn').addEventListener('click', async () => {
  await fetch('/api/reset', { method: 'POST' });
  // Clear filters
  document.getElementById('filter-role').value = '';
  document.getElementById('filter-interviewer').value = '';
  document.getElementById('filter-decision').value = '';
  document.getElementById('filter-date-from').value = '';
  document.getElementById('filter-date-to').value = '';
  fetchData();
});

// --- Modal ---
function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

function showModal(title, entries) {
  document.getElementById('modal-title').textContent = title;
  const body = document.getElementById('modal-body');
  body.innerHTML = '';

  if (!entries || entries.length === 0) {
    body.innerHTML = '<p class="text-muted">No matching feedback entries found.</p>';
  } else {
    entries.forEach(entry => {
      const div = document.createElement('div');
      div.className = 'feedback-entry';
      const decisionLabel = entry.decision.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
      div.innerHTML = `
        <div class="feedback-entry-header">
          <span class="feedback-tag interviewer">${escapeHtml(entry.interviewer)}</span>
          <span class="feedback-tag candidate">${escapeHtml(entry.candidate)}</span>
          <span class="feedback-tag decision-${escapeHtml(entry.decision)}">${escapeHtml(decisionLabel)}</span>
          <span class="text-muted">${escapeHtml(entry.role)} &middot; Score: ${entry.score}/5 &middot; ${escapeHtml(entry.date)}</span>
        </div>
        <div class="feedback-text">${escapeHtml(entry.feedback_text)}</div>
      `;
      body.appendChild(div);
    });
  }

  document.getElementById('modal').classList.add('active');
}

document.getElementById('modalClose').addEventListener('click', () => {
  document.getElementById('modal').classList.remove('active');
});

document.getElementById('modal').addEventListener('click', e => {
  if (e.target === document.getElementById('modal')) {
    document.getElementById('modal').classList.remove('active');
  }
});

// --- Interviewer Cards Grid ---
function renderInterviewersPage() {
  const grid = document.getElementById('interviewerCardsGrid');
  if (!grid || !appData || !appData.per_interviewer) return;
  grid.innerHTML = '';

  Object.entries(appData.per_interviewer).sort((a, b) => a[0].localeCompare(b[0])).forEach(([name, stats]) => {
    const card = document.createElement('div');
    card.className = 'interviewer-card';
    card.style.cursor = 'pointer';

    // Pass rate color
    let prClass = 'red';
    if (stats.pass_rate > 60) prClass = 'green';
    else if (stats.pass_rate >= 40) prClass = 'yellow';

    // Top 3 themes
    const topThemes = Object.entries(stats.themes || {})
      .sort((a, b) => b[1] - a[1])
      .slice(0, 3)
      .map(([t]) => t.replace(/_/g, ' '));

    const themePills = topThemes.map(t =>
      `<span class="theme-pill">${t}</span>`
    ).join('');

    card.innerHTML = `
      <h4 class="interviewer-card-name">${escapeHtml(name)}</h4>
      <div class="interviewer-card-stats">
        <div><span class="stat-label-sm">Interviews</span><span class="stat-val-sm">${stats.total}</span></div>
        <div><span class="stat-label-sm">Pass Rate</span><span class="stat-val-sm ${prClass}">${stats.pass_rate}%</span></div>
        <div><span class="stat-label-sm">Avg Score</span><span class="stat-val-sm">${stats.avg_score}/5</span></div>
      </div>
      <div class="theme-pills">${themePills || '<span class="text-muted" style="font-size:0.75rem;">No themes</span>'}</div>
    `;

    card.addEventListener('click', () => {
      const entries = appData.entries.filter(e => e.interviewer === name);
      showModal(`Feedback from ${name}`, entries);
    });

    grid.appendChild(card);
  });
}

// --- Interviewer Comparison ---
let comparisonChartInstances = {};

function destroyComparisonCharts() {
  Object.values(comparisonChartInstances).forEach(c => { if (c && c.destroy) c.destroy(); });
  comparisonChartInstances = {};
}

function renderComparison() {
  const a = document.getElementById('compare-a').value;
  const b = document.getElementById('compare-b').value;
  const grid = document.getElementById('comparisonGrid');
  const chartsContainer = document.getElementById('comparisonCharts');
  const gapSection = document.getElementById('calibrationGapSection');

  destroyComparisonCharts();

  if (!a && !b) {
    grid.innerHTML = '<p class="text-muted">Select interviewers above to compare their calibration</p>';
    if (chartsContainer) chartsContainer.style.display = 'none';
    return;
  }

  const interviewers = [a, b].filter(Boolean);
  grid.innerHTML = '';

  interviewers.forEach(name => {
    const stats = appData.per_interviewer[name];
    if (!stats) return;

    const card = document.createElement('div');
    card.className = 'comparison-card';
    const decisionsStr = Object.entries(stats.decisions)
      .map(([k, v]) => `${k.replace(/_/g, ' ')}: ${v}`)
      .join(', ');
    const rolesStr = Object.entries(stats.roles)
      .map(([k, v]) => `${k}: ${v}`)
      .join(', ');

    card.innerHTML = `
      <h4>${escapeHtml(name)}</h4>
      <div class="comparison-stat"><span class="label">Total Interviews</span><span class="value">${stats.total}</span></div>
      <div class="comparison-stat"><span class="label">Pass Rate</span><span class="value">${stats.pass_rate}%</span></div>
      <div class="comparison-stat"><span class="label">Avg Score</span><span class="value">${stats.avg_score}/5</span></div>
      <div class="comparison-stat"><span class="label">Decisions</span><span class="value" style="font-size:0.8rem">${decisionsStr}</span></div>
      <div class="comparison-stat"><span class="label">Roles Covered</span><span class="value" style="font-size:0.8rem">${rolesStr}</span></div>
    `;

    card.style.cursor = 'pointer';
    card.addEventListener('click', () => {
      const entries = appData.entries.filter(e => e.interviewer === name);
      showModal(`Feedback from ${name}`, entries);
    });

    grid.appendChild(card);
  });

  // If both selected, show comparison charts
  if (a && b && appData.per_interviewer[a] && appData.per_interviewer[b]) {
    const statsA = appData.per_interviewer[a];
    const statsB = appData.per_interviewer[b];
    chartsContainer.style.display = 'block';

    comparisonChartInstances.passRate = renderComparisonPassRate('chart-compare-passrate', statsA, statsB, a, b);
    comparisonChartInstances.scores = renderComparisonScores('chart-compare-scores', statsA, statsB, a, b);
    comparisonChartInstances.donutA = renderComparisonDonut('chart-compare-donut-a', statsA, a);
    comparisonChartInstances.donutB = renderComparisonDonut('chart-compare-donut-b', statsB, b);
    comparisonChartInstances.radarA = renderComparisonRadar('chart-compare-radar-a', statsA, a, ACCENT.blue);
    comparisonChartInstances.radarB = renderComparisonRadar('chart-compare-radar-b', statsB, b, ACCENT.green);

    // Calibration Gap Score
    const gap = Math.abs(statsA.pass_rate - statsB.pass_rate);
    let gapColor = 'var(--accent-green)';
    if (gap > 30) gapColor = 'var(--accent-red)';
    else if (gap > 15) gapColor = 'var(--accent-yellow)';

    gapSection.innerHTML = `
      <div class="calibration-gap-card">
        <div class="stat-label-sm" style="text-align:center;margin-bottom:8px;">CALIBRATION GAP SCORE</div>
        <div style="font-size:3rem;font-weight:700;text-align:center;color:${gapColor};">${gap.toFixed(1)}%</div>
        <p class="text-muted" style="text-align:center;font-size:0.8rem;margin-top:8px;">
          Absolute difference in pass rates between ${escapeHtml(a)} and ${escapeHtml(b)}
        </p>
      </div>
    `;
  } else {
    if (chartsContainer) chartsContainer.style.display = 'none';
  }
}

document.getElementById('compare-a').addEventListener('change', renderComparison);
document.getElementById('compare-b').addEventListener('change', renderComparison);

// --- Roles Page ---
let expandedRole = null;

function renderRolesPage() {
  const container = document.getElementById('roles-content');
  const rankingsEl = document.getElementById('roleRankings');
  const detailEl = document.getElementById('roleDetail');
  container.innerHTML = '';
  if (rankingsEl) rankingsEl.innerHTML = '';
  if (detailEl) { detailEl.style.display = 'none'; detailEl.innerHTML = ''; }

  if (!appData || !appData.per_role) return;

  // Role Rankings (sorted by difficulty - lowest pass rate first)
  const sortedRoles = Object.entries(appData.per_role)
    .sort((a, b) => (a[1].pass_rate || 0) - (b[1].pass_rate || 0));

  if (rankingsEl) {
    rankingsEl.innerHTML = `
      <h3 style="font-size:0.8rem;text-transform:uppercase;letter-spacing:0.08em;color:var(--text-secondary);margin-bottom:12px;">Role Rankings by Difficulty</h3>
      <div class="role-rankings-bar">
        ${sortedRoles.map(([role, stats], i) => {
          const pr = stats.pass_rate || 0;
          let prColor = 'var(--accent-red)';
          if (pr > 60) prColor = 'var(--accent-green)';
          else if (pr >= 40) prColor = 'var(--accent-yellow)';
          return `<div class="role-rank-item">
            <span class="role-rank-num">#${i + 1}</span>
            <span class="role-rank-name">${role}</span>
            <span class="role-rank-pr" style="color:${prColor};">${pr}%</span>
          </div>`;
        }).join('')}
      </div>
    `;
  }

  // Role Cards
  Object.entries(appData.per_role).forEach(([role, stats]) => {
    const card = document.createElement('div');
    card.className = 'chart-card role-card';
    card.style.cursor = 'pointer';

    const decisions = stats.decisions;
    const total = stats.total;
    const pr = stats.pass_rate || 0;
    let prColor = 'var(--accent-red)';
    if (pr > 60) prColor = 'var(--accent-green)';
    else if (pr >= 40) prColor = 'var(--accent-yellow)';

    const decisionBars = ['strong_hire', 'hire', 'maybe', 'no_hire', 'strong_no_hire'].map(d => {
      const count = decisions[d] || 0;
      const colors = {
        strong_hire: 'var(--accent-green)',
        hire: '#6ee7b7',
        maybe: 'var(--accent-yellow)',
        no_hire: '#fca5a5',
        strong_no_hire: 'var(--accent-red)',
      };
      return count > 0 ? `<div style="flex:${count};background:${colors[d]};height:8px;border-radius:4px;" title="${d.replace(/_/g,' ')}: ${count}"></div>` : '';
    }).join('');

    card.innerHTML = `
      <div class="card-title">${escapeHtml(role)}</div>
      <div style="display:flex;justify-content:space-between;margin-bottom:12px;">
        <div><span class="text-muted" style="font-size:0.75rem;">INTERVIEWS</span><br><span style="font-size:1.5rem;font-weight:700;">${total}</span></div>
        <div><span class="text-muted" style="font-size:0.75rem;">PASS RATE</span><br><span style="font-size:1.5rem;font-weight:700;color:${prColor};">${pr}%</span></div>
        <div><span class="text-muted" style="font-size:0.75rem;">AVG SCORE</span><br><span style="font-size:1.5rem;font-weight:700;">${stats.avg_score}</span></div>
      </div>
      <div style="display:flex;gap:2px;border-radius:4px;overflow:hidden;">${decisionBars}</div>
    `;

    card.addEventListener('click', () => {
      expandRoleDetail(role, stats);
    });

    container.appendChild(card);
  });
}

function expandRoleDetail(role, stats) {
  const detailEl = document.getElementById('roleDetail');
  if (!detailEl) return;

  if (expandedRole === role) {
    detailEl.style.display = 'none';
    expandedRole = null;
    return;
  }
  expandedRole = role;

  const interviewers = stats.interviewers || {};
  const interviewerEntries = Object.entries(interviewers).sort((a, b) => a[1].pass_rate - b[1].pass_rate);

  let toughest = null, lenient = null;
  if (interviewerEntries.length > 0) {
    toughest = interviewerEntries[0];
    lenient = interviewerEntries[interviewerEntries.length - 1];
  }

  let html = `
    <div class="chart-card full-width">
      <div class="card-title">${escapeHtml(role)} — Interviewer Breakdown</div>
      ${toughest && lenient ? `
        <div style="display:flex;gap:24px;margin-bottom:16px;">
          <div class="role-label-badge tough">Toughest: ${escapeHtml(toughest[0])} (${toughest[1].pass_rate}%)</div>
          <div class="role-label-badge lenient">Most Lenient: ${escapeHtml(lenient[0])} (${lenient[1].pass_rate}%)</div>
        </div>
      ` : ''}
      <table class="heatmap-table" style="width:100%;">
        <thead><tr><th style="text-align:left;">Interviewer</th><th>Interviews</th><th>Pass Rate</th><th>Avg Score</th></tr></thead>
        <tbody>
          ${interviewerEntries.map(([iname, istats]) => {
            const hue = istats.pass_rate * 1.2;
            return `<tr>
              <th style="text-align:left;font-size:0.85rem;">${escapeHtml(iname)}</th>
              <td class="heatmap-cell" style="background:transparent;color:var(--text-primary);">${istats.total}</td>
              <td class="heatmap-cell" style="background:hsl(${hue},70%,25%);color:#fff;">${istats.pass_rate}%</td>
              <td class="heatmap-cell" style="background:transparent;color:var(--text-primary);">${istats.avg_score}</td>
            </tr>`;
          }).join('')}
        </tbody>
      </table>
      <div style="margin-top:16px;">
        <button class="btn btn-secondary" onclick="showModal('${escapeHtml(role)} — All Feedback', appData.entries.filter(e => e.role === '${role.replace(/'/g, "\\'")}'))">View All Entries</button>
      </div>
    </div>
  `;

  detailEl.innerHTML = html;
  detailEl.style.display = 'block';
  detailEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

// --- Settings Page ---
function showSessionsStatus(msg, isError) {
  const el = document.getElementById('sessionsStatus');
  if (!el) return;
  el.textContent = msg;
  el.className = 'upload-status visible' + (isError ? ' error' : '');
  setTimeout(() => el.classList.remove('visible'), 5000);
}

async function renderSettingsPage() {
  const grid = document.getElementById('sessionsGrid');
  if (!grid) return;
  grid.innerHTML = '<p class="text-muted">Loading sessions...</p>';

  try {
    const res = await fetch('/api/sessions');
    const sessions = await res.json();
    if (sessions.length === 0) {
      grid.innerHTML = '<p class="text-muted">No saved sessions yet.</p>';
      return;
    }

    grid.innerHTML = '';
    sessions.forEach(session => {
      const card = document.createElement('div');
      card.className = 'session-card';
      card.innerHTML = `
        <div class="session-info">
          <div class="session-filename">${escapeHtml(session.filename)}</div>
          <div class="session-meta">${session.entries} entries &middot; ${escapeHtml(session.date)}</div>
        </div>
        <div class="session-actions">
          <button class="btn btn-primary btn-sm" data-load="${escapeHtml(session.filename)}">Load</button>
          <button class="btn btn-secondary btn-sm" data-delete="${escapeHtml(session.filename)}" style="color:var(--accent-red);">Delete</button>
        </div>
      `;

      card.querySelector('[data-load]').addEventListener('click', async () => {
        const r = await fetch('/api/sessions/load', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ filename: session.filename }),
        });
        if (r.ok) {
          showSessionsStatus(`Loaded session: ${session.filename}`, false);
          fetchData();
        } else {
          showSessionsStatus('Failed to load session', true);
        }
      });

      card.querySelector('[data-delete]').addEventListener('click', async () => {
        const r = await fetch(`/api/sessions/${encodeURIComponent(session.filename)}`, { method: 'DELETE' });
        if (r.ok) {
          showSessionsStatus('Session deleted', false);
          renderSettingsPage();
        }
      });

      grid.appendChild(card);
    });
  } catch (err) {
    grid.innerHTML = '<p class="text-muted">Failed to load sessions.</p>';
  }
}

document.getElementById('saveSessionBtn').addEventListener('click', async () => {
  const res = await fetch('/api/save', { method: 'POST' });
  if (res.ok) {
    showSessionsStatus('Session saved successfully', false);
    renderSettingsPage();
  } else {
    showSessionsStatus('Failed to save session', true);
  }
});

document.getElementById('clearDataBtn').addEventListener('click', async () => {
  if (!confirm('Clear all current data and reload sample data?')) return;
  const res = await fetch('/api/clear', { method: 'DELETE' });
  if (res.ok) {
    showSessionsStatus('Data cleared, sample data reloaded', false);
    fetchData();
  }
});

document.getElementById('deleteAllSessionsBtn').addEventListener('click', async () => {
  if (!confirm('Delete ALL saved sessions? This cannot be undone.')) return;
  const res = await fetch('/api/sessions', { method: 'DELETE' });
  if (res.ok) {
    showSessionsStatus('All sessions deleted', false);
    renderSettingsPage();
  }
});

// --- Export: Chart PNG ---
document.querySelectorAll('.chart-export-btn').forEach(btn => {
  btn.addEventListener('click', e => {
    e.stopPropagation();
    const chartId = btn.dataset.chart;

    // Check if it's a Chart.js canvas
    const chartInstance = chartInstances[
      chartId === 'chart-decisions' ? 'decisions' :
      chartId === 'chart-scores' ? 'scores' :
      chartId === 'chart-themes' ? 'themes' :
      chartId === 'chart-sentiment' ? 'sentiment' :
      chartId === 'chart-gauge' ? 'gauge' : null
    ];

    if (chartInstance) {
      const link = document.createElement('a');
      link.download = chartId + '.png';
      link.href = chartInstance.toBase64Image();
      link.click();
      return;
    }

    // For HTML-based charts (heatmaps, word cloud), use html2canvas-like approach via canvas
    const el = document.getElementById(chartId);
    if (!el) return;

    // Fallback: capture via selection range / simple text export
    const text = el.innerText;
    const blob = new Blob([text], { type: 'text/plain' });
    const link = document.createElement('a');
    link.download = chartId + '.txt';
    link.href = URL.createObjectURL(blob);
    link.click();
    URL.revokeObjectURL(link.href);
  });
});

// --- Export: Global CSV Report ---
document.getElementById('exportReportBtn').addEventListener('click', () => {
  if (!appData) return;

  let csv = '';

  // Section 1: Summary Stats
  csv += 'SUMMARY STATS\n';
  csv += 'Metric,Value\n';
  csv += `Total Interviews,${appData.stats.total_interviews}\n`;
  csv += `Unique Interviewers,${appData.stats.unique_interviewers}\n`;
  csv += `Unique Candidates,${appData.stats.unique_candidates}\n`;
  csv += `Overall Pass Rate,${appData.stats.overall_pass_rate}%\n`;
  csv += `Consistency Score,${appData.stats.consistency_score}\n`;
  csv += '\n';

  // Section 2: Per-Interviewer Stats
  csv += 'PER-INTERVIEWER STATS\n';
  csv += 'Interviewer,Total Interviews,Pass Rate,Avg Score\n';
  Object.entries(appData.per_interviewer).sort((a, b) => a[0].localeCompare(b[0])).forEach(([name, stats]) => {
    csv += `"${name}",${stats.total},${stats.pass_rate}%,${stats.avg_score}\n`;
  });
  csv += '\n';

  // Section 3: Per-Role Stats
  csv += 'PER-ROLE STATS\n';
  csv += 'Role,Total Interviews,Pass Rate,Avg Score\n';
  Object.entries(appData.per_role).sort((a, b) => a[0].localeCompare(b[0])).forEach(([role, stats]) => {
    csv += `"${role}",${stats.total},${stats.pass_rate || 'N/A'}%,${stats.avg_score}\n`;
  });
  csv += '\n';

  // Section 4: Red Flags
  csv += 'RED FLAGS\n';
  csv += 'Description,Severity\n';
  (appData.red_flags || []).forEach(flag => {
    csv += `"${flag.description.replace(/"/g, '""')}",${flag.severity}\n`;
  });
  csv += '\n';

  // Section 5: Agreement Matrix
  csv += 'AGREEMENT MATRIX\n';
  csv += 'Pair,Agreement Rate,Shared Candidates\n';
  Object.entries(appData.agreement_matrix || {}).forEach(([pair, data]) => {
    csv += `"${pair}",${data.rate !== null ? data.rate + '%' : 'N/A'},${data.total}\n`;
  });

  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
  const link = document.createElement('a');
  link.download = 'interview-insights-report.csv';
  link.href = URL.createObjectURL(blob);
  link.click();
  URL.revokeObjectURL(link.href);
});

// --- Initialize ---
fetchData();
