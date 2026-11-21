/**
 * app.js — Main Application Controller
 * Handles tab routing, toast notifications, cryptographic lab execution,
 * demo data seeding, and ML model parameter inspection.
 */

const AppModule = (() => {

    function init() {
        setupNavigationTabs();
        setupGlobalButtons();
        setupCryptoLab();
        loadMLModelInfo();

        // Initialize submodules
        MapModule.init();
        SensorModule.init();
        DashboardModule.init();
    }

    // -------------------------------------------------------------------------
    // 1. Navigation & Tab Switching
    // -------------------------------------------------------------------------
    function setupNavigationTabs() {
        const navButtons = document.querySelectorAll(".nav-item");
        const titleEl = document.getElementById("current-section-title");

        const titles = {
            "tab-overview": "Municipal Road Quality Dashboard",
            "tab-map": "Interactive Geospatial GIS Heatmap & DBSCAN Clusters",
            "tab-sensors": "Crowdsourced Sensor Telemetry Ingestion (Live & Simulation)",
            "tab-detections": "Verified Road Quality Detections & Cryptographic Log",
            "tab-security": "Cryptographic Integrity, Privacy & Non-Repudiation Center",
            "tab-viva": "Project Architecture & Examiner Viva Defense Guide"
        };

        navButtons.forEach(btn => {
            btn.addEventListener("click", () => {
                const targetTabId = btn.getAttribute("data-tab");
                if (!targetTabId) return;

                // Update nav button active states
                navButtons.forEach(b => b.classList.remove("active"));
                btn.classList.add("active");

                // Update tab panes
                document.querySelectorAll(".tab-pane").forEach(pane => {
                    pane.classList.remove("active");
                });
                const targetPane = document.getElementById(targetTabId);
                if (targetPane) targetPane.classList.add("active");

                // Update header title
                if (titleEl && titles[targetTabId]) {
                    titleEl.textContent = titles[targetTabId];
                }

                // If map is involved, recalculate leaflet dimensions
                if (targetTabId === "tab-overview" || targetTabId === "tab-map") {
                    MapModule.invalidateSize();
                }
            });
        });

        // Quick jump buttons
        const btnViewAll = document.getElementById("btn-view-all-detections");
        if (btnViewAll) {
            btnViewAll.addEventListener("click", () => {
                const navDet = document.querySelector('[data-tab="tab-detections"]');
                if (navDet) navDet.click();
            });
        }
    }

    // -------------------------------------------------------------------------
    // 2. Global Actions (Seed, Reset, Refresh)
    // -------------------------------------------------------------------------
    function setupGlobalButtons() {
        const btnSeed = document.getElementById("btn-quick-seed");
        const btnReset = document.getElementById("btn-reset-db");
        const btnRefresh = document.getElementById("btn-refresh-all");

        if (btnSeed) {
            btnSeed.addEventListener("click", async () => {
                showLoadingState(true);
                try {
                    const res = await fetch("/api/demo/seed", { method: "POST" });
                    const data = await res.json();
                    showLoadingState(false);
                    if (data.success) {
                        showAlert(data.message, "success");
                        DashboardModule.refreshAll();
                    } else {
                        showAlert("Seed failed: " + data.error, "danger");
                    }
                } catch (err) {
                    showLoadingState(false);
                    showAlert("Seed error: " + err.message, "danger");
                }
            });
        }

        if (btnReset) {
            btnReset.addEventListener("click", async () => {
                if (!confirm("Are you sure you want to completely wipe all detection records?")) return;
                showLoadingState(true);
                try {
                    const res = await fetch("/api/detections/reset", { method: "POST" });
                    const data = await res.json();
                    showLoadingState(false);
                    showAlert(data.message, "info");
                    DashboardModule.refreshAll();
                } catch (err) {
                    showLoadingState(false);
                    showAlert("Reset error: " + err.message, "danger");
                }
            });
        }

        if (btnRefresh) {
            btnRefresh.addEventListener("click", () => {
                DashboardModule.refreshAll();
                showAlert("Dashboard telemetry refreshed.", "info");
            });
        }
    }

    // -------------------------------------------------------------------------
    // 3. Interactive Cryptographic Lab (Tab 5)
    // -------------------------------------------------------------------------
    function setupCryptoLab() {
        const btnVerify = document.getElementById("btn-lab-verify");
        const btnTamper = document.getElementById("btn-lab-tamper");
        const select = document.getElementById("tamper-target-id");
        const logBox = document.getElementById("tamper-console-log");

        if (btnVerify) {
            btnVerify.addEventListener("click", async () => {
                const id = select.value;
                if (!id) return;
                logBox.textContent = `[INITIATING INTEGRITY CHECK FOR RECORD #${id}]...\n`;
                
                try {
                    const res = await fetch(`/api/detections/${id}/verify`, { method: "POST" });
                    const data = await res.json();

                    let log = `\n>>> RECORD #${id} INTEGRITY AUDIT RESULTS <<<\n`;
                    log += `Stored SHA-256 Hash:   ${data.stored_hash}\n`;
                    log += `Recomputed SHA-256:    ${data.current_computed_hash}\n\n`;

                    if (data.is_hash_valid) {
                        log += `[PASS] SHA-256 Hash Match: TRUE (No unauthorized database modification)\n`;
                    } else {
                        log += `[FAIL] SHA-256 Hash Match: FALSE (Database record values were tampered!)\n`;
                    }

                    if (data.is_signature_valid) {
                        log += `[PASS] RSA-2048 Digital Signature: VALID (Record authentic and unaltered)\n`;
                    } else {
                        log += `[FAIL] RSA-2048 Digital Signature: INVALID (Server signature rejected!)\n`;
                    }

                    log += `\nOVERALL RECORD INTEGRITY: ${data.status}`;
                    logBox.textContent = log;

                    if (data.is_hash_valid && data.is_signature_valid) {
                        showAlert(`Record #${id} verified cryptographically authentic!`, "success");
                    } else {
                        showAlert(`Record #${id} verification FAILED: Tampering detected!`, "danger");
                    }
                } catch (err) {
                    logBox.textContent = `Error: ${err.message}`;
                }
            });
        }

        if (btnTamper) {
            btnTamper.addEventListener("click", async () => {
                const id = select.value;
                if (!id) return;

                try {
                    const res = await fetch(`/api/detections/${id}/tamper`, {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ field: "pdi_score", value: 99.9 })
                    });
                    const data = await res.json();

                    let log = `[ALERT] DELIBERATE TAMPER SIMULATION EXECUTED\n`;
                    log += `Target: Record #${id}\n`;
                    log += `Modified: pdi_score set to 99.9 directly via SQLite UPDATE\n`;
                    log += `Notice: The stored SHA-256 hash and RSA signature were NOT updated.\n\n`;
                    log += `NOW: Click "Verify Current Integrity" above to demonstrate cryptographic tamper detection to your examiner!`;

                    logBox.textContent = log;
                    showAlert(`Record #${id} intentionally tampered! Click "Verify Current Integrity" to observe signature failure.`, "warning");
                    DashboardModule.refreshAll();
                } catch (err) {
                    logBox.textContent = `Error: ${err.message}`;
                }
            });
        }
    }

    // -------------------------------------------------------------------------
    // 4. ML Model Parameter Loader (Tab 6)
    // -------------------------------------------------------------------------
    async function loadMLModelInfo() {
        const container = document.getElementById("ml-metadata-container");
        if (!container) return;

        try {
            const res = await fetch("/api/ml/info");
            const data = await res.json();
            if (!data.success) {
                container.innerHTML = `<p class="text-muted">Model training metadata not found.</p>`;
                return;
            }

            const m = data.metadata;
            container.innerHTML = `
                <div style="display:flex; flex-direction:column; gap:12px; font-size:12px;">
                    <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(180px, 1fr)); gap:10px;">
                        <div><strong>Algorithm:</strong> ${m.model_type} (${m.n_estimators} trees)</div>
                        <div><strong>Test Accuracy:</strong> <span class="text-success font-bold">${(m.metrics.test_accuracy * 100).toFixed(2)}%</span></div>
                        <div><strong>Macro Precision:</strong> ${(m.metrics.test_precision_macro * 100).toFixed(2)}%</div>
                        <div><strong>Macro Recall:</strong> ${(m.metrics.test_recall_macro * 100).toFixed(2)}%</div>
                    </div>
                    <div>
                        <strong>Physical Features:</strong> <code>${m.features.join(", ")}</code>
                    </div>
                    <div>
                        <strong>Feature Importances:</strong>
                        <div class="mt-2" style="display:flex; flex-wrap:wrap; gap:6px;">
                            ${Object.entries(m.feature_importances || {}).map(([f, imp]) => `
                                <span class="badge-tag">${f}: <strong>${(imp * 100).toFixed(1)}%</strong></span>
                            `).join("")}
                        </div>
                    </div>
                    <div class="text-muted text-xs" style="margin-top:6px; border-top:1px solid #334155; padding-top:6px;">
                        <em>Disclaimer:</em> ${m.disclaimer}
                    </div>
                </div>
            `;
        } catch (err) {
            console.error("Error loading ML info:", err);
        }
    }

    // -------------------------------------------------------------------------
    // 5. Toast Notifications & Loading State
    // -------------------------------------------------------------------------
    function showAlert(message, type = "info") {
        const container = document.getElementById("alert-container");
        if (!container) return;

        const alert = document.createElement("div");
        alert.className = `alert alert-${type}`;
        alert.innerHTML = `
            <span>${escapeHtml(message)}</span>
            <button style="background:transparent; border:none; color:inherit; font-weight:bold; cursor:pointer;" onclick="this.parentElement.remove()">&times;</button>
        `;
        container.appendChild(alert);

        setTimeout(() => {
            if (alert.parentElement) {
                alert.style.opacity = "0";
                setTimeout(() => alert.remove(), 250);
            }
        }, 5000);
    }

    function showLoadingState(isLoading) {
        document.body.style.cursor = isLoading ? "wait" : "default";
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

    return {
        init,
        showAlert,
        showLoadingState
    };
})();

// Bootstrap on DOM Ready
document.addEventListener("DOMContentLoaded", () => {
    AppModule.init();
});
