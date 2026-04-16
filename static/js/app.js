/* HireSignal — Main Application Logic */

let appData = null;
let chartInstances = {};
let chatSessionId = sessionStorage.getItem('interviewInsightsChatSessionId') || crypto.randomUUID();
sessionStorage.setItem('interviewInsightsChatSessionId', chatSessionId);
let chatThinkingTimer = null;
let deckThinkingTimer = null;

// --- Page Routing ---
function switchPage(page) {
  document.querySelectorAll('.sidebar-nav a').forEach(l => l.classList.toggle('active', l.dataset.page === page));
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.getElementById('page-' + page).classList.add('active');
  if (page === 'settings') renderSettingsPage();
  if (page === 'interviewers' && appData) renderInterviewersPage();
  if (page === 'roles' && appData) renderRolesPage();
  if (page === 'copilot') renderDeckLibrary();
  if (page === 'insights' && appData) loadInsights();
}

document.querySelectorAll('.sidebar-nav a').forEach(link => {
  link.addEventListener('click', e => {
    e.preventDefault();
    switchPage(link.dataset.page);
  });
});

document.addEventListener('click', e => {
  const btn = e.target.closest('[data-page-jump]');
  if (!btn) return;
  switchPage(btn.dataset.pageJump);
});

// --- Data Fetching ---
async function fetchData(params = {}) {
  const query = new URLSearchParams(params).toString();
  const url = '/api/data' + (query ? '?' + query : '');
  const res = await fetch(url);
  appData = await res.json();
  renderDatasetScope();
  renderDatasetScopeSummary();
  renderDashboard();
}

function renderDatasetScope() {
  const select = document.getElementById('datasetScope');
  const state = appData?.dataset_state;
  if (!select || !state) return;
  const current = state.active_dataset_id || 'all';
  select.innerHTML = '<option value="all">All datasets</option>';
  (state.datasets || []).forEach(dataset => {
    const opt = document.createElement('option');
    opt.value = dataset.id;
    opt.textContent = `${dataset.name} · ${dataset.entries} items`;
    if (dataset.id === current) opt.selected = true;
    select.appendChild(opt);
  });
}

function renderDatasetScopeSummary() {
  const container = document.getElementById('datasetScopeSummary');
  const state = appData?.dataset_state;
  if (!container || !state) return;
  const activeId = state.active_dataset_id || 'all';
  const activeDataset = (state.datasets || []).find(dataset => dataset.id === activeId);

  if (activeId === 'all' || !activeDataset) {
    container.innerHTML = `
      <div class="dataset-scope-card aggregate">
        <div>
          <div class="dataset-scope-label">Current scope</div>
          <div class="dataset-scope-title">All datasets</div>
          <div class="dataset-scope-copy">You are looking at the combined hiring picture across every imported workspace.</div>
        </div>
        <div class="dataset-scope-metrics">
          <span>${state.datasets.length} workspaces</span>
          <span>${state.all_entries || 0} feedback items</span>
          <span>${state.all_candidates || 0} candidates</span>
        </div>
      </div>
    `;
    return;
  }

  container.innerHTML = `
    <div class="dataset-scope-card">
      <div>
        <div class="dataset-scope-label">Current scope</div>
        <div class="dataset-scope-title">${escapeHtml(activeDataset.name)}</div>
        <div class="dataset-scope-copy">${escapeHtml(activeDataset.source)} workspace focused on ${activeDataset.job_count || activeDataset.role_count || 1} role scope${(activeDataset.job_count || activeDataset.role_count || 1) === 1 ? '' : 's'}.</div>
      </div>
      <div class="dataset-scope-metrics">
        <span>${activeDataset.entries} feedback items</span>
        <span>${activeDataset.interviewer_count || 0} interviewers</span>
        <span>${activeDataset.date_start || 'No date'}${activeDataset.date_end && activeDataset.date_end !== activeDataset.date_start ? ` to ${activeDataset.date_end}` : ''}</span>
      </div>
    </div>
  `;
}

// --- Summary Panel ---
function renderSummary() {
  const s = appData.stats;
  document.getElementById('stat-total').textContent = s.total_interviews;
  document.getElementById('stat-candidates').textContent = s.unique_candidates;
  document.getElementById('stat-review-queue').textContent = s.conflicted_candidates;
  document.getElementById('stat-high-risk').textContent = s.high_risk_interviewers;
  document.getElementById('stat-analysis-coverage').textContent = `${Math.round(s.analysis_coverage || 0)}%`;

  document.getElementById('exec-summary').textContent = appData.executive_summary;

  const insightsList = document.getElementById('insights-list');
  insightsList.innerHTML = '';
  appData.top_insights.forEach(insight => {
    const li = document.createElement('li');
    li.textContent = insight;
    insightsList.appendChild(li);
  });

  renderRecruiterBrief();
}

