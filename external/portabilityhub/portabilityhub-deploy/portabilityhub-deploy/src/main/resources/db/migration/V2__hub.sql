CREATE TABLE hub (
    id        VARCHAR(64)   PRIMARY KEY,
    callback  VARCHAR(2048) NOT NULL,
    query     VARCHAR(512)
);
