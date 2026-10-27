PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS memories (
 memory_id TEXT PRIMARY KEY,
 workspace_id TEXT NOT NULL CHECK(length(trim(workspace_id))>0),
 scope TEXT NOT NULL CHECK(scope IN ('long_session','long_term')),
 kind TEXT NOT NULL,
 content_json TEXT NOT NULL CHECK(json_valid(content_json)),
 source_ids_json TEXT NOT NULL CHECK(json_valid(source_ids_json)),
 confirmed INTEGER NOT NULL CHECK(confirmed IN (0,1)),
 created_at TEXT NOT NULL, updated_at TEXT NOT NULL, deleted_at TEXT,
 CHECK((scope='long_term' AND confirmed=1 AND json_array_length(source_ids_json)>0)
    OR (scope='long_session' AND confirmed=0))
);
CREATE INDEX IF NOT EXISTS memory_workspace ON memories(workspace_id,scope,deleted_at);
CREATE TABLE IF NOT EXISTS workspace_records (
 record_id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL, kind TEXT NOT NULL,
 content_json TEXT NOT NULL CHECK(json_valid(content_json)), created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS record_workspace ON workspace_records(workspace_id,kind);