function renderRecruiterBrief() {
  if (!appData) return;
  const queue = appData.candidate_review_queue || [];
  const topQueue = queue[0];
  const topRisk = (appData.interviewer_risk || [])[0];
  const topRole = (appData.role_health || [])[0];

  const headline = document.getElementById('priority-headline');
  const subline = document.getElementById('priority-subline');
  const talkTrack = document.getElementById('sync-talk-track');
  const priorityList = document.getElementById('priority-list');
  const nextActions = document.getElementById('next-actions');

  if (headline) {
    headline.textContent = topQueue
      ? `${topQueue.candidate} is the clearest candidate to review next.`
      : 'The current hiring picture is stable with no urgent review queue.';
  }

  if (subline) {
    const parts = [];
    if (topRole) parts.push(`${topRole.role} is the noisiest pipeline`);
    if (topRisk) parts.push(`${topRisk.name} is the sharpest interviewer outlier`);
    if (queue.length) parts.push(`${queue.length} candidates need review`);
    subline.textContent = parts.join(' • ') || 'No urgent pressure points detected in the current slice.';
  }

  if (talkTrack) {
    talkTrack.textContent = topRisk
      ? `${topRisk.name} is currently the clearest calibration risk, while ${topRole?.role || 'the main pipeline'} carries the most recruiter review pressure.`
      : appData.executive_summary;
  }

  if (priorityList) {
    const items = [];
    if (topQueue) {
      items.push({
        label: 'Candidate review',
        text: `${topQueue.candidate} has ${topQueue.interview_count} interviews with only ${topQueue.confidence}% confidence.`,
      });
    }
    if (topRisk) {
      items.push({
        label: 'Interviewer drift',
        text: `${topRisk.name} is ${topRisk.stance} with a ${topRisk.pass_rate}% pass rate and ${topRisk.risk_score} risk score.`,
      });
    }
    if (topRole) {
      items.push({
        label: 'Pipeline health',
        text: `${topRole.role} has ${topRole.review_count} review cases and blockers around ${(topRole.top_blockers || []).slice(0, 2).join(' and ') || 'interview consistency'}.`,
      });
    }
    priorityList.innerHTML = items.map(item => `
      <div class="priority-item">
        <div class="priority-item-label">${escapeHtml(item.label)}</div>
        <div class="priority-item-copy">${escapeHtml(item.text)}</div>
      </div>
    `).join('') || '<p class="text-muted">No urgent recruiter actions identified.</p>';
  }

  if (nextActions) {
    const actions = [
      topQueue ? `Review ${topQueue.candidate} with the hiring manager before making a final call.` : 'No urgent candidate review is pending.',
      topRisk ? `Run a quick calibration check on ${topRisk.name} against the current team baseline.` : 'No interviewer calibration issue is currently dominant.',
      topRole ? `Use Copilot to draft a short update on the ${topRole.role} pipeline for the next recruiter sync.` : 'Use Copilot to create a recruiter-facing status update.',
    ];
    nextActions.innerHTML = actions.map(text => `
      <div class="next-action-item">
        <span class="next-action-bullet"></span>
        <span>${escapeHtml(text)}</span>
      </div>
    `).join('');
  }
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

function formatDecisionLabel(value) {
  return (value || '').replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

function getActiveFilters() {
  return {
    role: document.getElementById('filter-role')?.value || '',
    interviewer: document.getElementById('filter-interviewer')?.value || '',
    decision: document.getElementById('filter-decision')?.value || '',
    date_from: document.getElementById('filter-date-from')?.value || '',
    date_to: document.getElementById('filter-date-to')?.value || '',
  };
}

function renderDecisionFunnel(data) {
  const container = document.getElementById('decision-funnel');
  if (!container) return;
  const funnel = data.decision_funnel || [];
  if (funnel.length === 0) {
    container.innerHTML = '<p class="text-muted">No decision data available.</p>';
    return;
  }

  container.innerHTML = funnel.map(step => `
    <div class="funnel-step ${escapeHtml(step.decision)}">
      <div class="funnel-step-head">
        <span class="funnel-step-label">${escapeHtml(step.label)}</span>
        <span class="funnel-step-meta">${step.count} entries · ${step.pct}%</span>
      </div>
      <div class="funnel-bar">
        <div class="funnel-bar-fill ${escapeHtml(step.decision)}" style="width:${Math.max(step.pct, 6)}%"></div>
      </div>
    </div>
  `).join('');
}

function showCandidateReview(candidateName) {
  if (!appData) return;
  const entries = appData.entries.filter(e => e.candidate === candidateName);
  showModal(`${candidateName} — Review Detail`, entries);
}

function renderCandidateReviewQueue(data) {
  const container = document.getElementById('candidate-review-queue');
  if (!container) return;
  const queue = (data.candidate_review_queue || []).slice(0, 10);
  if (queue.length === 0) {
    container.innerHTML = '<p class="text-muted">No candidate review queue items.</p>';
    return;
  }

  container.innerHTML = `
    <div class="signal-table">
      ${queue.map(item => `
        <button class="signal-row candidate-review-row severity-${escapeHtml(item.severity)}" data-candidate="${escapeHtml(item.candidate)}">
          <div class="signal-main">
            <div class="signal-title">${escapeHtml(item.candidate)}</div>
            <div class="signal-subtitle">${escapeHtml(item.role)} · ${item.interview_count} interviews · confidence ${item.confidence}%</div>
          </div>
          <div class="signal-aside">
            <span class="signal-pill ${escapeHtml(item.severity)}">${escapeHtml(item.severity)}</span>
            <span class="signal-meta">${escapeHtml(formatDecisionLabel(item.consensus))}</span>
          </div>
          <div class="signal-detail">${escapeHtml((item.top_blockers || []).join(' • ') || (item.top_supports || []).join(' • ') || 'No extracted reasons')}</div>
        </button>
      `).join('')}
    </div>
  `;

  container.querySelectorAll('.candidate-review-row').forEach(row => {
    row.addEventListener('click', () => showCandidateReview(row.dataset.candidate));
  });
}

function showInterviewerRisk(interviewerName) {
  if (!appData) return;
  const entries = appData.entries.filter(e => e.interviewer === interviewerName);
  showModal(`${interviewerName} — Interviewer Detail`, entries);
}

function renderInterviewerRiskMap(data) {
  const container = document.getElementById('interviewer-risk-map');
  if (!container) return;
  const items = (data.interviewer_risk || []).slice(0, 10);
  if (items.length === 0) {
    container.innerHTML = '<p class="text-muted">No interviewer risk signals available.</p>';
    return;
  }

  container.innerHTML = `
    <div class="signal-table">
      ${items.map(item => `
        <button class="signal-row interviewer-risk-row" data-interviewer="${escapeHtml(item.name)}">
          <div class="signal-main">
            <div class="signal-title">${escapeHtml(item.name)}</div>
            <div class="signal-subtitle">${escapeHtml(item.stance)} · ${item.total} interviews · pass rate delta ${item.pass_rate_delta > 0 ? '+' : ''}${item.pass_rate_delta}%</div>
          </div>
          <div class="signal-aside">
            <span class="signal-pill ${item.risk_score >= 70 ? 'review' : item.risk_score >= 55 ? 'watch' : 'aligned'}">${item.risk_score}</span>
            <span class="signal-meta">${item.disagreement_rate == null ? 'no shared cases' : `${item.disagreement_rate}% disagreement`}</span>
          </div>
          <div class="signal-detail">${escapeHtml(item.top_negative_reason || item.top_positive_reason || 'No extracted reason pattern')}</div>
        </button>
      `).join('')}
    </div>
  `;

  container.querySelectorAll('.interviewer-risk-row').forEach(row => {
    row.addEventListener('click', () => showInterviewerRisk(row.dataset.interviewer));
  });
}

function renderReasonSignals(data) {
  const container = document.getElementById('reason-signals');
  if (!container) return;
  const reasonSignals = data.reason_signals || {};
  const blockers = (reasonSignals.blockers || []).slice(0, 4);
  const positives = (reasonSignals.positive || []).slice(0, 4);
  const negatives = (reasonSignals.negative || []).slice(0, 4);

  container.innerHTML = `
    <div class="signal-columns">
      <div class="signal-column">
        <div class="signal-column-title">Top Blockers</div>
        ${(blockers.length ? blockers : negatives).map(item => `
          <div class="reason-chip negative">
            <div class="reason-chip-head">
              <span>${escapeHtml(item.reason)}</span>
              <span>${item.count}</span>
            </div>
            <div class="reason-chip-meta">${item.no_hire_rate || 0}% no-hire · ${item.candidate_count || 0} candidates</div>
          </div>
        `).join('') || '<p class="text-muted">No blocker patterns found.</p>'}
      </div>
      <div class="signal-column">
        <div class="signal-column-title">Positive Signals</div>
        ${positives.map(item => `
          <div class="reason-chip positive">
            <div class="reason-chip-head">
              <span>${escapeHtml(item.reason)}</span>
              <span>${item.count}</span>
            </div>
            <div class="reason-chip-meta">${item.hire_rate || 0}% hire rate · avg score ${item.avg_score || 0}</div>
          </div>
        `).join('') || '<p class="text-muted">No positive signals found.</p>'}
      </div>
    </div>
  `;
}

function renderRoleHealth(data) {
  const container = document.getElementById('role-health-grid');
  if (!container) return;
  const roles = (data.role_health || []).slice(0, 8);
  if (roles.length === 0) {
    container.innerHTML = '<p class="text-muted">No role-level health data available.</p>';
    return;
  }

  container.innerHTML = `
    <div class="role-health-grid">
      ${roles.map(role => `
        <button class="role-health-card" data-role="${escapeHtml(role.role)}">
          <div class="role-health-head">
            <span class="role-health-title">${escapeHtml(role.role)}</span>
            <span class="role-health-score">${role.review_count} review</span>
          </div>
          <div class="role-health-metrics">
            <span>${role.total} interviews</span>
            <span>${role.pass_rate}% pass</span>
            <span>${role.calibration_spread}% spread</span>
          </div>
          <div class="role-health-detail">${escapeHtml((role.top_blockers || []).join(' • ') || 'No blockers extracted')}</div>
        </button>
      `).join('')}
    </div>
  `;

  container.querySelectorAll('.role-health-card').forEach(card => {
    card.addEventListener('click', () => {
      const entries = appData.entries.filter(e => e.role === card.dataset.role);
      showModal(`${card.dataset.role} — Role Detail`, entries);
    });
  });
}

function renderRoundInsightsPanel(data) {
  const container = document.getElementById('round-insights');
  if (!container) return;
  const rounds = data.round_insights || [];
  if (rounds.length === 0) {
    container.innerHTML = '<p class="text-muted">Round-level deep analysis will appear after enriched signals are available.</p>';
    return;
  }

  container.innerHTML = `
    <div class="signal-table compact">
      ${rounds.map(round => `
        <div class="signal-row static-row">
          <div class="signal-main">
            <div class="signal-title">${escapeHtml(formatDecisionLabel(round.round_type))}</div>
            <div class="signal-subtitle">${round.count} entries · ${round.pass_rate}% pass · avg score ${round.avg_score}</div>
          </div>
          <div class="signal-detail">${escapeHtml(round.top_blocker || round.top_signal || 'No extracted round signal')}</div>
        </div>
      `).join('')}
    </div>
  `;
}

// --- Generate AI Narrative ---
document.getElementById('generateNarrativeBtn').addEventListener('click', async () => {
  const btn = document.getElementById('generateNarrativeBtn');
  const btnText = document.getElementById('narrativeBtnText');
  const spinner = document.getElementById('narrativeSpinner');

  btn.disabled = true;
  btnText.textContent = 'Generating...';
  spinner.style.display = 'inline-block';

  try {
    const res = await fetch('/api/narrative', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    });
    const result = await res.json();
    if (result.narrative) {
      document.getElementById('exec-summary').textContent = result.narrative;
    }
  } catch (err) {
    console.error('Narrative generation failed:', err);
  } finally {
    btn.disabled = false;
    btnText.textContent = 'Generate AI Summary';
    spinner.style.display = 'none';
  }
});

// --- Render Dashboard ---
function renderDashboard() {
  renderSummary();
  populateFilters();

  // Destroy existing charts
  Object.values(chartInstances).forEach(c => { if (c && c.destroy) c.destroy(); });
  chartInstances = {};

  renderDecisionFunnel(appData);
  renderCandidateReviewQueue(appData);
  renderInterviewerRiskMap(appData);
  renderReasonSignals(appData);
  renderRoleHealth(appData);
  renderRoundInsightsPanel(appData);
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
  formData.append('dataset_mode', document.getElementById('uploadDatasetMode')?.value || 'new');
  formData.append('dataset_name', document.getElementById('uploadDatasetName')?.value || '');

  const hasPdf = Array.from(files).some(f => f.name.toLowerCase().endsWith('.pdf'));
  showStatus(hasPdf ? 'Sending files to server…' : 'Uploading...', false);

  try {
    const res = await fetch('/api/upload', { method: 'POST', body: formData });
    const data = await res.json();

    if (!res.ok) {
      showStatus(data.error || 'Upload failed', true);
      return;
    }

    if (data.async && data.job_id) {
      // Poll for job completion
      await pollUploadJob(data.job_id, hasPdf);
    } else {
      // Sync response (non-PDF)
      let msg = `Added ${data.added} entries. Total: ${data.total}`;
      if (data.errors && data.errors.length) msg += ' · Warnings: ' + data.errors.join('; ');
      showStatus(msg, false);
      fetchData();
    }
  } catch (err) {
    showStatus('Upload failed: ' + err.message, true);
  }
}

async function pollUploadJob(jobId, hasPdf) {
  const startMsg = hasPdf
    ? 'AI is reading the PDF — this takes 1–2 minutes…'
    : 'Processing…';
  showStatus(startMsg, false);

  return new Promise(resolve => {
    const interval = setInterval(async () => {
      try {
        const res = await fetch(`/api/upload/status/${jobId}`);
        const job = await res.json();

        const pct = job.progress ? ` (${job.progress}%)` : '';
        showStatus((job.message || 'Processing…') + pct, false);

        if (job.status === 'done') {
          clearInterval(interval);
          const r = job.result || {};
          let msg = `Done — added ${r.added || 0} entries. Total: ${r.total || 0}`;
          if (r.errors && r.errors.length) msg += ' · Warnings: ' + r.errors.join('; ');
          showStatus(msg, false);
          fetchData();
          resolve();
        } else if (job.status === 'error') {
          clearInterval(interval);
          showStatus('Upload failed: ' + (job.message || 'Unknown error'), true);
          resolve();
        }
      } catch (err) {
        clearInterval(interval);
        showStatus('Lost contact with server: ' + err.message, true);
        resolve();
      }
    }, 2000); // poll every 2 seconds
  });
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
      body: JSON.stringify({
        text,
        dataset_mode: document.getElementById('uploadDatasetMode')?.value || 'new',
        dataset_name: document.getElementById('uploadDatasetName')?.value || '',
      }),
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

document.getElementById('datasetScope')?.addEventListener('change', async e => {
  const datasetId = e.target.value || 'all';
  const res = await fetch('/api/datasets/select', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ dataset_id: datasetId }),
  });
  if (res.ok) fetchData();
});

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
  const strip = document.getElementById('teamPriorityStrip');
  if (!grid || !appData || !appData.per_interviewer) return;
  grid.innerHTML = '';
  if (strip) strip.innerHTML = '';

  const riskItems = (appData.interviewer_risk || []).slice(0, 3);
  if (strip && riskItems.length) {
    strip.innerHTML = riskItems.map(item => `
      <div class="focus-card">
        <div class="priority-item-label">${escapeHtml(item.stance)} reviewer</div>
        <div class="role-health-title">${escapeHtml(item.name)}</div>
        <div class="priority-item-copy">${item.pass_rate}% pass rate · ${item.risk_score} risk score · ${item.disagreement_rate == null ? 'no shared cases' : `${item.disagreement_rate}% disagreement`}</div>
      </div>
    `).join('');
  }

  const riskLookup = Object.fromEntries((appData.interviewer_risk || []).map(item => [item.name, item]));
  Object.entries(appData.per_interviewer).sort((a, b) => a[0].localeCompare(b[0])).forEach(([name, stats]) => {
    const card = document.createElement('div');
    card.className = 'interviewer-card';
    card.style.cursor = 'pointer';
    const risk = riskLookup[name] || {};
    const stance = risk.stance || (stats.pass_rate > 65 ? 'lenient' : stats.pass_rate < 35 ? 'strict' : 'balanced');
    const attention = risk.risk_score >= 70 ? 'Needs calibration review' : risk.risk_score >= 55 ? 'Worth recruiter check-in' : 'Generally aligned';
    const topThemes = Object.entries(stats.themes || {})
      .sort((a, b) => b[1] - a[1])
      .slice(0, 3)
      .map(([t]) => t.replace(/_/g, ' '));

    const themePills = topThemes.map(t =>
      `<span class="theme-pill">${t}</span>`
    ).join('');

    card.innerHTML = `
      <div class="interviewer-card-headline">
        <div>
          <div class="interviewer-card-name">${escapeHtml(name)}</div>
          <div class="interviewer-card-kicker">${escapeHtml(stance)} interviewer · ${escapeHtml(attention)}</div>
        </div>
        <span class="signal-pill ${risk.risk_score >= 70 ? 'review' : risk.risk_score >= 55 ? 'watch' : 'aligned'}">${risk.risk_score || 0}</span>
      </div>
      <div class="interviewer-card-stats">
        <div><span class="stat-label-sm">Feedback</span><span class="stat-val-sm">${stats.total}</span></div>
        <div><span class="stat-label-sm">Pass Rate</span><span class="stat-val-sm">${stats.pass_rate}%</span></div>
        <div><span class="stat-label-sm">Avg Score</span><span class="stat-val-sm">${stats.avg_score}/5</span></div>
      </div>
      <div class="interviewer-card-summary">${escapeHtml(risk.top_negative_reason || risk.top_positive_reason || 'No clear repeated pattern yet.')}</div>
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
    grid.innerHTML = '<p class="text-muted">Pick two interviewers to inspect whether they apply the same bar.</p>';
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
      <div class="comparison-stat"><span class="label">Feedback Items</span><span class="value">${stats.total}</span></div>
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
  const strip = document.getElementById('roleSummaryStrip');
  container.innerHTML = '';
  if (rankingsEl) rankingsEl.innerHTML = '';
  if (detailEl) { detailEl.style.display = 'none'; detailEl.innerHTML = ''; }
  if (strip) strip.innerHTML = '';

  if (!appData || !appData.per_role) return;

  // Role Rankings (sorted by difficulty - lowest pass rate first)
  const sortedRoles = Object.entries(appData.per_role)
    .sort((a, b) => (a[1].pass_rate || 0) - (b[1].pass_rate || 0));

  const roleHealth = appData.role_health || [];
  if (strip && roleHealth.length) {
    strip.innerHTML = roleHealth.slice(0, 3).map(role => `
      <div class="focus-card">
        <div class="priority-item-label">${escapeHtml(role.role)}</div>
        <div class="role-health-title">${role.pass_rate}% pass · ${role.review_count} reviews</div>
        <div class="priority-item-copy">${escapeHtml((role.top_blockers || []).slice(0, 2).join(' • ') || 'No repeated blocker extracted')}</div>
      </div>
    `).join('');
  }

  if (rankingsEl) {
    rankingsEl.innerHTML = `
      <h3 style="font-size:0.8rem;text-transform:uppercase;letter-spacing:0.08em;color:var(--text-secondary);margin-bottom:12px;">Where Recruiters Feel Pipeline Friction First</h3>
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
    const health = roleHealth.find(item => item.role === role) || {};

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
      <div class="interviewer-card-kicker">${escapeHtml((health.top_blockers || []).slice(0, 2).join(' • ') || 'No dominant blocker pattern')}</div>
      <div style="display:flex;justify-content:space-between;margin-bottom:12px;">
        <div><span class="text-muted" style="font-size:0.75rem;">INTERVIEWS</span><br><span style="font-size:1.5rem;font-weight:700;">${total}</span></div>
        <div><span class="text-muted" style="font-size:0.75rem;">PASS RATE</span><br><span style="font-size:1.5rem;font-weight:700;color:${prColor};">${pr}%</span></div>
        <div><span class="text-muted" style="font-size:0.75rem;">AVG SCORE</span><br><span style="font-size:1.5rem;font-weight:700;">${stats.avg_score}</span></div>
      </div>
      <div style="display:flex;gap:2px;border-radius:4px;overflow:hidden;">${decisionBars}</div>
      <div class="priority-item-copy" style="margin-top:12px;">${escapeHtml((health.top_supports || []).slice(0, 2).join(' • ') || 'No clear positive signal extracted')}</div>
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
  await checkLlmStatus();
  checkLocalAIStatus();
  // Update PDF source status
  const pdfDot = document.getElementById('pdfStatusDot');
  const pdfText = document.getElementById('pdfStatusText');
  if (pdfDot && pdfText && appData) {
    const n = appData.entries?.length || 0;
    pdfDot.className = n > 0 ? 'status-dot connected' : 'status-dot disconnected';
    pdfText.textContent = n > 0 ? `${n} entries loaded` : 'No data yet';
  }

  await renderDatasetsManager();
  const grid = document.getElementById('sessionsGrid');
  if (!grid) return;
  grid.innerHTML = '<p class="text-muted">Loading snapshots...</p>';

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

async function renderDatasetsManager() {
  const grid = document.getElementById('datasetsGrid');
  const selectA = document.getElementById('compareDatasetA');
  const selectB = document.getElementById('compareDatasetB');
  const compareResult = document.getElementById('datasetCompareResult');
  if (!grid) return;
  grid.innerHTML = '<p class="text-muted">Loading datasets...</p>';
  if (compareResult) compareResult.innerHTML = '';

  try {
    const res = await fetch('/api/datasets');
    const state = await res.json();
    const datasets = state.datasets || [];
    const cards = [{
      id: 'all',
      name: 'All datasets',
      source: 'aggregate',
      created_at: 'Combined view',
      entries: state.all_entries || 0,
      active: state.active_dataset_id === 'all',
      role_count: datasets.reduce((sum, item) => sum + (item.role_count || 0), 0),
      interviewer_count: 0,
      job_count: datasets.length,
      office_count: 0,
      department_count: 0,
      date_start: datasets.map(item => item.date_start).filter(Boolean).sort()[0] || null,
      date_end: datasets.map(item => item.date_end).filter(Boolean).sort().slice(-1)[0] || null,
      aggregate: true,
    }, ...datasets];
    if (!datasets.length) {
      grid.innerHTML = '<p class="text-muted">No datasets yet.</p>';
      if (selectA) selectA.innerHTML = '<option value="">Choose dataset A</option>';
      if (selectB) selectB.innerHTML = '<option value="">Choose dataset B</option>';
      return;
    }

    grid.innerHTML = '';
    cards.forEach(dataset => {
      const card = document.createElement('div');
      card.className = 'dataset-card' + (dataset.active ? ' active' : '') + (dataset.aggregate ? ' aggregate' : '');
      const dateLabel = dataset.date_start
        ? `${dataset.date_start}${dataset.date_end && dataset.date_end !== dataset.date_start ? ` to ${dataset.date_end}` : ''}`
        : 'Date range unavailable';
      card.innerHTML = `
        <div class="dataset-card-head">
          <div>
            <div class="session-filename">${escapeHtml(dataset.name)}</div>
            <div class="session-meta">${dataset.entries} items &middot; ${escapeHtml(dataset.source)} &middot; ${escapeHtml(dataset.created_at)}</div>
          </div>
          <span class="dataset-card-badge">${dataset.active ? 'Active scope' : (dataset.aggregate ? 'Combined view' : 'Saved workspace')}</span>
        </div>
        <div class="dataset-stat-strip">
          <div class="dataset-stat"><span class="dataset-stat-label">Jobs</span><span class="dataset-stat-value">${dataset.job_count || 0}</span></div>
          <div class="dataset-stat"><span class="dataset-stat-label">Roles</span><span class="dataset-stat-value">${dataset.role_count || 0}</span></div>
          <div class="dataset-stat"><span class="dataset-stat-label">Interviewers</span><span class="dataset-stat-value">${dataset.interviewer_count || 0}</span></div>
        </div>
        <div class="dataset-meta-row">
          <span>${dateLabel}</span>
          <span>${dataset.office_count || 0} offices</span>
          <span>${dataset.department_count || 0} departments</span>
        </div>
        <div class="session-actions">
          <button class="btn btn-primary btn-sm" data-activate-dataset="${escapeHtml(dataset.id)}">${dataset.active ? 'Viewing' : 'Open workspace'}</button>
          ${dataset.aggregate ? '' : `<button class="btn btn-secondary btn-sm" data-delete-dataset="${escapeHtml(dataset.id)}" style="color:var(--accent-red);">Delete</button>`}
        </div>
      `;
      card.querySelector('[data-activate-dataset]').addEventListener('click', async () => {
        const r = await fetch('/api/datasets/select', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ dataset_id: dataset.id }),
        });
        if (r.ok) {
          fetchData();
          renderSettingsPage();
        }
      });
      card.querySelector('[data-delete-dataset]')?.addEventListener('click', async () => {
        const r = await fetch(`/api/datasets/${encodeURIComponent(dataset.id)}`, { method: 'DELETE' });
        if (r.ok) {
          fetchData();
          renderSettingsPage();
        }
      });
      grid.appendChild(card);
    });

    [selectA, selectB].forEach(sel => {
      if (!sel) return;
      const current = sel.value;
      sel.innerHTML = '<option value="">Choose dataset</option>';
      datasets.forEach(dataset => {
        const opt = document.createElement('option');
        opt.value = dataset.id;
        opt.textContent = dataset.name;
        if (dataset.id === current) opt.selected = true;
        sel.appendChild(opt);
      });
    });
  } catch (err) {
    grid.innerHTML = '<p class="text-muted">Failed to load datasets.</p>';
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

document.getElementById('runDatasetCompareBtn')?.addEventListener('click', async () => {
  const a = document.getElementById('compareDatasetA')?.value;
  const b = document.getElementById('compareDatasetB')?.value;
  const container = document.getElementById('datasetCompareResult');
  if (!container) return;
  if (!a || !b) {
    container.innerHTML = '<p class="text-muted">Choose two datasets to compare.</p>';
    return;
  }
  const res = await fetch(`/api/datasets/compare?a=${encodeURIComponent(a)}&b=${encodeURIComponent(b)}`);
  const data = await res.json();
  if (!res.ok) {
    container.innerHTML = `<p class="text-muted">${escapeHtml(data.error || 'Comparison failed.')}</p>`;
    return;
  }
  const first = data.dataset_a;
  const second = data.dataset_b;
  const delta = data.delta || {};
  const passLead = delta.pass_rate === 0 ? 'Both datasets are converting at the same rate.' : `${delta.pass_rate > 0 ? escapeHtml(first.summary.name || first.id) : escapeHtml(second.summary.name || second.id)} is passing more candidates by ${Math.abs(delta.pass_rate)} points.`;
  const consistencyLead = delta.consistency_score === 0 ? 'Consistency is tied across both workspaces.' : `${delta.consistency_score > 0 ? escapeHtml(first.summary.name || first.id) : escapeHtml(second.summary.name || second.id)} is more calibrated by ${Math.abs(delta.consistency_score)} points.`;
  container.innerHTML = `
    <div class="dataset-compare-overview">
      <div class="dataset-compare-callout">
        <div class="dataset-compare-kicker">Biggest difference</div>
        <div class="dataset-compare-headline">${passLead}</div>
        <div class="dataset-compare-copy">${consistencyLead}</div>
      </div>
      <div class="dataset-compare-deltas">
        <div class="dataset-delta-pill"><span>Pass-rate delta</span><strong>${delta.pass_rate > 0 ? '+' : ''}${delta.pass_rate || 0} pts</strong></div>
        <div class="dataset-delta-pill"><span>Consistency delta</span><strong>${delta.consistency_score > 0 ? '+' : ''}${delta.consistency_score || 0}</strong></div>
        <div class="dataset-delta-pill"><span>Review queue delta</span><strong>${delta.review_queue > 0 ? '+' : ''}${delta.review_queue || 0}</strong></div>
      </div>
    </div>
    <div class="comparison-grid">
      <div class="comparison-card">
        <h4>${escapeHtml(first.summary.name || first.id)}</h4>
        <div class="comparison-stat"><span class="label">Feedback Items</span><span class="value">${first.stats.total_interviews}</span></div>
        <div class="comparison-stat"><span class="label">Candidates</span><span class="value">${first.stats.unique_candidates}</span></div>
        <div class="comparison-stat"><span class="label">Pass Rate</span><span class="value">${first.stats.overall_pass_rate}%</span></div>
        <div class="comparison-stat"><span class="label">Consistency</span><span class="value">${first.stats.consistency_score}</span></div>
        <div class="comparison-stat"><span class="label">Top role</span><span class="value">${escapeHtml(first.top_role?.role || '—')}</span></div>
        <div class="comparison-stat"><span class="label">Top calibration risk</span><span class="value">${escapeHtml(first.top_interviewer?.name || '—')}</span></div>
        <div class="comparison-insights">${(first.top_insights || []).map(item => `<div class="comparison-insight">${escapeHtml(item)}</div>`).join('')}</div>
      </div>
      <div class="comparison-card">
        <h4>${escapeHtml(second.summary.name || second.id)}</h4>
        <div class="comparison-stat"><span class="label">Feedback Items</span><span class="value">${second.stats.total_interviews}</span></div>
        <div class="comparison-stat"><span class="label">Candidates</span><span class="value">${second.stats.unique_candidates}</span></div>
        <div class="comparison-stat"><span class="label">Pass Rate</span><span class="value">${second.stats.overall_pass_rate}%</span></div>
        <div class="comparison-stat"><span class="label">Consistency</span><span class="value">${second.stats.consistency_score}</span></div>
        <div class="comparison-stat"><span class="label">Top role</span><span class="value">${escapeHtml(second.top_role?.role || '—')}</span></div>
        <div class="comparison-stat"><span class="label">Top calibration risk</span><span class="value">${escapeHtml(second.top_interviewer?.name || '—')}</span></div>
        <div class="comparison-insights">${(second.top_insights || []).map(item => `<div class="comparison-insight">${escapeHtml(item)}</div>`).join('')}</div>
      </div>
    </div>
  `;
});

function appendChatMessage(role, content) {
  const container = document.getElementById('chatMessages');
  if (!container) return;
  // Hide the welcome + starters once conversation starts
  const welcome = container.querySelector('.cop-welcome');
  const starters = container.querySelector('.cop-starters');
  if (welcome) welcome.style.display = 'none';
  if (starters) starters.style.display = 'none';

  const bubble = document.createElement('div');
  bubble.className = `chat-bubble ${role}`;
  if (role === 'assistant') {
    bubble.innerHTML = renderChatMarkdown(content);
  } else {
    bubble.textContent = content;
  }
  container.appendChild(bubble);
  container.scrollTop = container.scrollHeight;
}

function renderInlineMarkdown(text) {
  return escapeHtml(text)
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/`(.+?)`/g, '<code>$1</code>');
}

