/**
 * Admin Dashboard - Interactive Client Engine
 * Handles Global Search, Risk/Date Filters, Sorting, Modals, Lightbox & CSV Exports
 */

// Global filter state
let currentSearch = "";
let currentRisk = "all";
let currentDateFilter = "all";
let currentCustomDate = "";
let currentSortCol = "score";
let currentSortDir = "asc"; // Default: Lowest score first (prioritizes attention)
let riskDonutChartInstance = null;

document.addEventListener("DOMContentLoaded", function() {
    initSidebarToggle();
    initScoreBars();
    initRiskDonutChart();
    initFilteringEngine();
    initSortingEngine();
    initBatchExport();
    initModalEventListeners();
});

// ==========================================
// 0. VS Code Style Collapsible Sidebar Toggle
// ==========================================
function initSidebarToggle() {
    const sidebar = document.getElementById("adminSidebar");
    const layout = document.getElementById("dashboardLayout");
    const toggleBtn = document.getElementById("sidebarToggleBtn");
    const miniToggleBtn = document.getElementById("sidebarMiniToggle");

    if (!sidebar) return;

    // Load saved sidebar state preference
    const savedState = localStorage.getItem("admin_sidebar_collapsed");
    if (savedState === "true") {
        collapseSidebar(false);
    }

    function toggleSidebar() {
        const isCollapsed = sidebar.classList.contains("collapsed") || (layout && layout.classList.contains("sidebar-collapsed"));
        if (isCollapsed) {
            expandSidebar(true);
        } else {
            collapseSidebar(true);
        }
    }

    function collapseSidebar(save = true) {
        sidebar.classList.add("collapsed");
        if (layout) layout.classList.add("sidebar-collapsed");
        if (miniToggleBtn) {
            miniToggleBtn.innerHTML = '<i class="fa-solid fa-angles-right"></i>';
            miniToggleBtn.title = "Expand Sidebar";
        }
        if (save) localStorage.setItem("admin_sidebar_collapsed", "true");
        triggerChartResize();
    }

    function expandSidebar(save = true) {
        sidebar.classList.remove("collapsed");
        if (layout) layout.classList.remove("sidebar-collapsed");
        if (miniToggleBtn) {
            miniToggleBtn.innerHTML = '<i class="fa-solid fa-angles-left"></i>';
            miniToggleBtn.title = "Collapse Sidebar";
        }
        if (save) localStorage.setItem("admin_sidebar_collapsed", "false");
        triggerChartResize();
    }

    function triggerChartResize() {
        setTimeout(() => {
            if (riskDonutChartInstance) {
                riskDonutChartInstance.resize();
            }
        }, 260);
    }

    if (toggleBtn) {
        toggleBtn.addEventListener("click", function(e) {
            e.preventDefault();
            toggleSidebar();
        });
    }

    if (miniToggleBtn) {
        miniToggleBtn.addEventListener("click", function(e) {
            e.preventDefault();
            toggleSidebar();
        });
    }
}

function initScoreBars() {
    document.querySelectorAll(".mini-score-fill[data-score]").forEach(el => {
        const sc = el.getAttribute("data-score") || "0";
        el.style.width = sc + "%";
    });
}

// ==========================================
// 1. Chart.js Risk Distribution Donut Chart
// ==========================================
function initRiskDonutChart() {
    const ctx = document.getElementById("riskDonutChart");
    if (!ctx) return;

    const lowCount = Number(ctx.getAttribute("data-low") || 0);
    const medCount = Number(ctx.getAttribute("data-medium") || 0);
    const highCount = Number(ctx.getAttribute("data-high") || 0);

    riskDonutChartInstance = new Chart(ctx, {
        type: "doughnut",
        data: {
            labels: ["Low Risk", "Medium Risk", "High Risk"],
            datasets: [{
                data: [lowCount, medCount, highCount],
                backgroundColor: [
                    "#10b981", // green
                    "#f59e0b", // amber
                    "#ef4444"  // red
                ],
                borderWidth: 3,
                borderColor: "#ffffff",
                hoverOffset: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: "72%",
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const label = context.label || "";
                            const val = context.raw || 0;
                            const currentData = context.dataset.data || [];
                            const total = currentData.reduce((a, b) => a + b, 0);
                            const pct = total > 0 ? ((val / total) * 100).toFixed(1) : 0;
                            return ` ${label}: ${val} (${pct}%)`;
                        }
                    }
                }
            }
        }
    });
}

