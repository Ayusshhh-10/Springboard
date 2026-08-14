CREATE TABLE IF NOT EXISTS candidates (
    candidate_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,
    photo_path TEXT
);

CREATE TABLE IF NOT EXISTS exam_sessions (
    session_id INTEGER PRIMARY KEY AUTOINCREMENT,
    candidate_id TEXT NOT NULL,
    start_time TEXT,
    end_time TEXT,
    status TEXT,
    integrity_score INTEGER DEFAULT 100,
    identity_verified INTEGER DEFAULT 0,
    verification_time TEXT,
    verification_attempts INTEGER DEFAULT 0,
    FOREIGN KEY (candidate_id) REFERENCES candidates(candidate_id)
);
CREATE TABLE IF NOT EXISTS event_logs (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    candidate_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    remarks TEXT,
    proof_image TEXT,
    penalty INTEGER DEFAULT 0,
    FOREIGN KEY (candidate_id) REFERENCES candidates(candidate_id)
);

CREATE TABLE IF NOT EXISTS student_integrity_scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    candidate_id TEXT NOT NULL,
    name TEXT NOT NULL,
    session_id INTEGER NOT NULL,
    integrity_score INTEGER NOT NULL,
    total_suspicious_events INTEGER NOT NULL,
    proof_image TEXT,
    FOREIGN KEY (candidate_id) REFERENCES candidates(candidate_id),
    FOREIGN KEY (session_id) REFERENCES exam_sessions(session_id)
);