function renderChatMarkdown(content) {
  const lines = String(content || '').replace(/\r\n/g, '\n').split('\n');
  const parts = [];
  let listItems = [];

  function flushList() {
    if (!listItems.length) return;
    parts.push(`<ul>${listItems.map(item => `<li>${renderInlineMarkdown(item)}</li>`).join('')}</ul>`);
    listItems = [];
  }

  for (const rawLine of lines) {
    const line = rawLine.trimEnd();
    const bulletMatch = line.match(/^\s*[-*]\s+(.*)$/);
    if (bulletMatch) {
      listItems.push(bulletMatch[1]);
      continue;
    }
    if (!line.trim()) {
      flushList();
      continue;
    }
    flushList();
    parts.push(`<p>${renderInlineMarkdown(line.trim())}</p>`);
  }

  flushList();
  return parts.join('');
}

async function renderDeckLibrary() {
  const container = document.getElementById('deckLibrary');
  if (!container) return;
  container.innerHTML = '<p class="text-muted">Loading saved decks...</p>';
  try {
    const res = await fetch('/api/decks');
    const decks = await res.json();
    if (!decks.length) {
      container.innerHTML = '<p class="text-muted">No decks generated yet.</p>';
      return;
    }
    container.innerHTML = '';
    decks.forEach(deck => {
      const card = document.createElement('div');
      card.className = 'deck-library-item';
      card.innerHTML = `
        <div class="deck-library-main">
          <div class="deck-library-title">${escapeHtml(deck.title)}</div>
          <div class="deck-library-meta">${escapeHtml(deck.updated_at)} &middot; ${deck.size_kb} KB</div>
        </div>
        <div class="deck-library-actions">
          <a class="btn btn-primary btn-sm" href="${escapeHtml(deck.url)}" target="_blank" rel="noopener noreferrer">Open</a>
          <button class="btn btn-secondary btn-sm" data-delete-deck="${escapeHtml(deck.filename)}" style="color:var(--accent-red);">Delete</button>
        </div>
      `;
      card.querySelector('[data-delete-deck]').addEventListener('click', async () => {
        const r = await fetch(`/api/decks/${encodeURIComponent(deck.filename)}`, { method: 'DELETE' });
        if (r.ok) renderDeckLibrary();
      });
      container.appendChild(card);
    });
  } catch (err) {
    container.innerHTML = '<p class="text-muted">Failed to load saved decks.</p>';
  }
}

