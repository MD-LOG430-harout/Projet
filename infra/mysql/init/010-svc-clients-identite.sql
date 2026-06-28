USE clients_identite;

CREATE TABLE IF NOT EXISTS customers (
  customer_id CHAR(36) PRIMARY KEY,
  email VARCHAR(255) NOT NULL,
  display_name VARCHAR(160) NOT NULL,
  legal_name VARCHAR(180) NOT NULL,
  address_line1 VARCHAR(255) NOT NULL,
  city VARCHAR(120) NOT NULL,
  province CHAR(2) NOT NULL,
  postal_code VARCHAR(12) NOT NULL,
  identity_document_type VARCHAR(40) NOT NULL,
  identity_document_hash VARCHAR(255) NOT NULL,
  customer_type VARCHAR(40) NOT NULL,
  status VARCHAR(40) NOT NULL,
  identity_status VARCHAR(40) NOT NULL,
  risk_level VARCHAR(40) NOT NULL,
  password_hash VARCHAR(255) NULL,
  failed_login_attempts INT NOT NULL DEFAULT 0,
  locked_until DATETIME NULL,
  last_login_risk VARCHAR(40) NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uq_customers_email (email),
  KEY idx_customers_status (status)
);

CREATE TABLE IF NOT EXISTS mfa_challenges (
  challenge_id CHAR(36) PRIMARY KEY,
  customer_id CHAR(36) NOT NULL,
  otp_hash VARCHAR(255) NOT NULL,
  status VARCHAR(40) NOT NULL,
  expires_at DATETIME NOT NULL,
  verified_at DATETIME NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_mfa_customer FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
  KEY idx_mfa_customer_status (customer_id, status)
);
