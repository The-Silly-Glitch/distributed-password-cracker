// Live dashboard polling and UI management

const REFRESH_INTERVAL_MS = 2000;

document.addEventListener("DOMContentLoaded", () => {
    initModal();
    initForm();
    loadDashboard();
    setInterval(loadDashboard, REFRESH_INTERVAL_MS);
});

function initModal() {
    const modal = document.getElementById("submit-modal");
    const btnOpen = document.getElementById("btn-open-submit");
    const btnClose = document.getElementById("btn-close-submit");
    const btnCancel = document.getElementById("btn-cancel-submit");

    btnOpen.addEventListener("click", () => modal.classList.add("open"));
    btnClose.addEventListener("click", () => modal.classList.remove("open"));
    btnCancel.addEventListener("click", () => modal.classList.remove("open"));
}

function initForm() {
    const form = document.getElementById("job-form");
    form.addEventListener("submit", async (e) => {
        e.preventDefault();
        const name = document.getElementById("input-job-name").value.trim();
        const algo = document.getElementById("select-algo").value;
        const strategy = document.getElementById("select-strategy").value;
        const priority = parseInt(document.getElementById("input-priority").value, 10);
        const rawHashes = document.getElementById("input-hashes").value.trim();

        const targetHashes = rawHashes.split("\n").map(h => h.trim()).filter(h => h.length > 0);
        if (targetHashes.length === 0) {
            alert("Please enter at least one target hash.");
            return;
        }

        try {
            const resp = await fetch("/api/jobs", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    name,
                    algorithm: algo,
                    target_hashes: targetHashes,
                    attack_type: strategy,
                    priority
                })
            });
            if (!resp.ok) {
                const err = await resp.json();
                alert("Error submitting job: " + (err.detail || "Unknown"));
                return;
            }
            document.getElementById("submit-modal").classList.remove("open");
            form.reset();
            loadDashboard();
        } catch (err) {
            alert("Failed to submit job: " + err.message);
        }
    });
}

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
        const res = await fetch("/api/status");
        if (!res.ok) return;
        const data = await res.json();

        // Format hashrate
        let rateStr = `${data.total_hashrate.toLocaleString()} H/s`;
        if (data.total_hashrate >= 1000000) {
            rateStr = `${(data.total_hashrate / 1000000).toFixed(2)} MH/s`;
        } else if (data.total_hashrate >= 1000) {
            rateStr = `${(data.total_hashrate / 1000).toFixed(1)} kH/s`;
        }
        document.getElementById("val-hashrate").textContent = rateStr;

        document.getElementById("val-workers").textContent = data.active_workers;
        document.getElementById("val-worker-status").textContent = `${data.active_workers} online / ${data.total_workers - data.active_workers} offline`;

        const gpu = data.gpu_telemetry || {};
        document.getElementById("val-gpu-name").textContent = gpu.device_name || "CPU Reference";
        document.getElementById("val-gpu-temp").textContent = gpu.temperature_c ? `${gpu.temperature_c} °C` : "N/A";
        document.getElementById("val-gpu-mem").textContent = gpu.memory_used_mb ? `VRAM: ${gpu.memory_used_mb} / ${gpu.memory_total_mb} MB` : "Memory: System";

        document.getElementById("val-recovered").textContent = data.total_recovered;
        document.getElementById("val-active-jobs").textContent = `${data.active_jobs} Active Jobs`;
    } catch (e) {
        console.error("Status fetch error", e);
    }
}

