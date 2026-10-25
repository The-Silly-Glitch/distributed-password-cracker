/* === Distributed Password Cracker Dashboard Frontend === */

const REFRESH_MS = 2000;
const HISTORY_LENGTH = 18;

const charts = {
  hashrate: new Array(HISTORY_LENGTH).fill(0),
  workers: new Array(HISTORY_LENGTH).fill(0),
  temp: new Array(HISTORY_LENGTH).fill(0),
  recovered: new Array(HISTORY_LENGTH).fill(0),
};

document.addEventListener('DOMContentLoaded', () => {
  initTheme();
  initModal();
  initForm();
  loadDashboard();
  setInterval(loadDashboard, REFRESH_MS);
});

/* === Theme === */
function initTheme() {
  const saved = localStorage.getItem('crack-theme') || 'mono';
  applyTheme(saved);

  document.querySelectorAll('.theme-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const theme = btn.dataset.theme;
      applyTheme(theme);
      localStorage.setItem('crack-theme', theme);
    });
  });
}

function applyTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme);
  document.querySelectorAll('.theme-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.theme === theme);
  });
}

/* === Modal === */
function initModal() {
  const modal = document.getElementById('submit-modal');
  const openBtn = document.getElementById('btn-open-submit');
  const closeBtn = document.getElementById('btn-close-submit');
  const cancelBtn = document.getElementById('btn-cancel-submit');

  const open = () => modal.classList.add('open');
  const close = () => modal.classList.remove('open');

  openBtn.addEventListener('click', open);
  closeBtn.addEventListener('click', close);
  cancelBtn.addEventListener('click', close);
  modal.addEventListener('click', (e) => { if (e.target === modal) close(); });
}

/* === Job submission === */
function initForm() {
  const form = document.getElementById('job-form');
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const name = document.getElementById('input-job-name').value.trim();
    const algorithm = document.getElementById('select-algo').value;
    const attack_type = document.getElementById('select-strategy').value;
    const priority = parseInt(document.getElementById('input-priority').value, 10);
    const rawHashes = document.getElementById('input-hashes').value.trim();
    const target_hashes = rawHashes.split('\n').map(h => h.trim()).filter(Boolean);

    if (!target_hashes.length) {
      showToast('Enter at least one target hash.', 'error');
      return;
    }

    try {
      const resp = await fetch('/api/jobs', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, algorithm, target_hashes, attack_type, priority })
      });
      const data = await resp.json().catch(() => ({}));
      if (!resp.ok) {
        showToast(data.detail || 'Failed to submit job.', 'error');
        return;
      }
      document.getElementById('submit-modal').classList.remove('open');
      form.reset();
      document.getElementById('input-job-name').value = 'Audit Job #' + Math.floor(Math.random() * 900 + 100);
      showToast('Job dispatched: ' + data.job_id.slice(0, 8), 'success');
      loadDashboard();
    } catch (err) {
      showToast('Network error: ' + err.message, 'error');
    }
  });
}

/* === Dashboard data === */
async function loadDashboard() {
  await Promise.all([
    loadStatus(),
    loadJobs(),
    loadWorkers(),
    loadRecovered()
  ]);
}

async function loadStatus() {
  try {
    const res = await fetch('/api/status');
    if (!res.ok) return;
    const data = await res.json();

    const rate = data.total_hashrate || 0;
    document.getElementById('val-hashrate').textContent = formatRate(rate);
    document.getElementById('val-workers').textContent = data.active_workers || 0;
    document.getElementById('val-worker-status').textContent =
      `${data.active_workers || 0} online / ${Math.max(0, (data.total_workers || 0) - (data.active_workers || 0))} offline`;
    document.getElementById('val-recovered').textContent = data.total_recovered || 0;
    const jobSummary = data.active_jobs > 0
      ? `${data.active_jobs} active`
      : `${data.completed_jobs || 0} completed`;
    document.getElementById('val-active-jobs').textContent = jobSummary;

    const gpu = data.gpu_telemetry || {};
    document.getElementById('val-gpu-name').textContent = gpu.device_name ? `GPU: ${gpu.device_name}` : 'GPU: not detected';
    document.getElementById('val-gpu-temp').textContent = gpu.temperature_c != null ? `${gpu.temperature_c} °C` : '-- °C';
    document.getElementById('val-gpu-mem').textContent =
      gpu.memory_used_mb != null ? `VRAM: ${gpu.memory_used_mb} / ${gpu.memory_total_mb} MB` : 'VRAM: unavailable';

    pushChart('hashrate', rate);
    pushChart('workers', data.active_workers || 0);
    pushChart('temp', gpu.temperature_c || 0);
    pushChart('recovered', data.total_recovered || 0);

    renderCharts();
  } catch (err) {
    console.error('Status fetch error:', err);
  }
}

