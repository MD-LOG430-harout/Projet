USE lignes_services;

CREATE TABLE IF NOT EXISTS service_lines (
  line_id CHAR(36) PRIMARY KEY,
  customer_id CHAR(36) NOT NULL,
  offer_id VARCHAR(80) NOT NULL,
  msisdn VARCHAR(32) NOT NULL,
  sim_type VARCHAR(10) NOT NULL,
  sim_identifier VARCHAR(80) NOT NULL,
  imsi VARCHAR(32) NOT NULL,
  supi VARCHAR(48) NOT NULL,
  status VARCHAR(40) NOT NULL,
  hlr_status VARCHAR(40) NOT NULL,
  failure_reason VARCHAR(255) NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uq_lines_msisdn (msisdn),
  UNIQUE KEY uq_lines_sim_identifier (sim_identifier),
  UNIQUE KEY uq_lines_imsi (imsi),
  KEY idx_lines_customer (customer_id),
  KEY idx_lines_status (status)
);
