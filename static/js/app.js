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

// --- Interviewer Comparison ---
function renderComparison() {
  const a = document.getElementById('compare-a').value;
  const b = document.getElementById('compare-b').value;
  const grid = document.getElementById('comparisonGrid');

  if (!a && !b) {
    grid.innerHTML = '<p class="text-muted">Select interviewers above to compare their calibration</p>';
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
      <h4>${name}</h4>
      <div class="comparison-stat"><span class="label">Total Interviews</span><span class="value">${stats.total}</span></div>
      <div class="comparison-stat"><span class="label">Pass Rate</span><span class="value">${stats.pass_rate}%</span></div>
      <div class="comparison-stat"><span class="label">Avg Score</span><span class="value">${stats.avg_score}/5</span></div>
      <div class="comparison-stat"><span class="label">Decisions</span><span class="value" style="font-size:0.8rem">${decisionsStr}</span></div>
      <div class="comparison-stat"><span class="label">Roles Covered</span><span class="value" style="font-size:0.8rem">${rolesStr}</span></div>
    `;

    // Click to show entries
    card.style.cursor = 'pointer';
    card.addEventListener('click', () => {
      const entries = appData.entries.filter(e => e.interviewer === name);
      showModal(`Feedback from ${name}`, entries);
    });

    grid.appendChild(card);
  });
}

document.getElementById('compare-a').addEventListener('change', renderComparison);
document.getElementById('compare-b').addEventListener('change', renderComparison);

// --- Roles Page ---
function renderRolesPage() {
  const container = document.getElementById('roles-content');
  container.innerHTML = '';

  if (!appData.per_role) return;

  Object.entries(appData.per_role).forEach(([role, stats]) => {
    const card = document.createElement('div');
    card.className = 'chart-card';
    card.style.cursor = 'pointer';

    const decisions = stats.decisions;
    const total = stats.total;
    const decisionBars = ['strong_hire', 'hire', 'maybe', 'no_hire', 'strong_no_hire'].map(d => {
      const count = decisions[d] || 0;
      const pct = total > 0 ? (count / total * 100).toFixed(0) : 0;
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
      <div class="card-title">${role}</div>
      <div style="display:flex;justify-content:space-between;margin-bottom:12px;">
        <div><span class="text-muted" style="font-size:0.75rem;">INTERVIEWS</span><br><span style="font-size:1.5rem;font-weight:700;">${total}</span></div>
        <div><span class="text-muted" style="font-size:0.75rem;">AVG SCORE</span><br><span style="font-size:1.5rem;font-weight:700;">${stats.avg_score}</span></div>
      </div>
      <div style="display:flex;gap:2px;border-radius:4px;overflow:hidden;">${decisionBars}</div>
    `;

    card.addEventListener('click', () => {
      const entries = appData.entries.filter(e => e.role === role);
      showModal(`${role} — All Feedback`, entries);
    });

    container.appendChild(card);
  });
}

// --- Initialize ---
fetchData();