async function loadJobs() {
  try {
    const res = await fetch('/api/jobs');
    if (!res.ok) return;
    const jobs = await res.json();
    const container = document.getElementById('jobs-container');

    if (!jobs.length) {
      container.innerHTML = emptyState('No jobs queued. Submit a job to start the cluster.', '◉');
      return;
    }

    // Separate and sort: running first, then queued, then completed
    const order = { in_progress: 0, queued: 1, completed: 2 };
    jobs.sort((a, b) => (order[a.status] ?? 1) - (order[b.status] ?? 1));

    container.innerHTML = jobs.map(job => {
      const recovered = Math.min(job.recovered_count || 0, job.target_count || 0);
      const isDone = job.status === 'completed';
      const pct = isDone ? 100 : Math.min(job.percent_complete || 0, 100);
      const etaText = isDone
        ? 'Done'
        : job.eta_seconds != null
          ? `ETA ${formatDuration(job.eta_seconds)}`
          : 'ETA calculating…';
      const progressLabel = isDone && pct === 100 && (job.progress || 0) < (job.total_candidates || 0)
        ? `Keyspace ${(job.progress || 0).toLocaleString()} / ${(job.total_candidates || 0).toLocaleString()} · All targets recovered`
        : `Progress ${(job.progress || 0).toLocaleString()} / ${(job.total_candidates || 0).toLocaleString()}`;
      return `
        <div class="job">
          <div class="job-top">
            <div>
              <div class="job-name">${escapeHtml(job.name)}</div>
              <div class="job-algo">${job.algorithm.toUpperCase()} · Priority ${job.priority} · ${job.attack_type.replace('_', ' ')}</div>
            </div>
            <span class="status status-${job.status.replace('_', '-')}">${job.status.replace('_', ' ')}</span>
          </div>
          <div class="progress-wrap">
            <div class="progress-track">
              <div class="progress-fill" style="width: ${pct}%"></div>
            </div>
          </div>
          <div class="job-stats">
            <span>${progressLabel}</span>
            <span>Recovered ${recovered}/${job.target_count || 0} · ${etaText}</span>
          </div>
        </div>
      `;
    }).join('');
  } catch (err) {
    console.error('Jobs fetch error:', err);
  }
}

async function loadWorkers() {
  try {
    const res = await fetch('/api/workers');
    if (!res.ok) return;
    const workers = await res.json();
    const container = document.getElementById('workers-container');

    if (!workers.length) {
      container.innerHTML = emptyState('No workers registered.', '◈');
      return;
    }

    container.innerHTML = workers.map(w => {
      const isOnline = w.status !== 'offline' && w.status !== 'stale';
      const rate = w.hashrate >= 1_000_000
        ? `${(w.hashrate / 1_000_000).toFixed(2)} MH/s`
        : w.hashrate >= 1000
          ? `${(w.hashrate / 1000).toFixed(1)} kH/s`
          : `${Math.round(w.hashrate || 0)} H/s`;
      return `
        <div class="worker ${isOnline ? '' : 'worker-offline'}">
          <div class="worker-icon">${w.gpu_name.toLowerCase().includes('cpu') ? '▣' : '▦'}</div>
          <div class="worker-info">
            <div class="worker-id" title="${escapeHtml(w.id)}">${escapeHtml(w.id.slice(0, 18))}${w.id.length > 18 ? '…' : ''}</div>
            <div class="worker-device" title="${escapeHtml(w.gpu_name)}">${escapeHtml(w.gpu_name)}</div>
          </div>
          <div class="worker-rate">${isOnline ? rate : '<span class="muted">offline</span>'}</div>
        </div>
      `;
    }).join('');
  } catch (err) {
    console.error('Workers fetch error:', err);
  }
}

