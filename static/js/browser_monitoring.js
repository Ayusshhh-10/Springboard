let browserInactive = false;

function updateBrowserStatus(status, count, lastTime) {
    const statusElement = document.getElementById("browser-status");
    const countElement = document.getElementById("focus-loss-count");
    const lastTimeElement = document.getElementById("last-focus-loss-time");

    if (statusElement) {
        statusElement.innerText = status;
    }

    if (countElement && count !== undefined) {
        countElement.innerText = count;
    }

    if (lastTimeElement && lastTime !== undefined) {
        lastTimeElement.innerText = lastTime;
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
            updateBrowserStatus(
                data.browser_status,
                data.focus_loss_count,
                data.last_focus_loss_time
            );
        }
    })
    .catch(error => {
        console.log("Browser monitoring error:", error);
    });
}

function markBrowserInactive(reason) {
    if (!browserInactive) {
        browserInactive = true;

        updateBrowserStatus(
            "Browser Inactive",
            undefined,
            new Date().toLocaleString()
        );

        sendBrowserEvent(
            "Browser Focus Lost",
            reason
        );
    }
}

function markBrowserActive(reason) {
    if (browserInactive) {
        browserInactive = false;

        updateBrowserStatus(
            "Browser Active",
            undefined,
            undefined
        );

        sendBrowserEvent(
            "Browser Focus Regained",
            reason
        );
    }
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