function formatElapsedLabel(ms) {
  const seconds = Math.max(1, Math.round(ms / 1000));
  if (seconds < 60) return `${seconds}s elapsed`;
  const mins = Math.floor(seconds / 60);
  const rem = seconds % 60;
  return `${mins}m ${rem}s elapsed`;
}

function startThinkingSequence(config) {
  const {
    containerId,
    titleId,
    subtitleId,
    elapsedId,
    phaseId,
    buttonId,
    stages,
  } = config;
  const container = document.getElementById(containerId);
  const title = document.getElementById(titleId);
  const subtitle = document.getElementById(subtitleId);
  const elapsed = document.getElementById(elapsedId);
  const phase = phaseId ? document.getElementById(phaseId) : null;
  const button = buttonId ? document.getElementById(buttonId) : null;
  const startedAt = Date.now();

  if (container) container.style.display = container.classList.contains('cop-thinking') ? 'flex' : 'block';
  if (button) button.disabled = true;

  function applyStage() {
    const elapsedMs = Date.now() - startedAt;
    let activeStage = stages[stages.length - 1];
    for (const stage of stages) {
      if (elapsedMs >= stage.at) activeStage = stage;
    }
    if (title) title.textContent = activeStage.title;
    if (subtitle) subtitle.textContent = activeStage.subtitle;
    if (elapsed) elapsed.textContent = formatElapsedLabel(elapsedMs);
    if (phase && activeStage.phase) phase.textContent = activeStage.phase;
  }

  applyStage();
  const timer = window.setInterval(applyStage, 900);
  return () => {
    window.clearInterval(timer);
    if (container) container.style.display = 'none';
    if (button) button.disabled = false;
  };
}

