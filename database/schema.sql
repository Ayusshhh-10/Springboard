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
    FOREIGN KEY (candidate_id) REFERENCES candidates(candidate_id)
);
CREATE TABLE IF NOT EXISTS event_logs (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    candidate_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    remarks TEXT,
    FOREIGN KEY (candidate_id) REFERENCES candidates(candidate_id)
);