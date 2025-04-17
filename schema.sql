-- Drop tables if they already exist
DROP TABLE IF EXISTS tasks;
DROP TABLE IF EXISTS task_results;

-- Create tables
CREATE TABLE tasks (
    task_id TEXT PRIMARY KEY,
    part_number TEXT NOT NULL,
    start_time REAL NOT NULL,
    all_completed BOOLEAN NOT NULL DEFAULT 0,
    completed_count INTEGER NOT NULL DEFAULT 0,
    scrapers TEXT NOT NULL
);

CREATE TABLE task_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL,
    scraper_name TEXT NOT NULL,
    supplier TEXT NOT NULL,
    part_number TEXT NOT NULL,
    success BOOLEAN NOT NULL DEFAULT 0,
    message TEXT,
    time_taken REAL DEFAULT 0,
    completed BOOLEAN NOT NULL DEFAULT 0,
    results_json TEXT,
    FOREIGN KEY (task_id) REFERENCES tasks (task_id)
);