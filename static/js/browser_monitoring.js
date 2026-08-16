let browserInactive = false;
let isEndingExam = false;

function setText(elementId, value) {
    const element = document.getElementById(elementId);

    if (element) {
        element.innerText = value;
    }
}

function sendBrowserEvent(eventType, remarks) {
    fetch("/log-browser-event", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            event_type: eventType,
            remarks: remarks
        }),
        keepalive: true
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            setText("browser-status", data.browser_status);
        }
    })
    .catch(error => {
        console.log("Browser monitoring error:", error);
    });
}

function markBrowserInactive(reason) {
    if (isEndingExam) {
        return;
    }
    if (!browserInactive) {
        browserInactive = true;

        setText("browser-status", "Browser Inactive");

        sendBrowserEvent(
            "Browser Focus Lost",
            reason
        );
    }
}

function markBrowserActive(reason) {
    if (isEndingExam) {
        return;
    }
    if (browserInactive) {
        browserInactive = false;

        setText("browser-status", "Browser Active");

        sendBrowserEvent(
            "Browser Focus Regained",
            reason
        );
    }
}

function loadMonitoringStatus() {
    fetch("/monitoring-status")
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            setText("face-status", data.face_status);
            setText("browser-status", data.browser_status);
            setText("face-absence-count", data.face_absence_count);
            setText("focus-loss-count", data.browser_focus_loss_count);
            setText("multiple-face-count", data.multiple_face_count);
            setText("integrity-score", data.integrity_score);
            setText("face-presence-ratio", data.face_presence_ratio + "%");
            setText("risk-label", data.risk_label);
            setText("current-date-time", data.current_datetime);
            setText("session-timer", data.session_timer);
            setText("integrity-score", data.integrity_score);

            // Update Camera Status
            const cameraStatusEl = document.getElementById("camera-status");
            if (cameraStatusEl) {
                if (data.face_status === "Camera Not Opened" || data.face_status === "Camera Frame Not Read" || data.face_status === "Face Model Not Loaded") {
                    cameraStatusEl.innerText = "Inactive";
                    cameraStatusEl.style.color = "#ef4444"; // red
                } else {
                    cameraStatusEl.innerText = "Active";
                    cameraStatusEl.style.color = "#10b981"; // green
                }
            }

            // Update Faces Detected Count
            const facesDetectedEl = document.getElementById("faces-detected");
            if (facesDetectedEl) {
                if (data.face_status === "Face Detected") {
                    facesDetectedEl.innerText = "1";
                    facesDetectedEl.style.color = "#10b981"; // green
                } else if (data.face_status === "Multiple Faces Detected") {
                    facesDetectedEl.innerText = "2";
                    facesDetectedEl.style.color = "#ef4444"; // red
                } else if (data.face_status === "Face Not Detected") {
                    facesDetectedEl.innerText = "0";
                    facesDetectedEl.style.color = "#f59e0b"; // amber
                } else {
                    facesDetectedEl.innerText = "0";
                    facesDetectedEl.style.color = "";
                }
            }

            const faceStatusEl = document.getElementById("face-status");
            if (faceStatusEl) {
                if (data.face_status === "Face Detected") {
                    faceStatusEl.style.color = "#10b981"; // green
                } else if (data.face_status === "Multiple Faces Detected") {
                    faceStatusEl.style.color = "#ef4444"; // red
                } else if (data.face_status === "Face Not Detected") {
                    faceStatusEl.style.color = "#f59e0b"; // amber
                } else {
                    faceStatusEl.style.color = "";
                }
            }

            const browserStatusEl = document.getElementById("browser-status");
            if (browserStatusEl) {
                if (data.browser_status === "Browser Active") {
                    browserStatusEl.style.color = "#10b981";
                } else {
                    browserStatusEl.style.color = "#ef4444";
                }
            }
        }
    })
    .catch(error => {
        console.log("Monitoring status fetch error:", error);
    });
}

window.addEventListener("blur", function () {
    if (isEndingExam) return;
    markBrowserInactive("Candidate switched away from the examination window.");
});

window.addEventListener("focus", function () {
    if (isEndingExam) return;
    markBrowserActive("Candidate returned to the examination window.");
});

document.addEventListener("visibilitychange", function () {
    if (isEndingExam) return;
    if (document.hidden) {
        markBrowserInactive("Candidate switched to another tab or minimized the browser.");
    } else {
        markBrowserActive("Candidate returned to the examination tab.");
    }
});

const endExamForm = document.getElementById("endExamForm");
if (endExamForm) {
    endExamForm.addEventListener("submit", function (e) {
        isEndingExam = true;
        const confirmed = confirm("Are you sure you want to end the examination? This will finalize your integrity score.");
        if (!confirmed) {
            isEndingExam = false;
            e.preventDefault();
        }
    });
}

loadMonitoringStatus();
setInterval(loadMonitoringStatus, 2000);