function setChatThinking(isThinking) {
  const thinking = document.getElementById('chatThinking');
  if (!isThinking) {
    if (chatThinkingTimer) {
      chatThinkingTimer();
      chatThinkingTimer = null;
    } else if (thinking) {
      thinking.style.display = 'none';
    }
    // Scroll messages to bottom
    const msgs = document.getElementById('chatMessages');
    if (msgs) msgs.scrollTop = msgs.scrollHeight;
    return;
  }
  if (chatThinkingTimer) chatThinkingTimer();
  chatThinkingTimer = startThinkingSequence({
    containerId: 'chatThinking',
    titleId: 'chatThinkingTitle',
    subtitleId: 'chatThinkingSubtitle',
    elapsedId: 'chatThinkingElapsed',
    buttonId: 'sendChatBtn',
    stages: [
      {
        at: 0,
        title: 'Analyzing your data',
        subtitle: 'Pulling signals from the active dataset...',
      },
      {
        at: 12000,
        title: 'Comparing patterns',
        subtitle: 'Interviewer behavior, conflicts, repeated blockers...',
      },
      {
        at: 30000,
        title: 'Composing answer',
        subtitle: 'Compressing evidence into a direct response...',
      },
      {
        at: 70000,
        title: 'Finishing up',
        subtitle: 'Finalizing the response...',
      },
    ],
  });
}

function setDeckThinking(isThinking) {
  const thinking = document.getElementById('deckThinking');
  if (!isThinking) {
    if (deckThinkingTimer) {
      deckThinkingTimer();
      deckThinkingTimer = null;
    } else if (thinking) {
      thinking.style.display = 'none';
    }
    return;
  }
  if (deckThinkingTimer) deckThinkingTimer();
  deckThinkingTimer = startThinkingSequence({
    containerId: 'deckThinking',
    titleId: 'deckThinkingTitle',
    subtitleId: 'deckThinkingSubtitle',
    elapsedId: 'deckThinkingElapsed',
    phaseId: 'deckThinkingPhase',
    buttonId: 'generateDeckBtn',
    stages: [
      {
        at: 0,
        title: 'Building deck...',
        subtitle: 'Structuring slides and evidence.',
      },
      {
        at: 15000,
        title: 'Composing slides...',
        subtitle: 'Drafting each slide with key findings.',
      },
      {
        at: 40000,
        title: 'Polishing layout...',
        subtitle: 'Balancing stats, bullets, and pacing.',
      },
      {
        at: 80000,
        title: 'Rendering HTML...',
        subtitle: 'Packaging the final presentation.',
      },
    ],
  });
}

async function sendChatMessage() {
  const input = document.getElementById('chatInput');
  const message = input.value.trim();
  if (!message) return;

  appendChatMessage('user', message);
  input.value = '';
  setChatThinking(true);

  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message,
        chat_session_id: chatSessionId,
        filters: getActiveFilters(),
      }),
    });
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.error || 'No answer returned.');
    }
    appendChatMessage('assistant', data.answer || 'No answer returned.');
  } catch (err) {
    appendChatMessage('assistant', 'Chat failed: ' + err.message);
  } finally {
    setChatThinking(false);
    input.focus();
  }
}

document.getElementById('sendChatBtn').addEventListener('click', sendChatMessage);
document.getElementById('chatInput').addEventListener('keydown', e => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    if (!document.getElementById('sendChatBtn').disabled) {
      sendChatMessage();
    }
  }
});

document.getElementById('resetChatBtn').addEventListener('click', async () => {
  const oldSessionId = chatSessionId;
  chatSessionId = crypto.randomUUID();
  sessionStorage.setItem('interviewInsightsChatSessionId', chatSessionId);
  const container = document.getElementById('chatMessages');
  container.innerHTML = `
    <div class="cop-welcome">
      <div class="cop-welcome-icon">
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"><circle cx="12" cy="12" r="10"/><path d="M8 14s1.5 2 4 2 4-2 4-2"/><line x1="9" y1="9" x2="9.01" y2="9"/><line x1="15" y1="9" x2="15.01" y2="9"/></svg>
      </div>
      <h3>What would you like to know?</h3>
      <p>I can answer questions about interviewers, candidates, pipelines, blockers, round effectiveness, and more.</p>
    </div>
    <div class="cop-starters">
      <button class="cop-starter" data-chat-prompt="Why are Jan and Matej reaching different outcomes for PHP candidates?"><span class="cop-starter-icon"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M16 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/><circle cx="8.5" cy="7" r="4"/><path d="M20 8v6M23 11h-6"/></svg></span>Interviewer disagreement</button>
      <button class="cop-starter" data-chat-prompt="What are the top recurring blockers in the PHP Developer pipeline?"><span class="cop-starter-icon"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg></span>Top blockers</button>
      <button class="cop-starter" data-chat-prompt="Which candidates should leadership review first and why?"><span class="cop-starter-icon"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg></span>Review queue</button>
      <button class="cop-starter" data-chat-prompt="Which round seems least predictive right now?"><span class="cop-starter-icon"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg></span>Round effectiveness</button>
      <button class="cop-starter" data-chat-prompt="Summarize the overall hiring health and what needs attention this week"><span class="cop-starter-icon"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 20V10M12 20V4M6 20v-6"/></svg></span>Weekly summary</button>
      <button class="cop-starter" data-chat-prompt="Compare the take-home round vs the technical interview round — which is more predictive?"><span class="cop-starter-icon"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="1" y="4" width="22" height="16" rx="2" ry="2"/><line x1="1" y1="10" x2="23" y2="10"/></svg></span>Compare rounds</button>
    </div>
  `;
  bindStarterButtons();
  try {
    await fetch('/api/chat/reset', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ chat_session_id: oldSessionId }),
    });
  } catch (err) {
    console.warn('Unable to reset server chat thread', err);
  }
});

function bindStarterButtons() {
  document.querySelectorAll('[data-chat-prompt]').forEach(btn => {
    btn.addEventListener('click', () => {
      const input = document.getElementById('chatInput');
      input.value = btn.dataset.chatPrompt || '';
      input.focus();
      autoResizeChatInput();
      sendChatMessage();
    });
  });
}
bindStarterButtons();