// ==========================================
// 2. Global Search, Date & Risk Filter Engine
// ==========================================
function initFilteringEngine() {
    const searchInput = document.getElementById("globalSearchInput");
    const clearSearchBtn = document.getElementById("clearSearchBtn");

    if (searchInput) {
        searchInput.addEventListener("input", function() {
            currentSearch = this.value.trim().toLowerCase();
            if (clearSearchBtn) clearSearchBtn.style.display = currentSearch ? "block" : "none";
            applyAllFilters();
        });
    }

    if (clearSearchBtn) {
        clearSearchBtn.addEventListener("click", function() {
            if (searchInput) searchInput.value = "";
            currentSearch = "";
            clearSearchBtn.style.display = "none";
            applyAllFilters();
        });
    }

    // Risk Filter Pills
    const riskPills = document.querySelectorAll("#riskFilterPills .filter-pill");
    riskPills.forEach(pill => {
        pill.addEventListener("click", function() {
            riskPills.forEach(p => p.classList.remove("active"));
            this.classList.add("active");
            currentRisk = this.getAttribute("data-risk") || "all";
            applyAllFilters();
        });
    });

    // Date Filter Pills
    const datePills = document.querySelectorAll("#dateFilterPills .filter-pill");
    const customDateInput = document.getElementById("customDateInput");

    datePills.forEach(pill => {
        pill.addEventListener("click", function() {
            datePills.forEach(p => p.classList.remove("active"));
            this.classList.add("active");
            currentDateFilter = this.getAttribute("data-date") || "all";
            if (customDateInput) customDateInput.value = "";
            currentCustomDate = "";
            applyAllFilters();
        });
    });

    if (customDateInput) {
        customDateInput.addEventListener("change", function() {
            if (this.value) {
                datePills.forEach(p => p.classList.remove("active"));
                currentDateFilter = "custom";
                currentCustomDate = this.value;
                applyAllFilters();
            }
        });
    }

    const resetBtn = document.getElementById("resetAllFiltersBtn");
    if (resetBtn) {
        resetBtn.addEventListener("click", resetAllFilters);
    }
}

function resetAllFilters() {
    const searchInput = document.getElementById("globalSearchInput");
    const clearSearchBtn = document.getElementById("clearSearchBtn");
    if (searchInput) searchInput.value = "";
    if (clearSearchBtn) clearSearchBtn.style.display = "none";
    currentSearch = "";

    const riskPills = document.querySelectorAll("#riskFilterPills .filter-pill");
    riskPills.forEach(p => p.classList.remove("active"));
    const allRiskPill = document.querySelector("#riskFilterPills .filter-pill[data-risk='all']");
    if (allRiskPill) allRiskPill.classList.add("active");
    currentRisk = "all";

    const datePills = document.querySelectorAll("#dateFilterPills .filter-pill");
    datePills.forEach(p => p.classList.remove("active"));
    const allDatePill = document.querySelector("#dateFilterPills .filter-pill[data-date='all']");
    if (allDatePill) allDatePill.classList.add("active");
    currentDateFilter = "all";

    const customDateInput = document.getElementById("customDateInput");
    if (customDateInput) customDateInput.value = "";
    currentCustomDate = "";

    applyAllFilters();
}

function isDateMatch(sessionDate) {
    if (currentDateFilter === "all") return true;
    if (!sessionDate) return false;

    const now = new Date();
    const todayStr = formatDateISO(now);

    if (currentDateFilter === "today") {
        return sessionDate.startsWith(todayStr);
    }

    if (currentDateFilter === "yesterday") {
        const yesterdayDate = new Date();
        yesterdayDate.setDate(yesterdayDate.getDate() - 1);
        return sessionDate.startsWith(formatDateISO(yesterdayDate));
    }

    if (currentDateFilter === "7days") {
        const sevenDaysAgo = new Date();
        sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7);
        sevenDaysAgo.setHours(0, 0, 0, 0);
        const sDate = new Date(sessionDate.length === 10 ? sessionDate + "T00:00:00" : sessionDate);
        return sDate >= sevenDaysAgo;
    }

    if (currentDateFilter === "custom" && currentCustomDate) {
        return sessionDate.startsWith(currentCustomDate);
    }

    return true;
}

