let browserInactive = false;

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
                setText("monitor-candidate-name", data.candidate_name);
                setText("monitor-candidate-id", data.candidate_id);
                setText("face-status", data.face_status);
                setText("browser-status", data.browser_status);
                setText("face-absence-count", data.face_absence_count);
                setText("focus-loss-count", data.browser_focus_loss_count);
                setText("last-focus-loss-time", data.last_focus_loss_time);
                setText("current-date-time", data.current_datetime);
                setText("session-timer", data.session_timer);
            }
        })
        .catch(error => {
            console.log("Real-time dashboard error:", error);
        });
}

window.addEventListener("blur", function () {
    markBrowserInactive("Candidate switched away from the examination window.");
});

window.addEventListener("focus", function () {
    markBrowserActive("Candidate returned to the examination window.");
});

document.addEventListener("visibilitychange", function () {
    if (document.hidden) {
        markBrowserInactive("Candidate switched to another tab or minimized the browser.");
    } else {
        markBrowserActive("Candidate returned to the examination tab.");
    }
});

loadMonitoringStatus();

setInterval(loadMonitoringStatus, 2000);