async function loadRecovered() {
  try {
    const res = await fetch('/api/recovered');
    if (!res.ok) return;
    const list = await res.json();
    // Deduplicate by hash+plaintext
    const seen = new Set();
    const deduped = [];
    for (const item of list) {
      const key = `${item.hash_val}|${item.plaintext}`;
      if (!seen.has(key)) {
        seen.add(key);
        deduped.push(item);
      }
    }
    list.length = 0;
    list.push(...deduped);

    const tbody = document.getElementById('results-tbody');

    if (!list.length) {
      tbody.innerHTML = `
        <tr><td colspan="8" class="empty">
          <div class="empty" style="padding: 28px 0;">
            <div class="empty-icon">🔒</div>
            <p>No credentials recovered yet.</p>
          </div>
        </td></tr>`;
      return;
    }

    tbody.innerHTML = list.map(r => {
      const ana = r.analysis || {};
      const ratingKey = (ana.rating || 'weak').toLowerCase().replace(/\s+/g, '-');
      const timeStr = r.cracked_at ? new Date(r.cracked_at).toLocaleTimeString() : '--';
      return `
        <tr>
          <td><strong>${escapeHtml(r.job_name || r.job_id)}</strong></td>
          <td>${r.algorithm.toUpperCase()}</td>
          <td class="hash-cell" title="${escapeHtml(r.hash_val)}">${escapeHtml(r.hash_val.slice(0, 12))}…</td>
          <td class="plaintext">${escapeHtml(r.plaintext)}</td>
          <td>${ana.entropy_bits != null ? ana.entropy_bits.toFixed(1) + ' bits' : '--'}</td>
          <td><span class="rating rating-${ratingKey}">${ana.rating || 'Unknown'}</span></td>
          <td class="hash-cell">${escapeHtml((r.worker_id || '').slice(0, 12))}</td>
          <td>${timeStr}</td>
        </tr>
      `;
    }).join('');
  } catch (err) {
    console.error('Recovered fetch error:', err);
  }
}

/* === Charts === */
function pushChart(name, value) {
  charts[name].push(value);
  charts[name].shift();
}

function renderCharts() {
  renderMiniChart('hashrate-chart', charts.hashrate, true);
  renderMiniChart('worker-chart', charts.workers, false);
  renderMiniChart('temp-chart', charts.temp, false, 100);
  renderMiniChart('recovered-chart', charts.recovered, false);
}

function renderMiniChart(containerId, data, spark = false, maxOverride = null) {
  const container = document.getElementById(containerId);
  if (!container) return;
  const max = maxOverride || Math.max(...data, 1);
  const min = Math.min(...data);
  const range = max - min || 1;
  container.innerHTML = data.map(v => {
    let h = ((v - min) / range) * 100;
    if (spark && h < 15) h = Math.max(h, 6);
    if (!spark) h = Math.max(h, 4);
    return `<div class="metric-bar" style="height: ${h}%"></div>`;
  }).join('');
}

/* === Helpers === */
function formatRate(h) {
  if (h >= 1_000_000_000) return `${(h / 1_000_000_000).toFixed(2)} GH/s`;
  if (h >= 1_000_000) return `${(h / 1_000_000).toFixed(2)} MH/s`;
  if (h >= 1000) return `${(h / 1000).toFixed(1)} kH/s`;
  return `${Math.round(h)} H/s`;
}

function formatDuration(seconds) {
  if (seconds < 60) return `${Math.round(seconds)}s`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${Math.round(seconds % 60)}s`;
  return `${Math.floor(seconds / 3600)}h ${Math.round((seconds % 3600) / 60)}m`;
}

function emptyState(text, icon) {
  return `
    <div class="empty">
      <div class="empty-icon">${escapeHtml(icon)}</div>
      <p>${escapeHtml(text)}</p>
    </div>
  `;
}

function escapeHtml(str) {
  if (str == null) return '';
  return String(str).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

function showToast(message, type = 'info') {
  const toast = document.getElementById('toast');
  toast.textContent = message;
  toast.className = `toast ${type} show`;
  setTimeout(() => toast.classList.remove('show'), 3200);
}
