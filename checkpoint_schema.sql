USE etl_practice;

CREATE TABLE IF NOT EXISTS etl_checkpoints (
    job_name VARCHAR(100) PRIMARY KEY,
    last_row_number INT UNSIGNED NOT NULL DEFAULT 0
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS etl_rejections (
    job_name VARCHAR(100) NOT NULL,
    source_row_number INT UNSIGNED NOT NULL,
    raw_data JSON NOT NULL,
    reasons JSON NOT NULL,
    PRIMARY KEY (job_name, source_row_number)
) ENGINE=InnoDB;

INSERT INTO etl_checkpoints (job_name, last_row_number)
SELECT 'posts_100_v1', 0
WHERE NOT EXISTS (
    SELECT 1
    FROM etl_checkpoints
    WHERE job_name = 'posts_100_v1'
);