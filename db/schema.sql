CREATE TABLE IF NOT EXISTS oauth_states (
    state TEXT PRIMARY KEY,
    expires_at REAL
);

CREATE TABLE IF NOT EXISTS user_sessions (
    session_id TEXT PRIMARY KEY,
    access_token TEXT,
    refresh_token TEXT,
    expires_at REAL,
    created_at REAL
);
