document.addEventListener("DOMContentLoaded", () => {
    const sampleSelect = document.getElementById("sampleSelect");
    const fileUpload = document.getElementById("fileUpload");
    const confSlider = document.getElementById("confSlider");
    const confVal = document.getElementById("confVal");
    const btnRunInference = document.getElementById("btnRunInference");
    
    const statDice = document.getElementById("statDice");
    const statIou = document.getElementById("statIou");
    const statPrec = document.getElementById("statPrec");
    const statRec = document.getElementById("statRec");
    const statLatency = document.getElementById("statLatency");
    
    const sceneMetadata = document.getElementById("sceneMetadata");
    const icebergInspector = document.getElementById("icebergInspector");
    
    const imgOverlay = document.getElementById("imgOverlay");
    const imgPlaceholder = document.getElementById("imgPlaceholder");
    const imgProb = document.getElementById("imgProb");
    const imgCompareSar = document.getElementById("imgCompareSar");
    const imgCompareGt = document.getElementById("imgCompareGt");
    const imgComparePred = document.getElementById("imgComparePred");
    const imgCompareOverlay = document.getElementById("imgCompareOverlay");
    
    const jsonOutput = document.getElementById("jsonOutput");
    const icebergTableBody = document.getElementById("icebergTableBody");
    const icebergCount = document.getElementById("icebergCount");
    
    const tabBtns = document.querySelectorAll(".tab-button");
    const tabPanes = document.querySelectorAll(".tab-pane");

    let currentIcebergStates = [];

    // Tab Switching
    tabBtns.forEach(btn => {
        btn.addEventListener("click", () => {
            tabBtns.forEach(b => b.classList.remove("active"));
            tabPanes.forEach(p => p.classList.remove("active"));
            btn.classList.add("active");
            const target = document.getElementById(btn.dataset.tab);
            if (target) target.classList.add("active");
        });
    });

    // Probability Threshold Slider
    confSlider.addEventListener("input", (e) => {
        confVal.textContent = parseFloat(e.target.value).toFixed(2);
    });

    // Load Model Benchmark Metrics
    fetch("/api/metrics")
        .then(r => r.json())
        .then(data => {
            const m = data.test_metrics;
            if (m && m.dice_f1 !== undefined) {
                statDice.textContent = (m.dice_f1 * 100).toFixed(1) + "%";
                statIou.textContent = (m.iceberg_iou * 100).toFixed(1) + "%";
                statPrec.textContent = (m.precision * 100).toFixed(1) + "%";
                statRec.textContent = (m.recall * 100).toFixed(1) + "%";
                statLatency.textContent = m.avg_inference_latency_ms.toFixed(1) + " ms";
            }
        })
        .catch(err => console.error("Could not load metrics:", err));

    // Load Sample Scenes
    fetch("/api/samples")
        .then(r => r.json())
        .then(data => {
            sampleSelect.innerHTML = '<option value="">-- Choose Sentinel-1 Test Scene --</option>';
            data.samples.forEach((s, idx) => {
                const opt = document.createElement("option");
                opt.value = s.filename;
                opt.textContent = `Scene ${idx + 1}: ${s.filename.substring(0, 26)}... (${s.sensor} ${s.polarization})`;
                sampleSelect.appendChild(opt);
            });
            if (data.samples.length > 0) {
                sampleSelect.selectedIndex = 1;
            }
        })
        .catch(err => console.error("Could not load test scenes:", err));

    // Run Segmentation Handler
    btnRunInference.addEventListener("click", async () => {
        const uploadedFile = fileUpload.files[0];
        const selectedSample = sampleSelect.value;

        if (!uploadedFile && !selectedSample) {
            alert("Please select a sample scene or choose a GeoTIFF file to process.");
            return;
        }

        btnRunInference.disabled = true;
        btnRunInference.querySelector(".btn-text").textContent = "Segmenting Scene...";

        try {
            let resultData;
            if (uploadedFile) {
                const formData = new FormData();
                formData.append("file", uploadedFile);
                const res = await fetch("/api/predict-upload", {
                    method: "POST",
                    body: formData
                });
                resultData = await res.json();
            } else {
                const res = await fetch("/api/predict-sample", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ filename: selectedSample })
                });
                resultData = await res.json();
            }

            renderResults(resultData);
        } catch (err) {
            console.error("Segmentation error:", err);
            alert("Segmentation failed: " + err.message);
        } finally {
            btnRunInference.disabled = false;
            btnRunInference.querySelector(".btn-text").textContent = "Run Segmentation";
        }
    });

    function inspectIceberg(stateObj, rowIndex) {
        // Highlight row
        const allRows = icebergTableBody.querySelectorAll("tr");
        allRows.forEach((r, idx) => {
            if (idx === rowIndex) {
                r.classList.add("selected-row");
            } else {
                r.classList.remove("selected-row");
            }
        });

        if (!stateObj) {
            icebergInspector.innerHTML = `<p class="empty-note">No iceberg selected.</p>`;
            return;
        }

        const latStr = stateObj.latitude !== null ? `${stateObj.latitude.toFixed(5)}°` : "N/A";
        const lonStr = stateObj.longitude !== null ? `${stateObj.longitude.toFixed(5)}°` : "N/A";
        const projX = stateObj.projected_x !== null ? `${stateObj.projected_x.toLocaleString()} m` : "N/A";
        const projY = stateObj.projected_y !== null ? `${stateObj.projected_y.toLocaleString()} m` : "N/A";
        const areaM2 = stateObj.area_m2 !== null ? `${Math.round(stateObj.area_m2).toLocaleString()} m²` : "N/A";
        const areaKm2 = stateObj.area_km2 !== null ? `${stateObj.area_km2.toFixed(4)} km²` : "N/A";
        const perimM = stateObj.perimeter_m !== null ? `${Math.round(stateObj.perimeter_m).toLocaleString()} m` : "N/A";
        const lenM = stateObj.length_m !== null ? `${Math.round(stateObj.length_m)} m` : "N/A";
        const widM = stateObj.width_m !== null ? `${Math.round(stateObj.width_m)} m` : "N/A";
        const centroidStr = stateObj.centroid_pixel ? `(${stateObj.centroid_pixel.x.toFixed(1)}, ${stateObj.centroid_pixel.y.toFixed(1)})` : "N/A";

        icebergInspector.innerHTML = `
            <div class="meta-row"><span class="meta-key">Iceberg ID</span><span class="meta-val" style="color:var(--accent); font-weight:700;">${stateObj.iceberg_id}</span></div>
            <div class="meta-row"><span class="meta-key">Confidence</span><span class="meta-val">${(stateObj.segmentation_confidence * 100).toFixed(1)}%</span></div>
            <div class="meta-row"><span class="meta-key">Timestamp (UTC)</span><span class="meta-val">${stateObj.timestamp || 'N/A'}</span></div>
            <div class="meta-row"><span class="meta-key">Latitude (WGS84)</span><span class="meta-val">${latStr}</span></div>
            <div class="meta-row"><span class="meta-key">Longitude (WGS84)</span><span class="meta-val">${lonStr}</span></div>
            <div class="meta-row"><span class="meta-key">Projected X</span><span class="meta-val">${projX}</span></div>
            <div class="meta-row"><span class="meta-key">Projected Y</span><span class="meta-val">${projY}</span></div>
            <div class="meta-row"><span class="meta-key">Area (km²)</span><span class="meta-val">${areaKm2}</span></div>
            <div class="meta-row"><span class="meta-key">Area (m²)</span><span class="meta-val">${areaM2}</span></div>
            <div class="meta-row"><span class="meta-key">Dimensions (L × W)</span><span class="meta-val">${lenM} × ${widM}</span></div>
            <div class="meta-row"><span class="meta-key">Perimeter</span><span class="meta-val">${perimM}</span></div>
            <div class="meta-row"><span class="meta-key">Orientation</span><span class="meta-val">${stateObj.orientation_deg ? stateObj.orientation_deg.toFixed(1) + '°' : '0.0°'}</span></div>
            <div class="meta-row"><span class="meta-key">Aspect Ratio</span><span class="meta-val">${stateObj.aspect_ratio ? stateObj.aspect_ratio.toFixed(2) : '1.00'}</span></div>
            <div class="meta-row"><span class="meta-key">Pixel Centroid</span><span class="meta-val">${centroidStr}</span></div>
            <div class="meta-row"><span class="meta-key">Native CRS</span><span class="meta-val">${stateObj.crs || 'EPSG:3996'}</span></div>
        `;
    }

    function renderResults(data) {
        const imgs = data.images || {};
        currentIcebergStates = data.iceberg_states || [];
        
        // 1. Update Display Images
        if (imgs.overlay) {
            imgOverlay.src = "data:image/png;base64," + imgs.overlay;
            imgOverlay.style.display = "block";
            imgPlaceholder.style.display = "none";
            imgCompareOverlay.src = "data:image/png;base64," + imgs.overlay;
        }
        if (imgs.sar) {
            imgCompareSar.src = "data:image/png;base64," + imgs.sar;
        }
        if (imgs.probability_map) {
            imgProb.src = "data:image/png;base64," + imgs.probability_map;
        }
        if (imgs.predicted_mask) {
            imgComparePred.src = "data:image/png;base64," + imgs.predicted_mask;
        }
        if (imgs.ground_truth_mask) {
            imgCompareGt.src = "data:image/png;base64," + imgs.ground_truth_mask;
        } else {
            imgCompareGt.src = "data:image/png;base64," + (imgs.predicted_mask || "");
        }

        // 2. Update Scene Metadata Panel
        const doc = data.document || {};
        sceneMetadata.innerHTML = `
            <div class="meta-row"><span class="meta-key">File</span><span class="meta-val" title="${data.image_name}">${data.image_name ? data.image_name.substring(0, 18) + '...' : 'N/A'}</span></div>
            <div class="meta-row"><span class="meta-key">Acquisition UTC</span><span class="meta-val" style="color:var(--accent);">${doc.acquisition_timestamp || 'N/A'}</span></div>
            <div class="meta-row"><span class="meta-key">Sensor / Mode</span><span class="meta-val">${doc.sensor || 'Sentinel-1'} (${doc.mode || 'EW'})</span></div>
            <div class="meta-row"><span class="meta-key">Polarization</span><span class="meta-val">${doc.polarization || 'HH + HV'}</span></div>
            <div class="meta-row"><span class="meta-key">Native Projection</span><span class="meta-val">${doc.native_crs || 'EPSG:3996'}</span></div>
            <div class="meta-row"><span class="meta-key">Geographic CRS</span><span class="meta-val">EPSG:4326 (WGS84)</span></div>
            <div class="meta-row"><span class="meta-key">Ground Resolution</span><span class="meta-val">${doc.pixel_resolution_m || 40.0} m/pixel</span></div>
            <div class="meta-row"><span class="meta-key">Extracted Icebergs</span><span class="meta-val" style="color:var(--accent); font-weight:700;">${data.total_detected} detected</span></div>
        `;

        // 3. Update Raw JSON
        jsonOutput.textContent = JSON.stringify(data.document, null, 2);

        // 4. Populate Extracted Icebergs Table
        icebergCount.textContent = data.total_detected;
        
        if (currentIcebergStates.length === 0) {
            icebergTableBody.innerHTML = `<tr><td colspan="11" class="table-empty">No iceberg targets detected above threshold.</td></tr>`;
            icebergInspector.innerHTML = `<p class="empty-note">No icebergs extracted in this scene.</p>`;
        } else {
            icebergTableBody.innerHTML = currentIcebergStates.map((ib, idx) => {
                const latStr = ib.latitude !== null ? `${ib.latitude.toFixed(4)}°` : 'N/A';
                const lonStr = ib.longitude !== null ? `${ib.longitude.toFixed(4)}°` : 'N/A';
                const projXStr = ib.projected_x !== null ? Math.round(ib.projected_x).toLocaleString() : 'N/A';
                const projYStr = ib.projected_y !== null ? Math.round(ib.projected_y).toLocaleString() : 'N/A';
                const areaKm2 = ib.area_km2 !== null ? ib.area_km2.toFixed(4) : 'N/A';
                const areaM2 = ib.area_m2 !== null ? Math.round(ib.area_m2).toLocaleString() : 'N/A';
                const lengthM = ib.length_m !== null ? Math.round(ib.length_m) : 'N/A';
                const widthM = ib.width_m !== null ? Math.round(ib.width_m) : 'N/A';
                const orientStr = ib.orientation_deg !== null ? `${ib.orientation_deg.toFixed(1)}°` : 'N/A';
                const timeStr = ib.timestamp || 'N/A';
                
                return `
                    <tr data-index="${idx}">
                        <td><strong>${ib.iceberg_id}</strong></td>
                        <td><span class="conf-pill">${(ib.segmentation_confidence * 100).toFixed(1)}%</span></td>
                        <td>${timeStr}</td>
                        <td>${latStr}</td>
                        <td>${lonStr}</td>
                        <td>${projXStr}</td>
                        <td>${projYStr}</td>
                        <td>${areaKm2}</td>
                        <td>${areaM2}</td>
                        <td>${lengthM} × ${widthM}</td>
                        <td>${orientStr}</td>
                    </tr>
                `;
            }).join("");

            // Add click listeners to each row
            const rows = icebergTableBody.querySelectorAll("tr");
            rows.forEach((row, idx) => {
                row.addEventListener("click", () => {
                    inspectIceberg(currentIcebergStates[idx], idx);
                });
            });

            // Automatically inspect the first (or largest) iceberg
            inspectIceberg(currentIcebergStates[0], 0);
        }
    }
});
