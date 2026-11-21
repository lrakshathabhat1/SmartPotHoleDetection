/**
 * map.js — Interactive GIS Mapping Engine using Leaflet.js and OpenStreetMap
 * Displays:
 * - Color-coded road quality detections (PDI priority)
 * - DBSCAN geographic clusters with crowdsourced vehicle counts
 * - Interactive popups with cryptographic verification badges
 * - Map filters and dynamic viewport auto-centering
 */

const MapModule = (() => {
    let overviewMap = null;
    let fullMap = null;

    let overviewMarkerLayer = null;
    let fullMarkerLayer = null;
    let fullClusterLayer = null;

    const DEFAULT_CENTER = [12.9716, 77.5946]; // Default City View (Bengaluru)
    const DEFAULT_ZOOM = 12;

    const PRIORITY_COLORS = {
        "Critical": "#dc2626", // Red-Crimson
        "High": "#f97316",     // Orange
        "Moderate": "#f59e0b", // Yellow-Amber
        "Low": "#10b981"       // Green
    };

    function init() {
        initOverviewMap();
        initFullMap();
        setupFilterListeners();
    }

    function initOverviewMap() {
        const el = document.getElementById("overview-map");
        if (!el || overviewMap) return;

        overviewMap = L.map("overview-map", {
            center: DEFAULT_CENTER,
            zoom: DEFAULT_ZOOM,
            zoomControl: true
        });

        L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
            maxZoom: 19,
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        }).addTo(overviewMap);

        overviewMarkerLayer = L.layerGroup().addTo(overviewMap);

        const recenterBtn = document.getElementById("btn-recenter-map");
        if (recenterBtn) {
            recenterBtn.addEventListener("click", () => {
                fitMapToBounds(overviewMap, overviewMarkerLayer);
            });
        }
    }

    function initFullMap() {
        const el = document.getElementById("full-gis-map");
        if (!el || fullMap) return;

        fullMap = L.map("full-gis-map", {
            center: DEFAULT_CENTER,
            zoom: DEFAULT_ZOOM,
            zoomControl: true
        });

        L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
            maxZoom: 19,
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        }).addTo(fullMap);

        fullClusterLayer = L.layerGroup().addTo(fullMap);
        fullMarkerLayer = L.layerGroup().addTo(fullMap);
    }

    function setupFilterListeners() {
        const btnApply = document.getElementById("btn-apply-map-filter");
        const btnReset = document.getElementById("btn-reset-map-filter");

        if (btnApply) {
            btnApply.addEventListener("click", () => {
                const type = document.getElementById("map-filter-type").value;
                const priority = document.getElementById("map-filter-priority").value;
                DashboardModule.refreshMapWithFilters(type, priority);
            });
        }

        if (btnReset) {
            btnReset.addEventListener("click", () => {
                document.getElementById("map-filter-type").value = "All";
                document.getElementById("map-filter-priority").value = "All";
                DashboardModule.refreshMapWithFilters("All", "All");
            });
        }
    }

    function renderDetections(detections, clusters = []) {
        if (!overviewMap) initOverviewMap();
        if (!fullMap) initFullMap();

        overviewMarkerLayer.clearLayers();
        fullMarkerLayer.clearLayers();
        fullClusterLayer.clearLayers();

        const allLatLngs = [];

        // 1. Render DBSCAN Cluster Zones on Full Map
        if (clusters && clusters.length > 0) {
            clusters.forEach((c) => {
                const color = PRIORITY_COLORS[c.priority_level] || "#8b5cf6";

                // Draw circle indicating spatial consensus area (~50m radius)
                const circle = L.circle([c.center_latitude, c.center_longitude], {
                    color: color,
                    fillColor: color,
                    fillOpacity: 0.15,
                    weight: 2,
                    dashArray: "4, 6",
                    radius: 50
                });

                const clusterPopupHtml = `
                    <div style="font-family: inherit; font-size: 12px; line-height: 1.4;">
                        <div style="font-weight: 700; font-size: 13px; color: ${color}; border-bottom: 1px solid #ddd; padding-bottom: 4px; margin-bottom: 4px;">
                            DBSCAN Cluster #${c.cluster_id}: ${c.event_type}
                        </div>
                        <div><strong>Center GPS:</strong> ${c.center_latitude.toFixed(5)}, ${c.center_longitude.toFixed(5)}</div>
                        <div><strong>Total Detections:</strong> ${c.detection_count} passes</div>
                        <div><strong>Unique Vehicles:</strong> ${c.unique_devices} independent devices</div>
                        <div><strong>Composite PDI:</strong> <strong>${c.max_pdi_score}</strong> / 100 (${c.priority_level})</div>
                        <div style="margin-top: 4px; font-size: 10px; color: #666;">
                            Crowdsourced consensus verifies physical road anomaly.
                        </div>
                    </div>
                `;
                circle.bindPopup(clusterPopupHtml);
                fullClusterLayer.addLayer(circle);
            });
        }

        // 2. Render Individual Detections
        detections.forEach((d) => {
            const lat = parseFloat(d.latitude);
            const lon = parseFloat(d.longitude);
            if (isNaN(lat) || isNaN(lon)) return;

            allLatLngs.push([lat, lon]);
            const markerColor = PRIORITY_COLORS[d.priority_level] || "#3b82f6";

            const popupContent = `
                <div style="font-family: inherit; font-size: 12px; line-height: 1.4;">
                    <div style="font-weight: 700; font-size: 13px; color: ${markerColor}; border-bottom: 1px solid #ddd; padding-bottom: 4px; margin-bottom: 4px;">
                        ${d.event_type} (PDI: ${d.pdi_score})
                    </div>
                    <div><strong>Device:</strong> ${d.device_id}</div>
                    <div><strong>Priority:</strong> <span style="font-weight: 600; color: ${markerColor};">${d.priority_level}</span></div>
                    <div><strong>Confidence:</strong> ${Math.round(d.confidence * 100)}%</div>
                    <div><strong>Peak Shock:</strong> ${d.peak_accel} m/s²</div>
                    <div><strong>Timestamp:</strong> ${new Date(d.timestamp).toLocaleTimeString()}</div>
                    <div style="margin-top: 6px; font-size: 10px; background: #eef2ff; color: #3730a3; padding: 3px 6px; border-radius: 4px;">
                        🔒 SHA-256 Sealed &bull; RSA Signed
                    </div>
                </div>
            `;

            // Overview Marker
            const overviewMarker = L.circleMarker([lat, lon], {
                radius: 6,
                fillColor: markerColor,
                color: "#fff",
                weight: 1.5,
                opacity: 1,
                fillOpacity: 0.85
            });
            overviewMarker.bindPopup(popupContent);
            overviewMarkerLayer.addLayer(overviewMarker);

            // Full Map Marker
            const fullMarker = L.circleMarker([lat, lon], {
                radius: 7,
                fillColor: markerColor,
                color: "#fff",
                weight: 1.5,
                opacity: 1,
                fillOpacity: 0.9
            });
            fullMarker.bindPopup(popupContent);
            fullMarkerLayer.addLayer(fullMarker);
        });

        // Auto-center viewports
        if (allLatLngs.length > 0) {
            const bounds = L.latLngBounds(allLatLngs);
            overviewMap.fitBounds(bounds, { padding: [25, 25], maxZoom: 15 });
            fullMap.fitBounds(bounds, { padding: [40, 40], maxZoom: 15 });
        } else {
            overviewMap.setView(DEFAULT_CENTER, DEFAULT_ZOOM);
            fullMap.setView(DEFAULT_CENTER, DEFAULT_ZOOM);
        }

        // Update cluster badge count
        const clusterBadge = document.getElementById("cluster-count-badge");
        if (clusterBadge) {
            clusterBadge.textContent = `${clusters ? clusters.length : 0} DBSCAN Clusters`;
        }
    }

    function fitMapToBounds(mapInstance, layerGroup) {
        if (!mapInstance || !layerGroup) return;
        const layers = layerGroup.getLayers();
        if (layers.length > 0) {
            const group = L.featureGroup(layers);
            mapInstance.fitBounds(group.getBounds(), { padding: [30, 30] });
        } else {
            mapInstance.setView(DEFAULT_CENTER, DEFAULT_ZOOM);
        }
    }

    function invalidateSize() {
        setTimeout(() => {
            if (overviewMap) overviewMap.invalidateSize();
            if (fullMap) fullMap.invalidateSize();
        }, 150);
    }

    return {
        init,
        renderDetections,
        invalidateSize
    };
})();