function applyAllFilters() {
    const rows = document.querySelectorAll("#sessionsTableBody .session-row");
    if (!rows.length) return;

    let visibleCount = 0;
    const dateMatchingRows = [];

    rows.forEach(row => {
        const candName = (row.getAttribute("data-candidate-name") || "").toLowerCase();
        const candId = (row.getAttribute("data-candidate-id") || "").toLowerCase();
        const sessionId = row.getAttribute("data-session-id") || "";
        const sessionDate = row.getAttribute("data-date") || "";
        const sessionRisk = row.getAttribute("data-risk") || "";

        // 1. Search Query Match (Name, ID, Session ID)
        let matchesSearch = true;
        if (currentSearch) {
            const cleanQuery = currentSearch.replace("#", "");
            matchesSearch = candName.includes(cleanQuery) ||
                            candId.includes(cleanQuery) ||
                            sessionId.includes(cleanQuery);
        }

        // 2. Risk Match
        let matchesRisk = true;
        if (currentRisk !== "all") {
            matchesRisk = (sessionRisk === currentRisk);
        }

        // 3. Date Match
        let matchesDate = isDateMatch(sessionDate);

        if (matchesDate && matchesSearch) {
            dateMatchingRows.push(row);
        }

        if (matchesSearch && matchesRisk && matchesDate) {
            row.style.display = "";
            visibleCount++;
        } else {
            row.style.display = "none";
        }
    });

    const filterBanner = document.getElementById("filterStatusBanner");
    const matchingCountEl = document.getElementById("matchingCount");
    const noResultsBox = document.getElementById("noMatchingResultsBox");
    const isFiltering = currentSearch || currentRisk !== "all" || currentDateFilter !== "all" || currentCustomDate;

    if (filterBanner) {
        filterBanner.style.display = isFiltering ? "flex" : "none";
        if (matchingCountEl) matchingCountEl.innerText = String(visibleCount);
    }

    if (noResultsBox) {
        noResultsBox.style.display = (visibleCount === 0 && rows.length > 0) ? "block" : "none";
    }

    // Dynamically update Candidate Risk Distribution, Needs Attention cards, and Summary Stats
    updateRiskDistribution(dateMatchingRows);
    updateNeedsAttention();
    updateTopSummaryStats(dateMatchingRows);

    updateSelectedBatchCounter();
}

function updateRiskDistribution(matchingRows) {
    let lowRisk = 0, medRisk = 0, highRisk = 0;
    matchingRows.forEach(row => {
        const r = row.getAttribute("data-risk");
        if (r === "Low Risk") lowRisk++;
        else if (r === "Medium Risk") medRisk++;
        else if (r === "High Risk") highRisk++;
    });

    const total = matchingRows.length;

    // Update Donut Chart
    if (riskDonutChartInstance) {
        riskDonutChartInstance.data.datasets[0].data = [lowRisk, medRisk, highRisk];
        riskDonutChartInstance.update();
    }

    // Update Center Value
    const centerVal = document.getElementById("donutCenterVal");
    if (centerVal) centerVal.innerText = String(total);

    // Update Header Badge
    const headerBadge = document.getElementById("riskDonutTotalBadge");
    if (headerBadge) {
        headerBadge.innerText = `${total} Total Session${total !== 1 ? 's' : ''}`;
    }

    // Update Legend Counts & Percentages
    const lowCountEl = document.getElementById("donutLowCount");
    const lowPctEl = document.getElementById("donutLowPct");
    if (lowCountEl) lowCountEl.innerText = String(lowRisk);
    if (lowPctEl) lowPctEl.innerText = `(${total > 0 ? ((lowRisk / total) * 100).toFixed(1) : 0}%)`;

    const medCountEl = document.getElementById("donutMediumCount");
    const medPctEl = document.getElementById("donutMediumPct");
    if (medCountEl) medCountEl.innerText = String(medRisk);
    if (medPctEl) medPctEl.innerText = `(${total > 0 ? ((medRisk / total) * 100).toFixed(1) : 0}%)`;

    const highCountEl = document.getElementById("donutHighCount");
    const highPctEl = document.getElementById("donutHighPct");
    if (highCountEl) highCountEl.innerText = String(highRisk);
    if (highPctEl) highPctEl.innerText = `(${total > 0 ? ((highRisk / total) * 100).toFixed(1) : 0}%)`;
}

