/**
 * dashboard.js — Analytics, Statistics, Master Detections Table, and Inspection Modals
 * Interacts with SQLite backend API to keep all civic metrics, charts, and tables up-to-date.
 */

const DashboardModule = (() => {
    let severityChart = null;
    let currentDetectionsCache = [];
    let currentClustersCache = [];
    let activeInspectedId = null;

    function init() {
        setupToolbarFilters();
        setupModalControls();
        setupExportAndUtilityButtons();
        refreshAll();
    }

    async function refreshAll() {
        await Promise.all([
            fetchAndRenderStats(),
            fetchAndRenderDetections(),
            fetchAndRenderClusters()
        ]);
    }

    // -------------------------------------------------------------------------
    // 1. Fetch & Render Dashboard Statistics & Charts
    // -------------------------------------------------------------------------
    async function fetchAndRenderStats() {
        try {
            const res = await fetch("/api/stats");
            const json = await res.json();
            if (!json.success) return;

            const d = json.data;
            document.getElementById("stat-total-detections").textContent = d.total_detections;
            document.getElementById("stat-potholes").textContent = d.total_potholes;
            document.getElementById("stat-speed-breakers").textContent = d.total_speed_breakers;
            document.getElementById("stat-normal-roads").textContent = d.total_normal_roads;
            document.getElementById("stat-critical-count").textContent = d.total_critical;
            document.getElementById("stat-devices").textContent = d.unique_devices;

            // Update Legend numbers
            const dist = d.severity_distribution || {};
            document.getElementById("legend-low-count").textContent = dist.Low || 0;
            document.getElementById("legend-mod-count").textContent = dist.Moderate || 0;
            document.getElementById("legend-high-count").textContent = dist.High || 0;
            document.getElementById("legend-crit-count").textContent = dist.Critical || 0;

            // Render/Update Chart.js
            updateSeverityChart(dist);

            // Render Recent 10 Detections
            renderRecentDetectionsTable(d.recent_detections || []);
        } catch (err) {
            console.error("Error fetching stats:", err);
        }
    }

    function updateSeverityChart(dist) {
        const canvas = document.getElementById("chart-severity");
        if (!canvas) return;

        const ctx = canvas.getContext("2d");
        const labels = ["Low (0-29)", "Moderate (30-59)", "High (60-79)", "Critical (80-100)"];
        const dataVals = [dist.Low || 0, dist.Moderate || 0, dist.High || 0, dist.Critical || 0];
        const colors = ["#10b981", "#f59e0b", "#f97316", "#dc2626"];

        if (severityChart) {
            severityChart.data.datasets[0].data = dataVals;
            severityChart.update();
            return;
        }

        if (window.Chart) {
            severityChart = new Chart(ctx, {
                type: "doughnut",
                data: {
                    labels: labels,
                    datasets: [{
                        data: dataVals,
                        backgroundColor: colors,
                        borderColor: "#1e293b",
                        borderWidth: 2,
                        hoverOffset: 4
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false }
                    },
                    cutout: "65%"
                }
            });
        }
    }

    function renderRecentDetectionsTable(recent) {
        const tbody = document.getElementById("recent-detections-tbody");
        if (!tbody) return;

        if (recent.length === 0) {
            tbody.innerHTML = `<tr><td colspan="6" class="text-center text-muted">No telemetry received yet.</td></tr>`;
            return;
        }

        tbody.innerHTML = recent.map(r => `
            <tr>
                <td class="font-mono">#${r.id}</td>
                <td><span class="badge-tag">${escapeHtml(r.device_id)}</span></td>
                <td><span class="badge-pill pill-${r.event_type.toLowerCase().replace(/\s+/g, '')}">${r.event_type}</span></td>
                <td>${Math.round(r.confidence * 100)}%</td>
                <td><strong class="text-${getPriorityCssClass(r.priority_level)}">${r.pdi_score}</strong></td>
                <td><span class="text-xs font-mono text-success">✔ SHA-256</span></td>
            </tr>
        `).join("");
    }

    // -------------------------------------------------------------------------
    // 2. Fetch & Render DBSCAN Clusters
    // -------------------------------------------------------------------------
    async function fetchAndRenderClusters() {
        try {
            const res = await fetch("/api/clusters");
            const json = await res.json();
            if (!json.success) return;

            currentClustersCache = json.data;
            renderTopClustersTable(currentClustersCache);

            // Pass clusters to MapModule
            MapModule.renderDetections(currentDetectionsCache, currentClustersCache);
        } catch (err) {
            console.error("Error fetching clusters:", err);
        }
    }

    function renderTopClustersTable(clusters) {
        const tbody = document.getElementById("top-clusters-tbody");
        if (!tbody) return;

        if (!clusters || clusters.length === 0) {
            tbody.innerHTML = `<tr><td colspan="7" class="text-center text-muted">No DBSCAN clusters formed yet (needs &ge; 2 nearby passes).</td></tr>`;
            return;
        }

        tbody.innerHTML = clusters.map(c => `
            <tr>
                <td class="font-mono font-bold">Cluster #${c.cluster_id}</td>
                <td class="font-mono text-xs">${c.center_latitude.toFixed(4)}, ${c.center_longitude.toFixed(4)}</td>
                <td><span class="badge-pill pill-${c.event_type.toLowerCase().replace(/\s+/g, '')}">${c.event_type}</span></td>
                <td><strong>${c.detection_count}</strong></td>
                <td><span class="badge-tag">${c.unique_devices} cars</span></td>
                <td><strong>${c.max_pdi_score}</strong></td>
                <td><span class="badge-pill pill-${c.priority_level.toLowerCase()}">${c.priority_level}</span></td>
            </tr>
        `).join("");
    }

    // -------------------------------------------------------------------------
    // 3. Fetch & Render Master Detections Table
    // -------------------------------------------------------------------------
    async function fetchAndRenderDetections() {
        try {
            const search = document.getElementById("filter-search-input")?.value || "";
            const eventType = document.getElementById("filter-event-type")?.value || "All";
            const priority = document.getElementById("filter-priority")?.value || "All";
            const isSim = document.getElementById("filter-simulated")?.value || "-1";

            const url = new URL("/api/detections", window.location.origin);
            if (search) url.searchParams.set("search", search);
            if (eventType !== "All") url.searchParams.set("event_type", eventType);
            if (priority !== "All") url.searchParams.set("priority", priority);
            if (isSim !== "-1") url.searchParams.set("is_simulated", isSim);
            url.searchParams.set("limit", "200");

            const res = await fetch(url);
            const json = await res.json();
            if (!json.success) return;

            currentDetectionsCache = json.data;
            renderMasterTable(currentDetectionsCache);
            populateTamperDropdown(currentDetectionsCache);

            const totalLabel = document.getElementById("detections-total-label");
            if (totalLabel) totalLabel.textContent = `Showing ${currentDetectionsCache.length} detections`;

            // Update Map with current detections
            MapModule.renderDetections(currentDetectionsCache, currentClustersCache);
        } catch (err) {
            console.error("Error fetching detections:", err);
        }
    }

    function renderMasterTable(detections) {
        const tbody = document.getElementById("detections-table-tbody");
        if (!tbody) return;

        if (detections.length === 0) {
            tbody.innerHTML = `<tr><td colspan="12" class="text-center text-muted">No detection records match filter criteria.</td></tr>`;
            return;
        }

        tbody.innerHTML = detections.map(d => {
            const timeStr = new Date(d.timestamp).toLocaleTimeString();
            const clusterBadge = d.cluster_id >= 0 
                ? `<span class="badge-pill" style="background:#5b21b6; color:#ddd6fe;">#${d.cluster_id}</span>` 
                : `<span class="text-muted text-xs">Noise</span>`;

            return `
                <tr>
                    <td class="font-mono">#${d.id}</td>
                    <td>
                        <span class="badge-tag">${escapeHtml(d.device_id)}</span>
                        ${d.is_simulated ? '<span title="Simulated" style="font-size:10px;">🤖</span>' : '<span title="Live Hardware" style="font-size:10px;">📱</span>'}
                    </td>
                    <td class="text-xs text-muted font-mono">${timeStr}</td>
                    <td class="text-xs font-mono">${d.latitude.toFixed(4)}, ${d.longitude.toFixed(4)}</td>
                    <td class="font-mono text-xs">${d.peak_accel.toFixed(1)} m/s²</td>
                    <td><span class="badge-pill pill-${d.event_type.toLowerCase().replace(/\s+/g, '')}">${d.event_type}</span></td>
                    <td>${Math.round(d.confidence * 100)}%</td>
                    <td><strong>${d.pdi_score}</strong></td>
                    <td><span class="badge-pill pill-${d.priority_level.toLowerCase()}">${d.priority_level}</span></td>
                    <td>${clusterBadge}</td>
                    <td id="integrity-cell-${d.id}"><span class="badge-tag tag-success" style="color:#34d399;">✔ Signed</span></td>
                    <td>
                        <div class="action-btn-row">
                            <button class="btn btn-xs btn-outline" onclick="DashboardModule.openInspectModal(${d.id})" title="Inspect full record & decrypted fields">
                                🔍 Inspect
                            </button>
                            <button class="btn btn-xs btn-success" onclick="DashboardModule.verifySingleRecord(${d.id})" title="Verify SHA-256 and RSA Signature">
                                ✔ Verify
                            </button>
                            <button class="btn btn-xs btn-danger-outline" onclick="DashboardModule.deleteRecord(${d.id})" title="Delete record">
                                🗑️
                            </button>
                        </div>
                    </td>
                </tr>
            `;
        }).join("");
    }

    // -------------------------------------------------------------------------
    // 4. Modal Record Inspection
    // -------------------------------------------------------------------------
    async function openInspectModal(id) {
        activeInspectedId = id;
        const modal = document.getElementById("modal-inspect");
        const modalBody = document.getElementById("modal-inspect-body");
        if (!modal || !modalBody) return;

        modal.classList.remove("hidden");
        modalBody.innerHTML = `<p class="text-center text-muted">Retrieving decrypted details and signature proof for Record #${id}...</p>`;

        try {
            const res = await fetch(`/api/detections/${id}`);
            const json = await res.json();
            if (!json.success) {
                modalBody.innerHTML = `<p class="text-danger">Failed to load details: ${json.error}</p>`;
                return;
            }

            const rec = json.data;
            const v = rec.verification;

            modalBody.innerHTML = `
                <div style="display:flex; flex-direction:column; gap:14px;">
                    <div style="display:flex; justify-content:space-between; align-items:center; background:rgba(0,0,0,0.25); padding:10px; border-radius:6px;">
                        <div>
                            <strong style="font-size:16px;">Record #${rec.id} — ${rec.event_type}</strong>
                            <div class="text-muted text-xs">Reported by ${escapeHtml(rec.device_id)} at ${rec.timestamp}</div>
                        </div>
                        <span class="badge-pill pill-${rec.priority_level.toLowerCase()}">${rec.priority_level} (PDI: ${rec.pdi_score})</span>
                    </div>

                    <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px;">
                        <div class="sensor-metric-box">
                            <div class="metric-label">Model Confidence</div>
                            <div class="metric-val text-info">${Math.round(rec.confidence * 100)}%</div>
                        </div>
                        <div class="sensor-metric-box">
                            <div class="metric-label">Peak Shock Accel</div>
                            <div class="metric-val text-warning">${rec.peak_accel} m/s²</div>
                        </div>
                    </div>

                    <!-- Cryptographic & Privacy Verification Section -->
                    <div class="crypto-concept-block">
                        <div class="concept-title font-bold">🔐 Cryptographic Integrity & Privacy Seal</div>
                        <div class="mt-2 text-xs font-mono" style="line-height:1.7;">
                            <div><strong>SHA-256 Record Hash:</strong> <span style="color:#38bdf8;">${rec.data_hash}</span></div>
                            <div style="margin-top:4px;"><strong>Hash Verification:</strong> ${v.is_hash_valid ? '<span style="color:#34d399;">✔ VALID (Canonical Data Matches Digest)</span>' : '<span style="color:#f87171;">❌ FAILED (Integrity Tampered)</span>'}</div>
                            <div style="margin-top:4px;"><strong>RSA-2048 Digital Signature:</strong> <span style="color:#a78bfa;">${rec.digital_signature.slice(0, 48)}...</span></div>
                            <div style="margin-top:4px;"><strong>Signature Verification:</strong> ${v.is_signature_valid ? '<span style="color:#34d399;">✔ AUTHENTIC (Signed by Municipal Private Key)</span>' : '<span style="color:#f87171;">❌ INVALID SIGNATURE</span>'}</div>
                        </div>
                    </div>

                    <!-- Sensitive Fields Decrypted -->
                    <div style="background:rgba(0,0,0,0.3); border:1px solid #334155; padding:12px; border-radius:6px;">
                        <div class="font-bold text-xs" style="color:#94a3b8; text-transform:uppercase;">Fernet Symmetric Decryption (Authorized Inspector View)</div>
                        <div class="mt-2 text-xs font-mono" style="display:flex; flex-direction:column; gap:4px;">
                            <div><strong>Encrypted Lat Ciphertext:</strong> <span class="text-truncate">${rec.encrypted_latitude.slice(0, 28)}...</span></div>
                            <div><strong>Decrypted Latitude:</strong> <span style="color:#34d399;">${v.decrypted_latitude}</span></div>
                            <div><strong>Decrypted Longitude:</strong> <span style="color:#34d399;">${v.decrypted_longitude}</span></div>
                        </div>
                    </div>

                    <!-- Canonical Payload -->
                    <div>
                        <div class="font-bold text-xs text-muted">Canonical Deterministic String (Pre-image for Hash & Signature):</div>
                        <pre style="background:#000; padding:8px; border-radius:4px; font-size:11px; color:#38bdf8; overflow-x:auto;">${escapeHtml(v.canonical_string)}</pre>
                    </div>
                </div>
            `;
        } catch (err) {
            modalBody.innerHTML = `<p class="text-danger">Error: ${err.message}</p>`;
        }
    }

    function setupModalControls() {
        const btnClose = document.getElementById("btn-close-modal");
        const btnDismiss = document.getElementById("btn-modal-dismiss");
        const modal = document.getElementById("modal-inspect");
        const btnVerify = document.getElementById("btn-modal-verify");
        const btnTamper = document.getElementById("btn-modal-tamper");

        const closeModal = () => {
            if (modal) modal.classList.add("hidden");
            activeInspectedId = null;
        };

        if (btnClose) btnClose.addEventListener("click", closeModal);
        if (btnDismiss) btnDismiss.addEventListener("click", closeModal);

        if (btnVerify) {
            btnVerify.addEventListener("click", async () => {
                if (!activeInspectedId) return;
                await verifySingleRecord(activeInspectedId);
                openInspectModal(activeInspectedId);
            });
        }

        if (btnTamper) {
            btnTamper.addEventListener("click", async () => {
                if (!activeInspectedId) return;
                await tamperSingleRecord(activeInspectedId);
                openInspectModal(activeInspectedId);
            });
        }
    }

    // -------------------------------------------------------------------------
    // 5. Verification & Tamper Demonstrations
    // -------------------------------------------------------------------------
    async function verifySingleRecord(id) {
        try {
            const res = await fetch(`/api/detections/${id}/verify`, { method: "POST" });
            const data = await res.json();
            const cell = document.getElementById(`integrity-cell-${id}`);

            if (data.is_hash_valid && data.is_signature_valid) {
                if (cell) cell.innerHTML = `<span class="badge-tag tag-success" style="color:#34d399;">✔ VERIFIED</span>`;
                AppModule.showAlert(`Record #${id}: SHA-256 Hash intact and RSA signature verified authentic!`, "success");
            } else {
                if (cell) cell.innerHTML = `<span class="badge-tag tag-danger" style="background:#ef4444; color:#fff;">❌ COMPROMISED</span>`;
                AppModule.showAlert(`Record #${id}: TAMPER DETECTED! Stored hash does not match canonical payload, RSA signature failed.`, "danger");
            }
            return data;
        } catch (err) {
            AppModule.showAlert(`Verification error: ${err.message}`, "danger");
        }
    }

    async function tamperSingleRecord(id) {
        try {
            const res = await fetch(`/api/detections/${id}/tamper`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ field: "pdi_score", value: 99.9 })
            });
            const data = await res.json();
            if (data.success) {
                AppModule.showAlert(`Record #${id} pdi_score altered to 99.9 directly in SQLite. Cryptographic hash is now mismatched!`, "warning");
                const cell = document.getElementById(`integrity-cell-${id}`);
                if (cell) cell.innerHTML = `<span class="badge-tag tag-warning" style="color:#fbbf24;">⚠️ Tampered</span>`;
            }
        } catch (err) {
            AppModule.showAlert(`Tamper error: ${err.message}`, "danger");
        }
    }

    async function deleteRecord(id) {
        if (!confirm(`Are you sure you want to delete detection record #${id}?`)) return;
        try {
            const res = await fetch(`/api/detections/${id}`, { method: "DELETE" });
            const data = await res.json();
            if (data.success) {
                AppModule.showAlert(`Record #${id} deleted.`, "info");
                refreshAll();
            }
        } catch (err) {
            AppModule.showAlert(`Delete failed: ${err.message}`, "danger");
        }
    }

    function populateTamperDropdown(detections) {
        const select = document.getElementById("tamper-target-id");
        if (!select) return;

        const prevVal = select.value;
        select.innerHTML = `<option value="">-- Select Record to Inspect/Tamper --</option>` +
            detections.map(d => `<option value="${d.id}">Record #${d.id} — ${d.event_type} (PDI: ${d.pdi_score})</option>`).join("");

        if (prevVal && select.querySelector(`option[value="${prevVal}"]`)) {
            select.value = prevVal;
        }

        const btnVerify = document.getElementById("btn-lab-verify");
        const btnTamper = document.getElementById("btn-lab-tamper");

        select.onchange = () => {
            const hasVal = !!select.value;
            if (btnVerify) btnVerify.disabled = !hasVal;
            if (btnTamper) btnTamper.disabled = !hasVal;
        };
    }

    // -------------------------------------------------------------------------
    // 6. Controls, Exports & Utilities
    // -------------------------------------------------------------------------
    function setupToolbarFilters() {
        const searchInput = document.getElementById("filter-search-input");
        const eventType = document.getElementById("filter-event-type");
        const priority = document.getElementById("filter-priority");
        const simSelect = document.getElementById("filter-simulated");

        const triggerFilter = () => fetchAndRenderDetections();

        if (searchInput) searchInput.addEventListener("input", debounce(triggerFilter, 300));
        if (eventType) eventType.addEventListener("change", triggerFilter);
        if (priority) priority.addEventListener("change", triggerFilter);
        if (simSelect) simSelect.addEventListener("change", triggerFilter);

        const btnRecluster = document.getElementById("btn-recluster-now");
        const btnReclusterOverview = document.getElementById("btn-run-dbscan-overview");

        const runRecluster = async () => {
            try {
                AppModule.showLoadingState(true);
                const res = await fetch("/api/detections/recluster", { method: "POST" });
                const json = await res.json();
                AppModule.showLoadingState(false);
                if (json.success) {
                    AppModule.showAlert(`DBSCAN recalculated: Grouped into ${json.cluster_count} spatial clusters.`, "success");
                    refreshAll();
                }
            } catch (err) {
                AppModule.showLoadingState(false);
                AppModule.showAlert("Recluster failed: " + err.message, "danger");
            }
        };

        if (btnRecluster) btnRecluster.addEventListener("click", runRecluster);
        if (btnReclusterOverview) btnReclusterOverview.addEventListener("click", runRecluster);

        const btnDelSim = document.getElementById("btn-delete-simulated");
        if (btnDelSim) {
            btnDelSim.addEventListener("click", async () => {
                if (!confirm("Delete all simulated demonstration records?")) return;
                try {
                    const res = await fetch("/api/detections/simulated", { method: "DELETE" });
                    const json = await res.json();
                    AppModule.showAlert(json.message, "info");
                    refreshAll();
                } catch (err) {
                    AppModule.showAlert("Delete error: " + err.message, "danger");
                }
            });
        }
    }

    function setupExportAndUtilityButtons() {
        const btnCsv1 = document.getElementById("btn-export-csv");
        const btnCsv2 = document.getElementById("btn-download-csv-footer");

        const triggerCsv = () => {
            window.location.href = "/api/export/csv";
            AppModule.showAlert("Exporting detections to CSV file...", "info");
        };

        if (btnCsv1) btnCsv1.addEventListener("click", triggerCsv);
        if (btnCsv2) btnCsv2.addEventListener("click", triggerCsv);
    }

    function refreshMapWithFilters(type, priority) {
        let filtered = [...currentDetectionsCache];
        if (type && type !== "All") {
            filtered = filtered.filter(d => d.event_type === type);
        }
        if (priority && priority !== "All") {
            filtered = filtered.filter(d => d.priority_level === priority);
        }
        MapModule.renderDetections(filtered, currentClustersCache);
        AppModule.showAlert(`Map filtered: ${filtered.length} matching detections shown.`, "info");
    }

    function getPriorityCssClass(p) {
        switch (p) {
            case "Critical": return "danger";
            case "High": return "warning";
            case "Moderate": return "warning";
            default: return "success";
        }
    }

    function escapeHtml(str) {
        if (!str) return "";
        return String(str)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    function debounce(fn, ms) {
        let timer;
        return (...args) => {
            clearTimeout(timer);
            timer = setTimeout(() => fn(...args), ms);
        };
    }

    return {
        init,
        refreshAll,
        openInspectModal,
        verifySingleRecord,
        tamperSingleRecord,
        deleteRecord,
        refreshMapWithFilters
    };
})();
