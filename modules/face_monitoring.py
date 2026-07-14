import cv2
import os
from datetime import datetime


# Create photos folder if it does not exist
PHOTOS_FOLDER = "photos"
os.makedirs(PHOTOS_FOLDER, exist_ok=True)


# Load Haar Cascade face detection model
face_cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
face_cascade = cv2.CascadeClassifier(face_cascade_path)


# Access system webcam
camera = cv2.VideoCapture(0, cv2.CAP_DSHOW)

if not camera.isOpened():
    print("Error: Could not access the webcam.")
    exit()


print("Webcam started successfully.")
print("Press 'c' to capture image.")
print("Press 'q' to quit.")


while True:
    ret, frame = camera.read()

    if not ret:
        print("Error: Could not read video frame.")
        break

    # Convert frame to grayscale for face detection
    gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # Detect faces
    faces = face_cascade.detectMultiScale(
        gray_frame,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(80, 80)
    )

    # If face is detected
    if len(faces) > 0:
        status_text = "Face Detected"
        status_color = (0, 255, 0)

        # Draw bounding boxes around detected faces
        for (x, y, w, h) in faces:
            cv2.rectangle(
                frame,
                (x, y),
                (x + w, y + h),
                status_color,
                2
            )

    else:
        status_text = "Face Not Detected"
        status_color = (0, 0, 255)

    # Display status text on video feed
    cv2.putText(
        frame,
        status_text,
        (30, 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        status_color,
        2
    )

    # Show live video feed
    cv2.imshow("Face Presence Monitoring", frame)

    # Keyboard controls
    key = cv2.waitKey(1) & 0xFF

    if key == ord("c"):
        image_name = f"captured_face_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        image_path = os.path.join(PHOTOS_FOLDER, image_name)

        cv2.imwrite(image_path, frame)
        print(f"Image captured and saved successfully: {image_path}")

    elif key == ord("q"):
        print("Webcam closed successfully.")
        break


# Release webcam and close windows
camera.release()
cv2.destroyAllWindows()