document.querySelectorAll('[data-deck-prompt]').forEach(btn => {
  btn.addEventListener('click', () => {
    document.getElementById('deckTopicInput').value = btn.dataset.deckPrompt || '';
    document.getElementById('deckTopicInput').focus();
  });
});

// Auto-resize chat input
function autoResizeChatInput() {
  const input = document.getElementById('chatInput');
  if (!input) return;
  input.style.height = 'auto';
  input.style.height = Math.min(input.scrollHeight, 140) + 'px';
}

document.getElementById('chatInput').addEventListener('input', autoResizeChatInput);

document.getElementById('generateDeckBtn').addEventListener('click', async () => {
  const topic = document.getElementById('deckTopicInput').value.trim();
  const status = document.getElementById('deckStatus');
  status.textContent = 'Generating deck...';
  status.className = 'upload-status visible';
  setDeckThinking(true);

  try {
    const res = await fetch('/api/deck', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        topic,
        filters: getActiveFilters(),
      }),
    });
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.error || 'Deck generation failed');
    }
    const deckUrl = data.deck_url || '';
    const popup = deckUrl ? window.open(deckUrl, '_blank', 'noopener,noreferrer') : null;
    const escapedUrl = escapeHtml(deckUrl);
    if (!popup && deckUrl) {
      status.innerHTML = `Deck generated with ${data.slide_count || 0} slides. <a href="${escapedUrl}" target="_blank" rel="noopener noreferrer">Open saved deck</a>`;
    } else if (deckUrl) {
      status.innerHTML = `Deck generated with ${data.slide_count || 0} slides. <a href="${escapedUrl}" target="_blank" rel="noopener noreferrer">Open again</a>`;
    } else {
      status.textContent = `Deck generated with ${data.slide_count || 0} slides.`;
    }
    status.className = 'upload-status visible';
    renderDeckLibrary();
  } catch (err) {
    status.textContent = 'Deck generation failed: ' + err.message;
    status.className = 'upload-status visible error';
  } finally {
    setDeckThinking(false);
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
      chartId === 'chart-gauge' ? 'gauge' :
      chartId === 'chart-interviewer-bars' ? 'interviewerBars' : null
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

// --- Insights Page ---
let insightsChartInstances = {};

function destroyInsightsCharts() {
  Object.values(insightsChartInstances).forEach(c => { if (c && c.destroy) c.destroy(); });
  insightsChartInstances = {};
}

function showAnalysisStatus(msg, isError) {
  const el = document.getElementById('analysisStatus');
  if (!el) return;
  el.textContent = msg;
  el.className = 'upload-status visible' + (isError ? ' error' : '');
  if (!isError) {
    setTimeout(() => el.classList.remove('visible'), 8000);
  }
}

document.getElementById('runAnalysisBtn').addEventListener('click', async () => {
  const btn = document.getElementById('runAnalysisBtn');
  const btnText = document.getElementById('analysisBtnText');
  const spinner = document.getElementById('analysisSpinner');

  btn.disabled = true;
  btnText.textContent = 'Analyzing...';
  spinner.style.display = 'inline-block';
  showAnalysisStatus('Running deep analysis — this may take up to a minute...', false);

  try {
    const res = await fetch('/api/analyze', { method: 'POST' });
    const result = await res.json();
    if (res.ok) {
      showAnalysisStatus('Analysis complete! Loading insights...', false);
      await loadInsights();
    } else {
      showAnalysisStatus(result.error || 'Analysis failed', true);
    }
  } catch (err) {
    showAnalysisStatus('Analysis failed: ' + err.message, true);
  } finally {
    btn.disabled = false;
    btnText.textContent = 'Refresh Analysis';
    spinner.style.display = 'none';
  }
});

async function loadInsights() {
  destroyInsightsCharts();

  if (appData) {
    renderHiringBar();
    renderScoreDecisions();
    renderCrossRoundCorrelation();
    renderRoundDistribution();
    renderRoundScores();

    const headlineEl = document.getElementById('insights-headline');
    if (headlineEl) {
      const parts = [];
      const s = appData.stats || {};
      if (s.total_interviews) parts.push(`Analyzing <strong>${s.total_interviews}</strong> feedback entries across <strong>${s.unique_interviewers || 0}</strong> interviewers.`);
      if (s.overall_pass_rate != null) {
        const pr = s.overall_pass_rate;
        parts.push(`Overall pass rate is <strong>${pr}%</strong>${pr > 60 ? ' — the bar may be too low.' : pr < 35 ? ' — the bar is set high.' : '.'}`);
      }
      headlineEl.innerHTML = parts.join(' ') || '';
    }
  }

  const coverage = appData?.stats?.analysis_coverage || 0;
  const hasDeepAnalysis = coverage >= 100;
  if (!hasDeepAnalysis) {
    document.getElementById('reasons-section').style.display = 'none';
    document.getElementById('styles-section').style.display = 'none';
    showAnalysisStatus('Cross-round and bar views are ready. Run Deep Analysis to unlock standardized reasons and interviewer writing-style breakdowns.', false);
    return;
  }

  try {
    const [reasonsRes, stylesRes] = await Promise.allSettled([
      fetch('/api/reasons'),
      fetch('/api/styles'),
    ]);

    // Render reasons
    if (reasonsRes.status === 'fulfilled' && reasonsRes.value.ok) {
      const reasonsData = await reasonsRes.value.json();
      renderPositiveReasons(reasonsData);
      renderNegativeReasons(reasonsData);
      renderReasonImpact(reasonsData);
      document.getElementById('reasons-section').style.display = 'block';
    } else {
      document.getElementById('reasons-section').style.display = 'none';
    }

    // Render styles
    if (stylesRes.status === 'fulfilled' && stylesRes.value.ok) {
      const stylesData = await stylesRes.value.json();
      renderStyleProfiles(stylesData);
      document.getElementById('styles-section').style.display = 'block';
    } else {
      document.getElementById('styles-section').style.display = 'none';
    }
  } catch (err) {
    console.error('Failed to load insights:', err);
  }
}

function renderPositiveReasons(data) {
  const container = document.getElementById('positive-reasons-list');
  if (!container) return;
  const reasons = (data.top_positive_reasons || data.positive_reasons || data.positive || []).slice(0, 8);
  if (reasons.length === 0) {
    container.innerHTML = '<p class="text-muted" style="padding:12px;">No positive reasons extracted yet</p>';
    return;
  }
  const maxCount = Math.max(...reasons.map(r => r.count || r.mentions || 1));
  container.innerHTML = reasons.map(r => {
    const count = r.count || r.mentions || 1;
    const pct = Math.max(12, (count / maxCount) * 100);
    const candidates = r.candidates ? r.candidates.slice(0, 3).join(', ') : '';
    return `<div class="ins-reason-row">
      <div class="ins-reason-label">${escapeHtml(r.reason || r.text || '')}</div>
      <div class="ins-reason-bar-wrap">
        <div class="ins-reason-bar"><div class="ins-reason-bar-fill" style="width:${pct}%"></div></div>
        <span class="ins-reason-count">${count}</span>
      </div>
      ${candidates ? `<div class="ins-reason-meta">${escapeHtml(candidates)}</div>` : ''}
    </div>`;
  }).join('');
}

function renderNegativeReasons(data) {
  const container = document.getElementById('negative-reasons-list');
  if (!container) return;
  const reasons = (data.top_negative_reasons || data.negative_reasons || data.negative || []).slice(0, 8);
  if (reasons.length === 0) {
    container.innerHTML = '<p class="text-muted" style="padding:12px;">No negative reasons extracted yet</p>';
    return;
  }
  const maxCount = Math.max(...reasons.map(r => r.count || r.mentions || 1));
  container.innerHTML = reasons.map(r => {
    const count = r.count || r.mentions || 1;
    const pct = Math.max(12, (count / maxCount) * 100);
    const candidates = r.candidates ? r.candidates.slice(0, 3).join(', ') : '';
    return `<div class="ins-reason-row">
      <div class="ins-reason-label">${escapeHtml(r.reason || r.text || '')}</div>
      <div class="ins-reason-bar-wrap">
        <div class="ins-reason-bar"><div class="ins-reason-bar-fill" style="width:${pct}%"></div></div>
        <span class="ins-reason-count">${count}</span>
      </div>
      ${candidates ? `<div class="ins-reason-meta">${escapeHtml(candidates)}</div>` : ''}
    </div>`;
  }).join('');
}

function renderReasonImpact(data) {
  const container = document.getElementById('reason-impact-list');
  if (!container) return;
  const impacts = data.reason_correlations || data.reason_impacts || data.impacts || [];
  if (impacts.length === 0) {
    container.innerHTML = '<p class="text-muted" style="padding:12px;">No impact data available</p>';
    return;
  }
  container.innerHTML = impacts.slice(0, 12).map(item => {
    const impactStr = item.decision_impact || item.impact || '';
    const pctMatch = impactStr.match(/(\d+)%/);
    const pct = pctMatch ? parseInt(pctMatch[1]) : 50;
    const isNegative = impactStr.toLowerCase().includes('no_hire') || impactStr.toLowerCase().includes('no hire');
    const cls = isNegative ? 'negative' : 'positive';
    return `<div class="ins-impact-row">
      <div class="ins-impact-label">${escapeHtml(item.reason || item.text || '')}</div>
      <div class="ins-impact-meter">
        <div class="ins-impact-bar"><div class="ins-impact-fill ${cls}" style="width:${Math.max(10, pct)}%"></div></div>
        <span class="ins-impact-pct ${cls}">${pct}%</span>
      </div>
    </div>`;
  }).join('');
}

function renderStyleProfiles(data) {
  const grid = document.getElementById('style-profiles-grid');
  if (!grid) return;
  const profiles = data.profiles || data.styles || data;
  if (!profiles || (Array.isArray(profiles) && profiles.length === 0)) {
    grid.innerHTML = '<p class="text-muted">No style data available</p>';
    return;
  }

  const profileList = Array.isArray(profiles) ? profiles : Object.entries(profiles).map(([name, p]) => ({ name, ...p }));

  grid.innerHTML = profileList.map(p => {
    const tags = (p.style_tags || p.tags || []).map(t =>
      `<span class="style-tag">${escapeHtml(t)}</span>`
    ).join('');

    const focusAreas = (p.focus_areas || p.areas || []).map(a =>
      `<span class="theme-pill">${escapeHtml(a)}</span>`
    ).join('');

    const quote = p.key_quote || p.quote || '';
    const tone = p.tone || 'neutral';
    const avgLength = p.avg_length || p.avg_feedback_length || '—';

    return `<div class="style-card">
      <div class="style-card-name">${escapeHtml(p.name || p.interviewer || '')}</div>
      ${tags ? `<div class="style-tags">${tags}</div>` : ''}
      ${focusAreas ? `<div class="theme-pills" style="margin-bottom:12px;">${focusAreas}</div>` : ''}
      <div class="style-stats">
        <div>
          <div class="style-stat-label">Tone</div>
          <div class="style-stat-value">${escapeHtml(tone)}</div>
        </div>
        <div>
          <div class="style-stat-label">Avg Length</div>
          <div class="style-stat-value">${avgLength}</div>
        </div>
      </div>
      ${quote ? `<div class="style-quote">"${escapeHtml(quote)}"</div>` : ''}
    </div>`;
  }).join('');
}

function renderHiringBar() {
  if (!appData) return;
  insightsChartInstances.hiringBar = renderHiringBarChart('chart-hiring-bar', appData);
  document.getElementById('hiring-bar-section').style.display = 'block';
}

function renderScoreDecisions() {
  if (!appData) return;
  insightsChartInstances.scoreDecisions = renderScoreDecisionsChart('chart-score-decisions', appData);
}

function renderRoundDistribution() {
  if (!appData) return;
  insightsChartInstances.roundDist = renderRoundDistChart('chart-round-dist', appData);
  document.getElementById('round-correlation-section').style.display = 'block';

  // Build round summary cards
  const summaryEl = document.getElementById('round-summary-cards');
  if (summaryEl && appData.entries) {
    const roundStats = {};
    appData.entries.forEach(e => {
      const rt = e.round_type || 'unknown';
      if (!roundStats[rt]) roundStats[rt] = { total: 0, scoreSum: 0, hires: 0 };
      roundStats[rt].total++;
      roundStats[rt].scoreSum += e.score || 0;
      if (e.decision === 'hire' || e.decision === 'strong_hire') roundStats[rt].hires++;
    });
    const cards = Object.entries(roundStats).sort((a, b) => b[1].total - a[1].total);
    const colorMap = { tech_interview: 'var(--accent-blue)', take_home: 'var(--accent-green)', quiz: 'var(--accent-purple)', unknown: 'var(--text-muted)' };
    summaryEl.innerHTML = cards.map(([rt, s]) => {
      const avg = (s.scoreSum / s.total).toFixed(1);
      const pr = Math.round((s.hires / s.total) * 100);
      const color = colorMap[rt] || 'var(--accent-yellow)';
      const label = rt.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
      return `<div class="ins-round-card">
        <div class="ins-round-card-type">${escapeHtml(label)}</div>
        <div class="ins-round-card-score" style="color:${color}">${avg}</div>
        <div class="ins-round-card-meta">${s.total} entries · ${pr}% pass</div>
      </div>`;
    }).join('');
  }
}

function renderRoundScores() {
  if (!appData) return;
  insightsChartInstances.roundScores = renderRoundScoresChart('chart-round-scores', appData);
}

function renderCrossRoundCorrelation() {
  if (!appData) return;
  const correlations = appData.cross_round_correlation || [];
  const pairSummary = appData.round_pair_summary || {};
  const section = document.getElementById('cross-round-section');
  const tableEl = document.getElementById('cross-round-table');
  const pairEl = document.getElementById('round-pair-summary');
  if (!section || !tableEl) return;

  if (correlations.length === 0) {
    section.style.display = 'block';
    tableEl.innerHTML = '<p class="text-muted">No candidate appears in multiple round types inside the current scope. Switch to All datasets or load both take-home and interview feedback for the same candidates.</p>';
    if (pairEl) pairEl.innerHTML = '';
    return;
  }
  section.style.display = 'block';

  // Render pair summary cards
  if (pairEl && Object.keys(pairSummary).length > 0) {
    pairEl.innerHTML = Object.entries(pairSummary).map(([key, pair]) => {
      const labelA = pair.round_a.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
      const labelB = pair.round_b.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
      const agreeColor = pair.agreement_rate >= 70 ? 'var(--accent-green)' : pair.agreement_rate >= 40 ? 'var(--accent-yellow)' : 'var(--accent-red)';
      return `<div class="ins-round-card">
        <div class="ins-round-card-type">${escapeHtml(labelA)} vs ${escapeHtml(labelB)}</div>
        <div class="ins-round-card-score" style="color:${agreeColor}">${pair.agreement_rate}%</div>
        <div class="ins-round-card-meta">${pair.candidates} candidates · avg diff ${pair.avg_score_diff}</div>
      </div>`;
    }).join('');
  }

  // Get all round types across all candidates
  const allRoundTypes = [...new Set(correlations.flatMap(c => c.round_types))].sort();
  const rtLabels = Object.fromEntries(allRoundTypes.map(rt => [rt, rt.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())]));

  // Build candidate × round matrix
  tableEl.innerHTML = `
    <div class="xr-table-wrap">
      <table class="xr-table">
        <thead>
          <tr>
            <th class="xr-th-name">Candidate</th>
            ${allRoundTypes.map(rt => `<th class="xr-th-round">${escapeHtml(rtLabels[rt])}</th>`).join('')}
            <th class="xr-th-round">Agree?</th>
          </tr>
        </thead>
        <tbody>
          ${correlations.map(c => {
            const agreeCls = c.agreement ? 'xr-agree' : 'xr-disagree';
            return `<tr class="xr-row ${agreeCls}">
              <td class="xr-name">${escapeHtml(c.candidate)}</td>
              ${allRoundTypes.map(rt => {
                const rd = c.rounds[rt];
                if (!rd) return '<td class="xr-cell xr-empty">—</td>';
                const scoreColor = rd.score >= 4 ? 'var(--accent-green)' : rd.score >= 3 ? 'var(--accent-yellow)' : 'var(--accent-red)';
                const decLabel = formatDecisionLabel(rd.decision);
                return `<td class="xr-cell">
                  <div class="xr-score" style="color:${scoreColor}">${rd.score}</div>
                  <div class="xr-decision">${escapeHtml(decLabel)}</div>
                  <div class="xr-interviewer">${escapeHtml(rd.interviewer)}</div>
                </td>`;
              }).join('')}
              <td class="xr-cell xr-agree-cell">
                ${c.agreement
                  ? '<span class="xr-badge xr-badge-yes">Yes</span>'
                  : '<span class="xr-badge xr-badge-no">No</span>'}
              </td>
            </tr>`;
          }).join('')}
        </tbody>
      </table>
    </div>
  `;
}

