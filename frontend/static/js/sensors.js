/**
 * sensors.js — Sensor Data Collection & Demonstration Engine
 * Handles:
 * - Mode A: Live Hardware Smartphone Sensor Ingestion (DeviceMotion, Geolocation)
 * - Mode B: Realistic Multi-Vehicle Demonstration Simulation
 */

const SensorModule = (() => {
    let isLiveActive = false;
    let motionWatchId = null;
    let geoWatchId = null;

    let currentLat = 12.9716;
    let currentLon = 77.5946;
    let currentAccel = { x: 0.0, y: 0.0, z: 9.81, mag: 9.81 };
    let currentGyro = 0.0;

    let recentReadingsBuffer = [];
    let autoSampleInterval = null;

    function init() {
        setupModeBControls();
        setupModeAControls();
    }

    // -------------------------------------------------------------------------
    // MODE B: Demonstration Mode Controls
    // -------------------------------------------------------------------------
    function setupModeBControls() {
        const peakSlider = document.getElementById("sim-peak-slider");
        const peakValLabel = document.getElementById("sim-peak-val");
        const gyroSlider = document.getElementById("sim-gyro-slider");
        const gyroValLabel = document.getElementById("sim-gyro-val");
        const locPreset = document.getElementById("sim-location-preset");
        const latInput = document.getElementById("sim-lat");
        const lonInput = document.getElementById("sim-lon");

        if (peakSlider && peakValLabel) {
            peakSlider.addEventListener("input", (e) => {
                peakValLabel.textContent = `${parseFloat(e.target.value).toFixed(1)} m/s²`;
            });
        }

        if (gyroSlider && gyroValLabel) {
            gyroSlider.addEventListener("input", (e) => {
                gyroValLabel.textContent = `${parseFloat(e.target.value).toFixed(1)} rad/s`;
            });
        }

        if (locPreset) {
            locPreset.addEventListener("change", (e) => {
                if (e.target.value !== "custom") {
                    const [lat, lon] = e.target.value.split(",");
                    if (latInput) latInput.value = parseFloat(lat).toFixed(6);
                    if (lonInput) lonInput.value = parseFloat(lon).toFixed(6);
                }
            });
        }

        // Preset 1-Click Buttons
        const btnPothole = document.getElementById("btn-preset-pothole");
        const btnSpeedBreaker = document.getElementById("btn-preset-speedbreaker");
        const btnNormal = document.getElementById("btn-preset-normal");

        if (btnPothole) {
            btnPothole.addEventListener("click", () => {
                setPresetValues(22.5, 2.4, "DEV-CAB-101", "12.927900", "77.683500");
                AppModule.showAlert("Configured high-impact Pothole shock profile (Peak: 22.5 m/s²)", "info");
            });
        }

        if (btnSpeedBreaker) {
            btnSpeedBreaker.addEventListener("click", () => {
                setPresetValues(14.0, 1.2, "DEV-BUS-201", "12.978400", "77.640800");
                AppModule.showAlert("Configured Speed Breaker undulating profile (Peak: 14.0 m/s²)", "info");
            });
        }

        if (btnNormal) {
            btnNormal.addEventListener("click", () => {
                setPresetValues(10.1, 0.05, "DEV-CAR-309", "12.976600", "77.599300");
                AppModule.showAlert("Configured smooth Normal Road asphalt baseline (Peak: 10.1 m/s²)", "info");
            });
        }

        // Form Submit
        const formSim = document.getElementById("form-simulate-event");
        if (formSim) {
            formSim.addEventListener("submit", async (e) => {
                e.preventDefault();
                await submitSimulatedEvent();
            });
        }
    }

    function setPresetValues(peak, gyro, device, lat, lon) {
        const peakSlider = document.getElementById("sim-peak-slider");
        const peakValLabel = document.getElementById("sim-peak-val");
        const gyroSlider = document.getElementById("sim-gyro-slider");
        const gyroValLabel = document.getElementById("sim-gyro-val");
        const devInput = document.getElementById("sim-device-id");
        const latInput = document.getElementById("sim-lat");
        const lonInput = document.getElementById("sim-lon");

        if (peakSlider) { peakSlider.value = peak; }
        if (peakValLabel) { peakValLabel.textContent = `${peak.toFixed(1)} m/s²`; }
        if (gyroSlider) { gyroSlider.value = gyro; }
        if (gyroValLabel) { gyroValLabel.textContent = `${gyro.toFixed(1)} rad/s`; }
        if (devInput) { devInput.value = device; }
        if (latInput) { latInput.value = lat; }
        if (lonInput) { lonInput.value = lon; }
    }

    async function submitSimulatedEvent() {
        const deviceId = document.getElementById("sim-device-id").value.trim() || "DEV-SIM-001";
        const lat = parseFloat(document.getElementById("sim-lat").value);
        const lon = parseFloat(document.getElementById("sim-lon").value);
        const peak = parseFloat(document.getElementById("sim-peak-slider").value);
        const gyro = parseFloat(document.getElementById("sim-gyro-slider").value);

        // Approximate variance based on peak
        const variance = Math.max(0.1, (peak - 9.8) * 1.8);

        const payload = {
            device_id: deviceId,
            timestamp: new Date().toISOString(),
            latitude: lat,
            longitude: lon,
            accel_x: parseFloat((Math.random() * 0.6 - 0.3).toFixed(2)),
            accel_y: parseFloat((Math.random() * 0.6 - 0.3).toFixed(2)),
            accel_z: parseFloat(peak.toFixed(2)),
            peak_accel: peak,
            accel_variance: parseFloat(variance.toFixed(2)),
            gyro_mag: gyro,
            is_simulated: true
        };

        try {
            AppModule.showLoadingState(true);
            const res = await fetch("/api/detections", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });

            const data = await res.json();
            AppModule.showLoadingState(false);

            if (data.success) {
                renderSimulationResult(data);
                AppModule.showAlert(`Event classified as "${data.event_type}" with ${Math.round(data.confidence * 100)}% confidence! Cryptographically signed and sealed.`, "success");
                DashboardModule.refreshAll();
            } else {
                AppModule.showAlert(`Simulation failed: ${data.error}`, "danger");
            }
        } catch (err) {
            AppModule.showLoadingState(false);
            AppModule.showAlert(`Network error: ${err.message}`, "danger");
        }
    }

    function renderSimulationResult(data) {
        const card = document.getElementById("sim-result-card");
        if (!card) return;

        card.classList.remove("hidden");
        document.getElementById("result-badge-type").textContent = data.event_type;
        document.getElementById("result-event-type").textContent = data.event_type;
        document.getElementById("result-confidence").textContent = `${Math.round(data.confidence * 100)}%`;
        document.getElementById("result-pdi").textContent = `${data.pdi_score} / 100`;

        const priorityEl = document.getElementById("result-priority");
        priorityEl.textContent = data.priority_level;
        priorityEl.className = `badge-pill pill-${data.priority_level.toLowerCase()}`;

        document.getElementById("result-hash").textContent = data.cryptography.data_hash || "-";
        document.getElementById("result-sig").textContent = data.cryptography.digital_signature_preview || "-";
        document.getElementById("result-enc-lat").textContent = data.cryptography.encrypted_latitude_preview || "-";
    }

    // -------------------------------------------------------------------------
    // MODE A: Live Hardware Sensor Handling
    // -------------------------------------------------------------------------
    function setupModeAControls() {
        const btnStart = document.getElementById("btn-start-live-sensors");
        const btnStop = document.getElementById("btn-stop-live-sensors");
        const btnInstant = document.getElementById("btn-trigger-instant-sample");

        if (btnStart) {
            btnStart.addEventListener("click", startLiveSensors);
        }
        if (btnStop) {
            btnStop.addEventListener("click", stopLiveSensors);
        }
        if (btnInstant) {
            btnInstant.addEventListener("click", () => transmitLiveReading(true));
        }
    }

    function startLiveSensors() {
        if (!window.DeviceMotionEvent && !navigator.geolocation) {
            AppModule.showAlert("Your web browser does not support DeviceMotion or Geolocation. Use Demonstration Mode.", "danger");
            return;
        }

        isLiveActive = true;
        document.getElementById("btn-start-live-sensors").disabled = true;
        document.getElementById("btn-stop-live-sensors").disabled = false;
        document.getElementById("btn-trigger-instant-sample").disabled = false;

        const statusBadge = document.getElementById("live-sensor-status-badge");
        statusBadge.textContent = "Telemetry Ingesting...";
        statusBadge.className = "badge-tag tag-success";

        // Request Geolocation
        if (navigator.geolocation) {
            geoWatchId = navigator.geolocation.watchPosition(
                (pos) => {
                    currentLat = pos.coords.latitude;
                    currentLon = pos.coords.longitude;
                    const gpsEl = document.getElementById("live-gps");
                    if (gpsEl) gpsEl.textContent = `${currentLat.toFixed(4)}, ${currentLon.toFixed(4)}`;
                },
                (err) => {
                    console.warn("GPS Warning:", err.message);
                },
                { enableHighAccuracy: true, maximumAge: 2000 }
            );
        }

        // Request Device Motion
        if (window.DeviceMotionEvent) {
            // iOS 13+ requires permission request
            if (typeof DeviceMotionEvent.requestPermission === "function") {
                DeviceMotionEvent.requestPermission()
                    .then(permissionState => {
                        if (permissionState === "granted") {
                            window.addEventListener("devicemotion", handleDeviceMotion);
                        } else {
                            AppModule.showAlert("Motion sensor access denied by user.", "warning");
                        }
                    })
                    .catch(err => console.error(err));
            } else {
                window.addEventListener("devicemotion", handleDeviceMotion);
            }
        }

        // Auto-sample every 4 seconds or on significant shock
        autoSampleInterval = setInterval(() => {
            if (isLiveActive) {
                transmitLiveReading(false);
            }
        }, 4000);

        AppModule.showAlert("Live smartphone sensor collection active.", "success");
    }

    function handleDeviceMotion(event) {
        const accel = event.accelerationIncludingGravity || event.acceleration || {};
        const x = accel.x || 0;
        const y = accel.y || 0;
        const z = accel.z || 9.81;
        const mag = Math.sqrt(x*x + y*y + z*z);

        const rot = event.rotationRate || {};
        const gx = rot.alpha || 0;
        const gy = rot.beta || 0;
        const gz = rot.gamma || 0;
        const gyroMag = Math.sqrt(gx*gx + gy*gy + gz*gz);

        currentAccel = { x, y, z, mag };
        currentGyro = gyroMag;

        // Update UI
        document.getElementById("live-accel-x").textContent = `${x.toFixed(2)} m/s²`;
        document.getElementById("live-accel-y").textContent = `${y.toFixed(2)} m/s²`;
        document.getElementById("live-accel-z").textContent = `${z.toFixed(2)} m/s²`;
        document.getElementById("live-accel-mag").textContent = `${mag.toFixed(2)} m/s²`;
        document.getElementById("live-gyro").textContent = `${gyroMag.toFixed(2)} rad/s`;

        // Store sample in sliding buffer
        recentReadingsBuffer.push({ x, y, z, gx, gy, gz });
        if (recentReadingsBuffer.length > 50) {
            recentReadingsBuffer.shift();
        }

        // Trigger immediate transmission if sharp shock detected (|mag - 9.8| > 6.0)
        if (Math.abs(mag - 9.81) > 6.0) {
            transmitLiveReading(true);
        }
    }

    function stopLiveSensors() {
        isLiveActive = false;
        if (geoWatchId !== null) navigator.geolocation.clearWatch(geoWatchId);
        window.removeEventListener("devicemotion", handleDeviceMotion);
        if (autoSampleInterval) clearInterval(autoSampleInterval);

        document.getElementById("btn-start-live-sensors").disabled = false;
        document.getElementById("btn-stop-live-sensors").disabled = true;
        document.getElementById("btn-trigger-instant-sample").disabled = true;

        const statusBadge = document.getElementById("live-sensor-status-badge");
        statusBadge.textContent = "Sensors Inactive";
        statusBadge.className = "badge-tag tag-neutral";

        AppModule.showAlert("Live sensor stream stopped.", "info");
    }

    async function transmitLiveReading(isShock = false) {
        const payload = {
            device_id: "PHONE-LIVE-HW",
            timestamp: new Date().toISOString(),
            latitude: currentLat,
            longitude: currentLon,
            accel_x: currentAccel.x,
            accel_y: currentAccel.y,
            accel_z: currentAccel.z,
            peak_accel: currentAccel.mag,
            accel_variance: Math.abs(currentAccel.mag - 9.81) * 0.5,
            gyro_mag: currentGyro,
            is_simulated: false,
            readings: recentReadingsBuffer.slice(-15)
        };

        try {
            const res = await fetch("/api/detections", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });
            const data = await res.json();
            if (data.success && isShock) {
                AppModule.showAlert(`Live Shock Captured: Classified as "${data.event_type}" (PDI: ${data.pdi_score})`, "warning");
                DashboardModule.refreshAll();
            }
        } catch (err) {
            console.error("Live ingest error:", err);
        }
    }

    return {
        init,
        setPresetValues
    };
})();
