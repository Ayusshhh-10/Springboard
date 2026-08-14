// Configuration parameters matching config.py
const MAX_VERIFICATION_ATTEMPTS = 3;
const VERIFICATION_TOTAL_FRAMES = 8;
const VERIFICATION_REQUIRED_FRAMES = 5;

let stream = null;
let currentAttempt = 0;
let isVerifying = false;

const cameraPreview = document.getElementById("cameraPreview");
const captureCanvas = document.getElementById("captureCanvas");
const verifyBtn = document.getElementById("verifyBtn");
const startExamForm = document.getElementById("startExamForm");
const statusTitle = document.getElementById("statusTitle");
const statusDesc = document.getElementById("statusDesc");
const statusBox = document.getElementById("statusBox");
const retryBadgeContainer = document.getElementById("retryBadgeContainer");
const guidelineText = document.getElementById("guidelineText");

// Initialize camera stream
async function initCamera() {
    try {
        stream = await navigator.mediaDevices.getUserMedia({
            video: { width: 640, height: 480 }
        });
        cameraPreview.srcObject = stream;
        updateStatus("waiting", "Waiting", "Position your face in front of the camera and click Verify My Face.");
        verifyBtn.disabled = false;
    } catch (error) {
        console.error("Camera startup failed:", error);
        updateStatus("failure", "Camera Unavailable", "Unable to access the webcam. Ensure the camera is connected and permissions are granted.");
        verifyBtn.disabled = true;
    }
}

function updateStatus(state, title, description) {
    statusTitle.innerText = title;
    statusDesc.innerText = description;
    
    // Reset status classes
    statusTitle.className = "status-title";
    if (state === "waiting") {
        statusTitle.classList.add("status-waiting");
    } else if (state === "verifying") {
        statusTitle.classList.add("status-verifying");
    } else if (state === "success") {
        statusTitle.classList.add("status-success");
    } else if (state === "failure") {
        statusTitle.classList.add("status-failure");
    }
}

function updateRetryBadge() {
    if (currentAttempt > 0) {
        retryBadgeContainer.innerHTML = `<span class="retry-badge">Attempt ${currentAttempt} / ${MAX_VERIFICATION_ATTEMPTS} Failed</span>`;
    } else {
        retryBadgeContainer.innerHTML = "";
    }
}

function stopCamera() {
    if (stream) {
        stream.getTracks().forEach(track => track.stop());
        cameraPreview.style.display = "none";
        document.getElementById("faceOverlay").style.display = "none";
    }
}

async function verifyFace() {
    if (isVerifying) return;
    
    isVerifying = true;
    verifyBtn.disabled = true;
    updateStatus("verifying", "Verifying", "Verifying identity... Please hold still.");
    
    let matchingFramesCount = 0;
    let validFramesCount = 0;
    let errorMessage = null;

    // Capture and analyze frames sequentially
    for (let f = 1; f <= VERIFICATION_TOTAL_FRAMES; f++) {
        updateStatus("verifying", "Verifying", `Verifying identity... (Analyzing frame ${f} of ${VERIFICATION_TOTAL_FRAMES})`);
        
        try {
            const frameData = captureFrame();
            const response = await sendFrameToServer(frameData);
            
            if (response.success) {
                validFramesCount++;
                if (response.matched) {
                    matchingFramesCount++;
                }
            } else {
                // If it's a validation error (like no face or multiple faces), capture the latest one
                errorMessage = response.message;
            }
        } catch (error) {
            console.error("Frame transmission failed:", error);
        }
        
        // Wait 350ms before capturing the next frame
        await new Promise(resolve => setTimeout(resolve, 350));
    }
    
    // Evaluate match decision
    const isSuccessful = (matchingFramesCount >= VERIFICATION_REQUIRED_FRAMES);
    currentAttempt++;

    // Notify backend of verification completion
    try {
        const finalRes = await fetch("/complete-verification", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                status: isSuccessful ? "success" : "failed",
                attempts: currentAttempt
            })
        });
        const finalData = await finalRes.json();
        if (!finalData.success) {
            console.error("Failed to sync verification completion with server");
        }
    } catch (e) {
        console.error("Sync error:", e);
    }

    isVerifying = false;

    if (isSuccessful) {
        stopCamera();
        updateStatus("success", "✓ Identity Verified", "Identity verified successfully.");
        guidelineText.innerText = "Verification complete. You can now start your examination.";
        retryBadgeContainer.innerHTML = "";
        verifyBtn.style.display = "none";
        startExamForm.style.display = "block";
    } else {
        updateRetryBadge();
        
        if (currentAttempt >= MAX_VERIFICATION_ATTEMPTS) {
            stopCamera();
            updateStatus("failure", "✗ Identity Verification Locked", "Identity verification could not be completed. Please contact the administrator.");
            guidelineText.innerText = "Maximum attempts exceeded.";
            verifyBtn.style.display = "none";
        } else {
            // Provide context on what failed (e.g. multiple faces or mismatch)
            let failText = "Identity verification failed. Please position your face clearly and try again.";
            if (errorMessage) {
                if (errorMessage.includes("No face detected") || errorMessage.includes("Face not detected")) {
                    failText = "No face detected. Please position your face in the camera.";
                } else if (errorMessage.includes("Multiple faces")) {
                    failText = "Multiple faces detected. Only one person should be visible.";
                } else if (errorMessage.includes("Unable to recognize") || errorMessage.includes("embedding") || errorMessage.includes("failed on candidate")) {
                    failText = "Unable to recognize the face. Please improve lighting and try again.";
                } else {
                    failText = errorMessage;
                }
            }
            
            updateStatus("failure", "✗ Identity Verification Failed", failText);
            verifyBtn.innerHTML = "<i class='fa-solid fa-arrows-rotate' style='margin-right: 8px;'></i>Try Again";
            verifyBtn.disabled = false;
        }
    }
}

function captureFrame() {
    const context = captureCanvas.getContext("2d");
    captureCanvas.width = cameraPreview.videoWidth || 640;
    captureCanvas.height = cameraPreview.videoHeight || 480;
    
    // Draw current video frame to canvas
    context.drawImage(cameraPreview, 0, 0, captureCanvas.width, captureCanvas.height);
    
    // Convert to base64 Data URL
    return captureCanvas.toDataURL("image/jpeg", 0.8);
}

async function sendFrameToServer(base64Image) {
    const response = await fetch("/verify-face-frame", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ image: base64Image })
    });
    return await response.json();
}

verifyBtn.addEventListener("click", verifyFace);

// Start camera preview on load
window.addEventListener("DOMContentLoaded", initCamera);