// --- Greenhouse Integration ---
function greenhouseLog(msg, type) {
  const log = document.getElementById('greenhouseLog');
  if (!log) return;
  const entry = document.createElement('div');
  entry.className = 'greenhouse-log-entry' + (type ? ' ' + type : '');
  entry.textContent = new Date().toLocaleTimeString() + ' — ' + msg;
  log.prepend(entry);
}

function updateGreenhouseUI(state) {
  const dot = document.getElementById('greenhouseStatusDot');
  const text = document.getElementById('greenhouseStatusText');
  const syncBtn = document.getElementById('greenhouseSyncBtn');
  if (!dot || !text) return;

  if (state.connected) {
    dot.className = 'status-dot connected';
    text.textContent = 'Connected' + (state.last_sync ? ' — last sync: ' + state.last_sync : '');
    if (syncBtn) syncBtn.disabled = false;
  } else {
    dot.className = 'status-dot disconnected';
    text.textContent = 'Not connected';
    if (syncBtn) syncBtn.disabled = true;
  }
}

async function checkGreenhouseStatus() {
  try {
    const res = await fetch('/api/greenhouse/status');
    const state = await res.json();
    updateGreenhouseUI(state);
  } catch (err) {
    // Silently ignore — status check is non-critical
  }
}

document.getElementById('greenhouseConnectBtn').addEventListener('click', async () => {
  const apiKey = document.getElementById('greenhouseApiKey').value.trim();
  if (!apiKey) {
    greenhouseLog("Please enter a Greenhouse Harvest API key or type 'mock' for demo data.", 'error');
    return;
  }

  const btn = document.getElementById('greenhouseConnectBtn');
  btn.disabled = true;
  btn.textContent = 'Connecting...';
  greenhouseLog('Connecting to Greenhouse API...');

  try {
    const res = await fetch('/api/greenhouse/connect', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        api_key: apiKey,
        dataset_mode: document.getElementById('uploadDatasetMode')?.value || 'new',
        dataset_name: document.getElementById('uploadDatasetName')?.value || '',
      }),
    });
    const data = await res.json();
    if (res.ok) {
      greenhouseLog('Connected successfully. Loaded ' + data.entries_loaded + ' feedback entries. Total: ' + data.total, 'success');
      updateGreenhouseUI({ connected: true, last_sync: new Date().toLocaleString() });
      fetchData();
    } else {
      greenhouseLog(data.error || 'Connection failed.', 'error');
    }
  } catch (err) {
    greenhouseLog('Connection error: ' + err.message, 'error');
  } finally {
    btn.disabled = false;
    btn.textContent = 'Connect';
  }
});