async function loadJobs() {
    try {
        const res = await fetch("/api/jobs");
        if (!res.ok) return;
        const jobs = await res.json();
        const container = document.getElementById("jobs-container");

        if (jobs.length === 0) {
            container.innerHTML = `<div class="empty-state">No jobs currently queued. Submit a job to begin cracking.</div>`;
            return;
        }

        container.innerHTML = jobs.map(j => {
            const etaText = j.eta_seconds ? `ETA: ${j.eta_seconds}s` : (j.status === 'completed' ? 'Done' : 'ETA: --');
            return `
                <div class="job-card">
                    <div class="job-card-header">
                        <span class="job-name">${escapeHtml(j.name)} [${j.algorithm.toUpperCase()}]</span>
                        <span class="badge ${getStatusBadge(j.status)}">${j.status.toUpperCase()}</span>
                    </div>
                    <div class="progress-bar-bg">
                        <div class="progress-bar-fill" style="width: ${j.percent_complete}%"></div>
                    </div>
                    <div class="job-card-footer">
                        <span>Progress: ${j.progress.toLocaleString()} / ${j.total_candidates.toLocaleString()} (${j.percent_complete}%)</span>
                        <span>Cracked: ${j.recovered_count}/${j.target_count} | ${etaText}</span>
                    </div>
                </div>
            `;
        }).join("");
    } catch (e) {
        console.error("Jobs fetch error", e);
    }
}

async function loadWorkers() {
    try {
        const res = await fetch("/api/workers");
        if (!res.ok) return;
        const workers = await res.json();
        const tbody = document.getElementById("workers-tbody");

        if (workers.length === 0) {
            tbody.innerHTML = `<tr><td colspan="5" class="empty-cell">No workers registered.</td></tr>`;
            return;
        }

        tbody.innerHTML = workers.map(w => {
            const rate = w.hashrate >= 1000 ? `${(w.hashrate / 1000).toFixed(1)} kH/s` : `${w.hashrate} H/s`;
            const task = w.current_range ? `Range: ${w.current_range}` : (w.status === 'idle' ? 'Awaiting Job' : 'Offline');
            return `
                <tr>
                    <td><strong>${escapeHtml(w.id.substring(0, 16))}</strong></td>
                    <td>${escapeHtml(w.gpu_name)}</td>
                    <td><span class="badge badge-${w.status}">${w.status.toUpperCase()}</span></td>
                    <td>${rate}</td>
                    <td><small>${escapeHtml(task)}</small></td>
                </tr>
            `;
        }).join("");
    } catch (e) {
        console.error("Workers fetch error", e);
    }
}

async function loadRecovered() {
    try {
        const res = await fetch("/api/recovered");
        if (!res.ok) return;
        const list = await res.json();
        const tbody = document.getElementById("results-tbody");

        if (list.length === 0) {
            tbody.innerHTML = `<tr><td colspan="8" class="empty-cell">No credentials recovered yet.</td></tr>`;
            return;
        }

        tbody.innerHTML = list.map(r => {
            const ana = r.analysis || {};
            const ratingClass = `rating-${(ana.rating || 'weak').toLowerCase().replace(' ', '-')}`;
            const timeStr = r.cracked_at ? new Date(r.cracked_at).toLocaleTimeString() : "--";
            return `
                <tr>
                    <td><strong>${escapeHtml(r.job_name || r.job_id)}</strong></td>
                    <td><span class="badge">${r.algorithm.toUpperCase()}</span></td>
                    <td><code title="${r.hash_val}">${escapeHtml(r.hash_val.substring(0, 14))}...</code></td>
                    <td><strong style="color: var(--accent); font-family: var(--font-mono);">${escapeHtml(r.plaintext)}</strong></td>
                    <td>${ana.entropy_bits ? ana.entropy_bits + ' bits' : '--'}</td>
                    <td><span class="badge ${ratingClass}">${ana.rating || 'Unknown'}</span></td>
                    <td><small>${escapeHtml(r.worker_id.substring(0, 12))}</small></td>
                    <td><small>${timeStr}</small></td>
                </tr>
            `;
        }).join("");
    } catch (e) {
        console.error("Recovered fetch error", e);
    }
}

function getStatusBadge(status) {
    if (status === 'completed') return 'badge-idle';
    if (status === 'in_progress') return 'badge-busy';
    return 'badge-idle';
}

function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/[&<>'"]/g, tag => ({
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        "'": '&#39;',
        '"': '&quot;'
    }[tag] || tag));
}
