CREATE TABLE IF NOT EXISTS qd_api_keys (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES qd_users(id) ON DELETE CASCADE,
    api_key TEXT NOT NULL UNIQUE,
    key_name VARCHAR(100) DEFAULT 'Default',
    description TEXT DEFAULT '',
    active BOOLEAN DEFAULT TRUE,
    expires_at TIMESTAMP,
    last_used_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_api_keys_user_id ON qd_api_keys(user_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_api_key ON qd_api_keys(api_key);
CREATE INDEX IF NOT EXISTS idx_api_keys_active ON qd_api_keys(active);
CREATE INDEX IF NOT EXISTS idx_api_keys_expires ON qd_api_keys(expires_at) WHERE expires_at IS NOT NULL;
