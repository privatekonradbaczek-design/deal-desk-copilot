-- ─────────────────────────────────────────────
-- Deal Desk Copilot — PostgreSQL Initialization
-- ─────────────────────────────────────────────

-- Extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- ── Documents ─────────────────────────────────

CREATE TABLE IF NOT EXISTS documents (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id       VARCHAR(255) NOT NULL,
    filename        VARCHAR(500) NOT NULL,
    content_type    VARCHAR(100) NOT NULL,
    file_size_bytes BIGINT NOT NULL,
    storage_path    TEXT NOT NULL,
    status          VARCHAR(50) NOT NULL DEFAULT 'uploaded',
    uploaded_by     VARCHAR(255) NOT NULL,
    uploaded_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    page_count      INT,
    chunk_count     INT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS documents_tenant_id_idx ON documents(tenant_id);
CREATE INDEX IF NOT EXISTS documents_status_idx ON documents(status);
CREATE INDEX IF NOT EXISTS documents_uploaded_at_idx ON documents(uploaded_at DESC);

-- ── Document Chunks + Embeddings ──────────────

CREATE TABLE IF NOT EXISTS document_chunks (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id     UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    tenant_id       VARCHAR(255) NOT NULL,
    content         TEXT NOT NULL,
    page_number     INT,
    chunk_index     INT NOT NULL,
    token_count     INT NOT NULL,
    embedding_model VARCHAR(100) NOT NULL,
    embedding       vector(1536),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- HNSW index for approximate nearest neighbor search
CREATE INDEX IF NOT EXISTS document_chunks_embedding_hnsw_idx
    ON document_chunks
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

CREATE INDEX IF NOT EXISTS document_chunks_document_id_idx ON document_chunks(document_id);
CREATE INDEX IF NOT EXISTS document_chunks_tenant_id_idx ON document_chunks(tenant_id);

-- ── Audit Log (append-only) ───────────────────

CREATE TABLE IF NOT EXISTS audit_log (
    id              BIGSERIAL PRIMARY KEY,
    event_id        UUID NOT NULL UNIQUE,
    correlation_id  UUID NOT NULL,
    timestamp_utc   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    service         VARCHAR(100) NOT NULL,
    event_type      VARCHAR(200) NOT NULL,
    actor_id        VARCHAR(200),
    tenant_id       VARCHAR(255),
    resource_type   VARCHAR(100),
    resource_id     UUID,
    payload_hash    VARCHAR(64) NOT NULL,
    payload         JSONB NOT NULL,
    model_id        VARCHAR(100),
    record_hash     VARCHAR(64) NOT NULL
);

CREATE INDEX IF NOT EXISTS audit_log_correlation_id_idx ON audit_log(correlation_id);
CREATE INDEX IF NOT EXISTS audit_log_tenant_id_idx ON audit_log(tenant_id);
CREATE INDEX IF NOT EXISTS audit_log_event_type_idx ON audit_log(event_type);
CREATE INDEX IF NOT EXISTS audit_log_timestamp_idx ON audit_log(timestamp_utc DESC);

-- ── Idempotency Table ─────────────────────────

CREATE TABLE IF NOT EXISTS processed_events (
    event_id        UUID NOT NULL,
    consumer_group  VARCHAR(200) NOT NULL,
    processed_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (event_id, consumer_group)
);

CREATE INDEX IF NOT EXISTS processed_events_processed_at_idx
    ON processed_events(processed_at DESC);

-- ── Agent Sessions ────────────────────────────

CREATE TABLE IF NOT EXISTS agent_sessions (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id       VARCHAR(255) NOT NULL,
    user_id         VARCHAR(255) NOT NULL,
    correlation_id  UUID NOT NULL,
    status          VARCHAR(50) NOT NULL DEFAULT 'active',
    state_snapshot  JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS agent_sessions_tenant_id_idx ON agent_sessions(tenant_id);
CREATE INDEX IF NOT EXISTS agent_sessions_correlation_id_idx ON agent_sessions(correlation_id);
