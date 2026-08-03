CREATE TABLE portability_order (
    id              VARCHAR(64)  PRIMARY KEY,
    state           VARCHAR(32)  NOT NULL,
    creation_date   TIMESTAMPTZ,
    last_update     TIMESTAMPTZ,
    payload         JSONB        NOT NULL
);

CREATE INDEX idx_po_state ON portability_order (state);