function updateNeedsAttention() {
    const attentionCards = document.querySelectorAll("#attentionCardsContainer .attention-item-card");
    let visibleAttCount = 0;

    attentionCards.forEach(card => {
        const cardDate = card.getAttribute("data-date") || "";
        const cardRisk = card.getAttribute("data-risk") || "";
        const candName = (card.getAttribute("data-candidate-name") || "").toLowerCase();
        const candId = (card.getAttribute("data-candidate-id") || "").toLowerCase();
        const sessionId = card.getAttribute("data-session-id") || "";

        let matchesSearch = true;
        if (currentSearch) {
            const cleanQuery = currentSearch.replace("#", "");
            matchesSearch = candName.includes(cleanQuery) ||
                            candId.includes(cleanQuery) ||
                            sessionId.includes(cleanQuery);
        }

        let matchesRisk = true;
        if (currentRisk !== "all") {
            matchesRisk = (cardRisk === currentRisk);
        }

        let matchesDate = isDateMatch(cardDate);

        if (matchesDate && matchesRisk && matchesSearch) {
            card.style.display = "";
            visibleAttCount++;
        } else {
            card.style.display = "none";
        }
    });

    const needsAttentionBadge = document.getElementById("needsAttentionBadge");
    if (needsAttentionBadge) {
        needsAttentionBadge.innerText = `${visibleAttCount} Flagged Session${visibleAttCount !== 1 ? 's' : ''}`;
    }

    const emptyAttentionState = document.getElementById("emptyAttentionState");
    if (emptyAttentionState) {
        emptyAttentionState.style.display = (visibleAttCount === 0) ? "block" : "none";
    }
}

function updateTopSummaryStats(matchingRows) {
    const statTotalSessions = document.getElementById("statTotalSessions");
    const statActiveSessions = document.getElementById("statActiveSessions");
    const statCompletedSessions = document.getElementById("statCompletedSessions");
    const statAvgScore = document.getElementById("statAvgScore");
    const statScoreRange = document.getElementById("statScoreRange");
    const statHighRisk = document.getElementById("statHighRisk");
    const statTotalEvents = document.getElementById("statTotalEvents");

    const total = matchingRows.length;
    let activeCount = 0, completedCount = 0, totalEventsCount = 0, highRiskCount = 0;
    let scores = [];

    matchingRows.forEach(row => {
        const status = (row.getAttribute("data-status") || "").toLowerCase();
        const statusCode = (row.getAttribute("data-status-code") || "").toLowerCase();
        const risk = row.getAttribute("data-risk");

        if (statusCode === "active" || status === "active") activeCount++;
        if (statusCode === "completed" || status === "completed" || status === "ended") completedCount++;
        if (risk === "High Risk") highRiskCount++;

        const score = parseFloat(row.getAttribute("data-score"));
        if (!isNaN(score)) scores.push(score);

        const ev = parseInt(row.getAttribute("data-events"), 10);
        if (!isNaN(ev)) totalEventsCount += ev;
    });

    if (statTotalSessions) statTotalSessions.innerText = String(total);
    if (statActiveSessions) {
        statActiveSessions.innerHTML = `${activeCount}${activeCount > 0 ? ' <span class="live-pulse-dot" title="Live exam in progress"></span>' : ''}`;
    }
    if (statCompletedSessions) statCompletedSessions.innerText = String(completedCount);

    if (statAvgScore) {
        const avg = scores.length > 0 ? (scores.reduce((a, b) => a + b, 0) / scores.length).toFixed(1) : "0.0";
        statAvgScore.innerText = `${avg}%`;
    }
    if (statScoreRange) {
        const maxScore = scores.length > 0 ? Math.max(...scores) : 0;
        const minScore = scores.length > 0 ? Math.min(...scores) : 0;
        statScoreRange.innerText = `High: ${maxScore} | Low: ${minScore}`;
    }
    if (statHighRisk) statHighRisk.innerText = String(highRiskCount);
    if (statTotalEvents) statTotalEvents.innerText = String(totalEventsCount);
}