document.getElementById('greenhouseSyncBtn').addEventListener('click', async () => {
  const btn = document.getElementById('greenhouseSyncBtn');
  btn.disabled = true;
  btn.textContent = 'Syncing...';
  greenhouseLog('Syncing latest data from Greenhouse...');

  try {
    const res = await fetch('/api/greenhouse/sync', { method: 'POST' });
    const data = await res.json();
    if (res.ok) {
      greenhouseLog('Sync complete. ' + data.new_entries + ' new entries added. Total: ' + data.total, 'success');
      updateGreenhouseUI({ connected: true, last_sync: new Date().toLocaleString() });
      fetchData();
    } else {
      greenhouseLog(data.error || 'Sync failed.', 'error');
    }
  } catch (err) {
    greenhouseLog('Sync error: ' + err.message, 'error');
  } finally {
    btn.disabled = false;
    btn.textContent = 'Sync Data';
  }
});

// --- Initialize ---
fetchData();
checkGreenhouseStatus();
checkLlmStatus();

// ── LLM Backend ──────────────────────────────────────────────────────────────
const BACKEND_LABELS = { claude: 'Claude Code', codex: 'Codex CLI', ollama: 'Local (Ollama)' };

async function checkLlmStatus() {
  try {
    const res = await fetch('/api/llm/status');
    const data = await res.json();
    updateLlmUI(data);
  } catch (_) {}
}

function updateLlmUI(data) {
  const { active, available = {}, ollama_model } = data;

  // Sidebar pill
  const dot = document.getElementById('llmStatusDot');
  const label = document.getElementById('llmStatusLabel');
  if (dot && label) {
    const anyAvailable = available[active];
    dot.className = 'status-dot ' + (anyAvailable ? 'connected' : 'disconnected');
    label.textContent = 'AI: ' + (BACKEND_LABELS[active] || active);
  }

  // Backend buttons on settings page
  ['claude', 'codex', 'ollama'].forEach(b => {
    const btn = document.getElementById('llmBtn' + b.charAt(0).toUpperCase() + b.slice(1));
    const avail = document.getElementById('llmAvail' + b.charAt(0).toUpperCase() + b.slice(1));
    if (!btn) return;
    btn.classList.toggle('active', b === active);
    btn.classList.toggle('unavailable', !available[b]);
    if (avail) avail.textContent = available[b] ? 'Available' : 'Not found';
  });

  // Ollama model row
  const modelRow = document.getElementById('llmModelRow');
  const modelInput = document.getElementById('llmOllamaModel');
  if (modelRow) modelRow.style.display = active === 'ollama' ? 'flex' : 'none';
  if (modelInput && ollama_model) modelInput.value = ollama_model;
}

async function switchLlmBackend(backend) {
  const modelInput = document.getElementById('llmOllamaModel');
  const statusEl = document.getElementById('llmSwitchStatus');
  const body = { backend };
  if (backend === 'ollama' && modelInput) body.ollama_model = modelInput.value.trim();

  try {
    const res = await fetch('/api/llm/set', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    const data = await res.json();
    if (res.ok) {
      if (statusEl) {
        statusEl.textContent = `Switched to ${BACKEND_LABELS[data.active] || data.active}`;
        statusEl.className = 'upload-status visible';
        setTimeout(() => statusEl.classList.remove('visible'), 3000);
      }
      await checkLlmStatus();
    } else {
      if (statusEl) {
        statusEl.textContent = data.error || 'Switch failed';
        statusEl.className = 'upload-status visible error';
      }
    }
  } catch (err) {
    if (statusEl) {
      statusEl.textContent = 'Error: ' + err.message;
      statusEl.className = 'upload-status visible error';
    }
  }
}

// Wire up backend buttons
document.getElementById('llmBackendRow')?.addEventListener('click', e => {
  const btn = e.target.closest('[data-backend]');
  if (!btn || btn.classList.contains('unavailable')) return;
  switchLlmBackend(btn.dataset.backend);
});

document.getElementById('llmSaveModelBtn')?.addEventListener('click', () => {
  switchLlmBackend('ollama');
});

// ── Local AI one-click setup ──────────────────────────────────────────────────

let _localAiPollTimer = null;

async function checkLocalAIStatus() {
  try {
    const res = await fetch('/api/local-ai/status');
    const d = await res.json();
    renderLocalAIStatus(d);
  } catch (_) {}
}

function renderLocalAIStatus(d) {
  const set = (id, ok, text) => {
    const dot = document.getElementById('laiDot' + id);
    const status = document.getElementById('laiStatus' + id);
    if (dot) { dot.className = 'lai-dot ' + (ok ? 'ok' : 'fail'); }
    if (status) status.textContent = text;
  };

  set('Ollama',  d.ollama_installed, d.ollama_installed ? 'Installed' : 'Not installed');
  set('Service', d.ollama_running,   d.ollama_running   ? 'Running'   : 'Not running');
  set('Model',   d.model_available,  d.model_available  ? 'Downloaded': 'Not downloaded');

  const nameEl = document.getElementById('laiModelName');
  if (nameEl) nameEl.textContent = d.model || 'qwen3.5:0.8b';

  const btn   = document.getElementById('localAiInstallBtn');
  const badge = document.getElementById('laiReadyBadge');

  if (d.ready) {
    if (btn)   btn.style.display   = 'none';
    if (badge) badge.style.display = 'inline-flex';
  } else {
    if (btn)   btn.style.display   = 'inline-flex';
    if (badge) badge.style.display = 'none';
  }
}

async function startLocalAIInstall() {
  const btn = document.getElementById('localAiInstallBtn');
  const log = document.getElementById('localAiLog');
  if (btn) { btn.disabled = true; btn.textContent = '⏳ Installing…'; }
  if (log) { log.style.display = 'block'; log.textContent = ''; }

  // Set checklist dots to spinning
  ['Ollama','Service','Model'].forEach(id => {
    const dot = document.getElementById('laiDot' + id);
    if (dot) dot.className = 'lai-dot spin';
  });

  try {
    const model = document.getElementById('llmOllamaModel')?.value?.trim() || 'qwen3.5:0.8b';
    const res = await fetch('/api/local-ai/install', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ model }),
    });
    const { job_id } = await res.json();
    pollLocalAIInstall(job_id);
  } catch (err) {
    if (log) log.textContent += 'Failed to start install: ' + err.message + '\n';
    if (btn) { btn.disabled = false; btn.textContent = '⚡ Set Up Local AI'; }
  }
}

function pollLocalAIInstall(jobId) {
  let lastLogLen = 0;
  const log = document.getElementById('localAiLog');

  _localAiPollTimer = setInterval(async () => {
    try {
      const res = await fetch('/api/local-ai/progress/' + jobId);
      const job = await res.json();

      // Append new log lines
      if (log && job.log && job.log.length > lastLogLen) {
        const newLines = job.log.slice(lastLogLen).join('\n');
        log.textContent += newLines + '\n';
        log.scrollTop = log.scrollHeight;
        lastLogLen = job.log.length;
      }

      if (job.status === 'done') {
        clearInterval(_localAiPollTimer);
        await checkLocalAIStatus();
        await checkLlmStatus();
        const btn = document.getElementById('localAiInstallBtn');
        if (btn) { btn.disabled = false; btn.textContent = '⚡ Set Up Local AI'; }
      } else if (job.status === 'failed') {
        clearInterval(_localAiPollTimer);
        if (log) log.textContent += '\n' + (job.error || 'Install failed.') + '\n';
        const btn = document.getElementById('localAiInstallBtn');
        if (btn) { btn.disabled = false; btn.textContent = '⚡ Set Up Local AI'; }
        ['Ollama','Service','Model'].forEach(id => {
          const dot = document.getElementById('laiDot' + id);
          if (dot && dot.classList.contains('spin')) dot.className = 'lai-dot fail';
        });
      }
    } catch (_) {}
  }, 800);
}

document.getElementById('localAiInstallBtn')?.addEventListener('click', startLocalAIInstall);

// Check status whenever settings page is opened (hooked into renderSettingsPage)
const _origRenderSettings = typeof renderSettingsPage === 'function' ? renderSettingsPage : null;
// Also run on page load
checkLocalAIStatus();
