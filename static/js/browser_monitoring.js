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
          console.log(data);
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

        if(data.success){

            setText("face-status", data.face_status);

            setText("browser-status", data.browser_status);

            setText("face-absence-count", data.face_absence_count);

            setText("focus-loss-count", data.browser_focus_loss_count);

            setText("current-date-time", data.current_datetime);

            setText("session-timer", data.session_timer);
            setText("integrity-score", data.integrity_score);

        }

    })
    .catch(error => {
        console.log(error);
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