function formatDateISO(d) {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${y}-${m}-${day}`;
}

// ==========================================
// 3. Sortable Table Columns
// ==========================================
function initSortingEngine() {
    const headers = document.querySelectorAll("#sessionsMasterTable th[data-sort]");
    headers.forEach(th => {
        th.addEventListener("click", function() {
            const col = this.getAttribute("data-sort");
            if (currentSortCol === col) {
                currentSortDir = currentSortDir === "asc" ? "desc" : "asc";
            } else {
                currentSortCol = col;
                currentSortDir = col === "score" ? "asc" : "desc";
            }

            headers.forEach(h => {
                h.classList.remove("sorted-col");
                const icon = h.querySelector(".sort-icon");
                if (icon) icon.className = "fa-solid fa-sort sort-icon";
            });

            this.classList.add("sorted-col");
            const icon = this.querySelector(".sort-icon");
            if (icon) {
                icon.className = currentSortDir === "asc" ? "fa-solid fa-sort-up sort-icon" : "fa-solid fa-sort-down sort-icon";
            }

            sortSessionsTable(currentSortCol, currentSortDir);
        });
    });
}

function sortSessionsTable(col, direction) {
    const tbody = document.getElementById("sessionsTableBody");
    if (!tbody) return;
    const rows = Array.from(tbody.querySelectorAll(".session-row"));
    if (!rows.length) return;

    rows.sort((a, b) => {
        let valA, valB;
        if (col === "score") {
            valA = Number(a.getAttribute("data-score")) || 0;
            valB = Number(b.getAttribute("data-score")) || 0;
        } else if (col === "events") {
            valA = Number(a.getAttribute("data-events")) || 0;
            valB = Number(b.getAttribute("data-events")) || 0;
        } else if (col === "face_presence") {
            valA = Number(a.getAttribute("data-face-presence")) || 0;
            valB = Number(b.getAttribute("data-face-presence")) || 0;
        } else if (col === "session_id") {
            valA = Number(a.getAttribute("data-session-id")) || 0;
            valB = Number(b.getAttribute("data-session-id")) || 0;
        } else if (col === "candidate") {
            valA = a.getAttribute("data-candidate-name") || "";
            valB = b.getAttribute("data-candidate-name") || "";
        } else if (col === "candidate_id") {
            valA = a.getAttribute("data-candidate-id") || "";
            valB = b.getAttribute("data-candidate-id") || "";
        } else if (col === "risk") {
            const riskMap = { "High Risk": 3, "Medium Risk": 2, "Low Risk": 1 };
            valA = riskMap[a.getAttribute("data-risk")] || 0;
            valB = riskMap[b.getAttribute("data-risk")] || 0;
        } else if (col === "status") {
            valA = a.getAttribute("data-status") || "";
            valB = b.getAttribute("data-status") || "";
        } else {
            valA = a.getAttribute("data-timestamp") || "";
            valB = b.getAttribute("data-timestamp") || "";
        }

        if (typeof valA === "string") {
            return direction === "asc" ? valA.localeCompare(valB) : valB.localeCompare(valA);
        } else {
            return direction === "asc" ? valA - valB : valB - valA;
        }
    });

    rows.forEach(r => tbody.appendChild(r));
}

// ==========================================
// 4. Batch Checkbox Selection & CSV Export
// ==========================================
function initBatchExport() {
    const selectAllCheckbox = document.getElementById("selectAllCheckbox");
    const exportSelectedBtn = document.getElementById("exportSelectedBtn");
    const exportFilteredBtn = document.getElementById("exportFilteredBtn");

    if (selectAllCheckbox) {
        selectAllCheckbox.addEventListener("change", function() {
            const visibleRowCheckboxes = document.querySelectorAll("#sessionsTableBody .session-row:not([style*='display: none']) .session-row-checkbox");
            visibleRowCheckboxes.forEach(cb => {
                cb.checked = selectAllCheckbox.checked;
            });
            updateSelectedBatchCounter();
        });
    }

    document.addEventListener("change", function(e) {
        if (e.target && e.target.classList.contains("session-row-checkbox")) {
            updateSelectedBatchCounter();
        }
    });

    if (exportSelectedBtn) {
        exportSelectedBtn.addEventListener("click", function() {
            const checkedCbs = document.querySelectorAll(".session-row-checkbox:checked");
            const ids = Array.from(checkedCbs).map(cb => cb.value).join(",");
            if (ids) {
                window.location.href = `/admin/export-sessions-csv?session_ids=${encodeURIComponent(ids)}`;
            }
        });
    }

    if (exportFilteredBtn) {
        exportFilteredBtn.addEventListener("click", function() {
            const visibleRows = document.querySelectorAll("#sessionsTableBody .session-row:not([style*='display: none'])");
            const ids = Array.from(visibleRows).map(r => r.getAttribute("data-session-id")).filter(Boolean).join(",");
            if (ids) {
                window.location.href = `/admin/export-sessions-csv?session_ids=${encodeURIComponent(ids)}`;
            } else {
                window.location.href = `/admin/export-sessions-csv`;
            }
        });
    }
}

function updateSelectedBatchCounter() {
    const checked = document.querySelectorAll(".session-row-checkbox:checked");
    const countLabel = document.getElementById("selectedCountLabel");
    const exportBtn = document.getElementById("exportSelectedBtn");

    if (countLabel && exportBtn) {
        if (checked.length > 0) {
            countLabel.style.display = "inline-block";
            countLabel.innerText = `${checked.length} selected`;
            exportBtn.disabled = false;
            exportBtn.innerHTML = `<i class="fa-solid fa-download"></i> Export Selected (${checked.length})`;
        } else {
            countLabel.style.display = "none";
            exportBtn.disabled = true;
            exportBtn.innerHTML = `<i class="fa-solid fa-download"></i> Export Selected CSV`;
        }
    }
}

// ==========================================
// 5. Modal & Lightbox Event Listeners
// ==========================================
function initModalEventListeners() {
    document.addEventListener("click", function(e) {
        // Open session modal via data attribute
        const viewSessionBtn = e.target.closest("[data-view-session]");
        if (viewSessionBtn) {
            const sid = viewSessionBtn.getAttribute("data-view-session");
            if (sid) openSessionModal(sid);
            return;
        }

        // Open evidence lightbox via data attribute
        const viewProofBtn = e.target.closest("[data-view-proof]");
        if (viewProofBtn) {
            const proofUrl = viewProofBtn.getAttribute("data-view-proof");
            const candId = viewProofBtn.getAttribute("data-candidate-id") || "Candidate";
            const caption = viewProofBtn.getAttribute("data-caption") || "Violation Evidence";
            if (proofUrl) openEvidenceViewer(proofUrl, candId, caption);
            return;
        }

        // Modal backdrop click
        const sessionModal = document.getElementById("sessionDetailsModal");
        const evidenceModal = document.getElementById("evidenceViewerModal");
        if (e.target === sessionModal) closeSessionModal();
        if (e.target === evidenceModal) closeEvidenceViewer();
    });

    document.addEventListener("keydown", function(e) {
        if (e.key === "Escape") {
            closeSessionModal();
            closeEvidenceViewer();
        }
    });
}

function openSessionModal(sessionId) {
    const modal = document.getElementById("sessionDetailsModal");
    const titleEl = document.getElementById("modalSessionTitle");
    const subEl = document.getElementById("modalSessionSub");
    const bodyEl = document.getElementById("modalSessionBody");
    const pdfBtn = document.getElementById("modalDownloadPdfBtn");
    const reportBtn = document.getElementById("modalViewReportBtn");

    if (!modal) return;
    modal.style.display = "flex";
    if (titleEl) titleEl.innerText = `Session Details #${sessionId}`;
    if (subEl) subEl.innerText = "Loading candidate telemetry...";
    if (pdfBtn) pdfBtn.href = `/download-report/${sessionId}`;
    if (reportBtn) reportBtn.href = `/exam-report/${sessionId}`;

    if (bodyEl) {
        bodyEl.innerHTML = `
            <div class="modal-loading-spinner">
                <i class="fa-solid fa-circle-notch fa-spin"></i>
                <p>Loading candidate telemetry & infraction logs...</p>
            </div>
        `;
    }

    fetch(`/admin/session/${sessionId}/details`)
        .then(res => res.json())
        .then(data => {
            if (!data.success) {
                if (bodyEl) bodyEl.innerHTML = `<div class="empty-state"><p>${data.message || 'Error loading session details'}</p></div>`;
                return;
            }

            if (subEl) subEl.innerText = `${data.candidate_name} (${data.candidate_id}) • ${data.start_time}`;

            const scoreBadgeClass = data.integrity_score >= 80 ? 'badge-success' : (data.integrity_score >= 50 ? 'badge-warning' : 'badge-danger');
            const riskBadgeClass = data.risk_label === 'Low Risk' ? 'badge-success' : (data.risk_label === 'Medium Risk' ? 'badge-warning' : 'badge-danger');

            let timelineHtml = "";
            if (data.events && data.events.length > 0) {
                timelineHtml = data.events.map(ev => {
                    const badgeClass = (ev.event_type.includes('Lost') || ev.event_type.includes('Not Detected') || ev.event_type.includes('Multiple')) ? 'badge-danger' : 'badge-warning';
                    const penaltyText = ev.penalty < 0 ? `${ev.penalty} pts` : (ev.deduction > 0 ? `-${ev.deduction} pts` : '0 pts');
                    const proofBtn = ev.proof_image ? `
                        <button type="button" class="btn-inline-proof" data-view-proof="/static/${ev.proof_image}" data-candidate-id="${data.candidate_id}" data-caption="${ev.event_type} at ${ev.timestamp}">
                            <i class="fa-solid fa-eye"></i> Evidence
                        </button>
                    ` : '';

                    return `
                        <div class="modal-timeline-row">
                            <span class="m-time"><i class="fa-regular fa-clock"></i> ${ev.timestamp}</span>
                            <span class="badge ${badgeClass}">${ev.event_type}</span>
                            <span class="m-penalty">${penaltyText}</span>
                            <span class="m-score-rem">Running: <strong>${ev.running_score}</strong></span>
                            ${proofBtn}
                        </div>
                    `;
                }).join('');
            } else {
                timelineHtml = `<p style="color: var(--text-muted); font-size: 0.9rem; padding: 10px 0;"><i class="fa-solid fa-circle-check" style="color: #10b981;"></i> No suspicious events recorded in this session.</p>`;
            }

            let proofsHtml = "";
            if (data.proofs && data.proofs.length > 0) {
                proofsHtml = `
                    <div class="modal-section-title" style="margin-top: 1.5rem;">
                        <i class="fa-solid fa-camera"></i> Security Evidence Snapshots (${data.proofs.length})
                    </div>
                    <div class="modal-proofs-grid">
                        ${data.proofs.map(p => `
                            <div class="proof-thumbnail-card" data-view-proof="/static/${p}" data-candidate-id="${data.candidate_id}" data-caption="Session #${data.session_id} Security Proof">
                                <img src="/static/${p}" alt="Violation Proof">
                                <span class="proof-hover-zoom"><i class="fa-solid fa-magnifying-glass-plus"></i></span>
                            </div>
                        `).join('')}
                    </div>
                `;
            }

            if (bodyEl) {
                bodyEl.innerHTML = `
                    <div class="modal-info-grid">
                        <div class="m-card">
                            <span class="m-card-lbl">Candidate</span>
                            <h4 style="font-size: 1rem; margin: 4px 0;">${data.candidate_name}</h4>
                            <span style="font-size: 0.8rem; color: var(--text-muted);">ID: <code>${data.candidate_id}</code></span>
                        </div>
                        <div class="m-card">
                            <span class="m-card-lbl">Integrity Score</span>
                            <h3 style="font-size: 1.5rem; margin: 4px 0;" class="${scoreBadgeClass}">${data.integrity_score}/100</h3>
                            <span class="badge ${riskBadgeClass}">${data.risk_label}</span>
                        </div>
                        <div class="m-card">
                            <span class="m-card-lbl">Timing & Duration</span>
                            <span style="display: block; font-size: 0.85rem; margin-top: 4px;"><strong>Start:</strong> ${data.start_time}</span>
                            <span style="display: block; font-size: 0.85rem;"><strong>End:</strong> ${data.end_time}</span>
                            <span style="display: block; font-size: 0.85rem; color: var(--primary-color);"><strong>Duration:</strong> ${data.duration}</span>
                            <span style="display: block; font-size: 0.85rem; margin-top: 4px;"><strong>Verification:</strong> ${data.identity_verified == 1 ? '<span class="badge badge-success" style="color:#10b981; font-weight:bold;">✓ Verified</span>' : '<span class="badge badge-danger" style="color:#ef4444; font-weight:bold;">✗ Failed</span>'}</span>
                            <span style="display: block; font-size: 0.85rem;"><strong>Verify Time:</strong> ${data.verification_time || 'N/A'}</span>
                            <span style="display: block; font-size: 0.85rem;"><strong>Attempts:</strong> ${data.verification_attempts || 0}</span>
                        </div>
                        <div class="m-card">
                            <span class="m-card-lbl">Infraction Summary</span>
                            <span style="display: block; font-size: 0.8rem; margin-top: 4px;">Face Absent: <strong>${data.face_absence_count}</strong></span>
                            <span style="display: block; font-size: 0.8rem;">Focus Lost: <strong>${data.browser_focus_loss_count}</strong></span>
                            <span style="display: block; font-size: 0.8rem;">Multiple Faces: <strong>${data.multiple_face_count}</strong></span>
                            <span style="display: block; font-size: 0.8rem;">Presence: <strong>${data.face_presence_ratio}%</strong></span>
                        </div>
                    </div>

                    <div class="modal-section-title" style="margin-top: 1.5rem;">
                        <i class="fa-solid fa-list-check"></i> Examination Event Timeline (${data.total_suspicious_events} events)
                    </div>
                    <div class="modal-timeline-container">
                        ${timelineHtml}
                    </div>

                    ${proofsHtml}
                `;
            }
        })
        .catch(err => {
            console.error(err);
            if (bodyEl) bodyEl.innerHTML = `<div class="empty-state"><p>Error connecting to server.</p></div>`;
        });
}

function closeSessionModal() {
    const modal = document.getElementById("sessionDetailsModal");
    if (modal) modal.style.display = "none";
}

function openEvidenceViewer(imgUrl, candidateId, caption) {
    const modal = document.getElementById("evidenceViewerModal");
    const img = document.getElementById("evidenceModalImg");
    const title = document.getElementById("evidenceModalTitle");
    const sub = document.getElementById("evidenceModalSub");
    const info = document.getElementById("evidenceEventInfo");
    const downloadLink = document.getElementById("evidenceDownloadLink");

    if (!modal) return;

    modal.style.display = "flex";
    if (img) img.src = imgUrl;
    if (title) title.innerText = `Evidence: Candidate ${candidateId}`;
    if (sub) sub.innerText = caption || "Live Proctoring Snapshot";
    if (info) info.innerHTML = `<i class="fa-solid fa-camera"></i> ${caption || 'Captured during examination'}`;
    if (downloadLink) downloadLink.href = imgUrl;
}

function closeEvidenceViewer() {
    const modal = document.getElementById("evidenceViewerModal");
    if (modal) modal.style.display = "none";
}
