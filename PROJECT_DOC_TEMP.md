# Online Examination Monitoring and Integrity Analytics Platform

## 1. Project Overview

The Online Examination Monitoring and Integrity Analytics Platform is designed to support secure online examinations. The system allows candidates to register, login, start an exam session, and be monitored during the exam.

The platform monitors both face presence and browser activity. If the candidate's face is not detected or the candidate switches away from the exam window, the system records the event in SQLite for later review.

## 2. Technologies Used

- Python
- Flask
- SQLite
- OpenCV
- Haar Cascade Classifier
- HTML
- CSS
- JavaScript
- Faker

## 3. Module Description

### Candidate Registration
The registration module allows candidates to enter their Candidate ID, name, email, and password. The system also captures the candidate photo using OpenCV and stores the photo path in SQLite.

### Candidate Login
The login module verifies the candidate's email and password. After successful login, the candidate is redirected to the dashboard.

### Exam Session Management
The dashboard allows the candidate to start, pause, resume, and end the exam session. Start time, end time, status, and session duration are stored and displayed.

### Face Monitoring
Face Monitoring uses OpenCV and Haar Cascade Classifier to detect whether the candidate's face is visible or not. If the face is not detected, the event is stored in SQLite.

### Browser Activity Monitoring
Browser Activity Monitoring uses JavaScript events such as blur, focus, and visibilitychange to detect tab switching, browser minimization, and focus loss. Browser events are sent to Flask and stored in SQLite.

### Unified Event Logging
All monitoring events are stored in the same event_logs table. This includes Face Not Detected, Browser Focus Lost, and Browser Focus Regained events.

### Real-Time Monitoring Dashboard
The dashboard displays candidate name, candidate ID, face status, browser status, face absence count, browser focus loss count, current date and time, and session timer.

## 4. Database Schema

### candidates Table
Stores candidate details.

Fields:
- candidate_id
- name
- email
- password
- photo_path

### exam_sessions Table
Stores exam session details.

Fields:
- session_id
- candidate_id
- start_time
- end_time
- status

### event_logs Table
Stores monitoring events.

Fields:
- event_id
- candidate_id
- event_type
- timestamp
- remarks

## 5. Complete Workflow

Registration
↓
Login
↓
Dashboard
↓
Start Exam
↓
Face Monitoring Starts
↓
Browser Activity Monitoring Starts
↓
Events Logged in SQLite
↓
Session Ends

## 6. Challenges Faced

- Managing webcam access with OpenCV.
- Preventing Flask from opening the camera twice by using use_reloader=False.
- Detecting browser tab switch and focus loss using JavaScript.
- Storing both face and browser events in one common Event Log table.
- Making the dashboard update in real time without manual refresh.

## 7. Future Improvements

- Add session-wise event tracking using session_id.
- Add admin dashboard for reviewing candidate activity.
- Generate AI-based integrity reports.
- Add risk score based on suspicious events.
- Add face recognition to compare live face with registered photo.
- Add charts and analytics for better visualization.