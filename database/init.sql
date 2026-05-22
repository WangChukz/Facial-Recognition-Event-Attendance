-- Event Face Attendance — PostgreSQL schema
-- ERD (ASCII):
--   users 1---* face_embeddings
--   users 1---* attendance_logs
--   events 1---* event_sessions
--   events 1---* attendance_logs
--   event_sessions 1---* attendance_logs (optional link)
--   users *---* events (via attendance_logs)

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TYPE user_role AS ENUM ('admin', 'staff', 'student');
CREATE TYPE attendance_direction AS ENUM ('check_in', 'check_out');

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    role user_role NOT NULL DEFAULT 'student',
    student_code VARCHAR(64) UNIQUE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    location VARCHAR(255),
    starts_at TIMESTAMPTZ,
    ends_at TIMESTAMPTZ,
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE event_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_id UUID NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    name VARCHAR(128) DEFAULT 'default',
    opened_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    closed_at TIMESTAMPTZ
);

CREATE TABLE face_embeddings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    faiss_id BIGINT UNIQUE NOT NULL,
    embedding_dim INT NOT NULL DEFAULT 512,
    model_name VARCHAR(64) NOT NULL DEFAULT 'buffalo_l',
    is_primary BOOLEAN NOT NULL DEFAULT TRUE,
    image_path VARCHAR(512),
    embedding_vector BYTEA NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE attendance_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    event_id UUID NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    session_id UUID REFERENCES event_sessions(id) ON DELETE SET NULL,
    direction attendance_direction NOT NULL,
    similarity DOUBLE PRECISION,
    source VARCHAR(32) NOT NULL DEFAULT 'webcam',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_attendance_user_time ON attendance_logs(user_id, created_at DESC);
CREATE INDEX idx_attendance_event_time ON attendance_logs(event_id, created_at DESC);
CREATE INDEX idx_face_embeddings_user ON face_embeddings(user_id);
