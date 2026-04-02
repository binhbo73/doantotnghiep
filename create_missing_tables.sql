-- Create async_tasks table
CREATE TABLE async_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_type VARCHAR(100) NOT NULL CHECK(task_type IN ('EMBED_CHUNK', 'SYNC_QDRANT', 'INDEX_DOCUMENT', 'CLEANUP', 'REGENERATE_CACHE')),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_id UUID REFERENCES document_chunks(id) ON DELETE SET NULL,
    payload JSONB NOT NULL DEFAULT '{}',
    status VARCHAR(50) NOT NULL DEFAULT 'pending' CHECK(status IN ('pending', 'running', 'completed', 'failed', 'retrying', 'cancelled')),
    priority VARCHAR(20) NOT NULL DEFAULT 'normal' CHECK(priority IN ('high', 'normal', 'low')),
    retry_count INTEGER NOT NULL DEFAULT 0,
    max_retries INTEGER NOT NULL DEFAULT 3,
    scheduled_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP NULL,
    completed_at TIMESTAMP NULL,
    failed_reason TEXT NULL,
    worker_id VARCHAR(100) NULL,
    backoff_multiplier FLOAT DEFAULT 2.0,
    next_retry_at TIMESTAMP NULL,
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP NULL
);

CREATE INDEX idx_async_tasks_status ON async_tasks(status, priority DESC) WHERE status IN ('pending', 'retrying');
CREATE INDEX idx_async_tasks_document ON async_tasks(document_id, status) WHERE is_deleted = FALSE;
CREATE INDEX idx_async_tasks_chunk ON async_tasks(chunk_id) WHERE chunk_id IS NOT NULL AND is_deleted = FALSE;
CREATE INDEX idx_async_tasks_retry ON async_tasks(next_retry_at, status) WHERE status = 'retrying' AND is_deleted = FALSE;
CREATE INDEX idx_async_tasks_scheduled ON async_tasks(scheduled_at, priority DESC) WHERE status = 'pending' AND is_deleted = FALSE;

-- Create human_feedback table
CREATE TABLE human_feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id UUID NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    account_id UUID NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    rating VARCHAR(50) NOT NULL CHECK (rating IN ('upvote', 'downvote')),
    comment TEXT NULL,
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP NULL,
    UNIQUE(message_id, account_id)
);

CREATE UNIQUE INDEX idx_human_feedback_unique ON human_feedback(message_id, account_id);
CREATE INDEX idx_human_feedback_message_id ON human_feedback(message_id);
CREATE INDEX idx_human_feedback_account_id ON human_feedback(account_id);
CREATE INDEX idx_human_feedback_rating ON human_feedback(rating);

-- Create user_document_cache table
CREATE TABLE user_document_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id UUID NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    max_permission VARCHAR(50) NOT NULL CHECK (max_permission IN ('read', 'write', 'delete')) DEFAULT 'read',
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    cached_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NULL,
    deleted_at TIMESTAMP NULL,
    UNIQUE(account_id, document_id)
);

CREATE INDEX idx_user_doc_cache_unique ON user_document_cache(account_id, document_id);
CREATE INDEX idx_user_doc_cache_account ON user_document_cache(account_id, is_deleted);
CREATE INDEX idx_user_doc_cache_permission ON user_document_cache(max_permission);
CREATE INDEX idx_user_doc_cache_expires ON user_document_cache(expires_at) WHERE is_deleted = FALSE;
CREATE INDEX idx_user_doc_cache_expired_active ON user_document_cache(expires_at, is_deleted) WHERE expires_at < CURRENT_TIMESTAMP AND is_deleted = FALSE;
