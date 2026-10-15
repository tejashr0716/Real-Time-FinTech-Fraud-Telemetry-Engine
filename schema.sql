-- ============================================================================
-- Real-Time FinTech Fraud Telemetry & Stream Ingestion Engine
-- Database Schema & Enterprise Seed Data (PostgreSQL 14+ / Azure SQL compatible)
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

DROP TABLE IF EXISTS telemetry_stream_metrics CASCADE;
DROP TABLE IF EXISTS fraud_audit_ledger CASCADE;
DROP TABLE IF EXISTS transactions CASCADE;
DROP TABLE IF EXISTS merchants CASCADE;
DROP TABLE IF EXISTS accounts CASCADE;

-- ----------------------------------------------------------------------------
-- 1. ACCOUNTS: Customer Wallets & Dynamic Risk Baselines
-- ----------------------------------------------------------------------------
CREATE TABLE accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_number VARCHAR(32) UNIQUE NOT NULL,
    owner_name VARCHAR(128) NOT NULL,
    email VARCHAR(255) NOT NULL,
    balance NUMERIC(16, 2) NOT NULL DEFAULT 50000.00 CHECK (balance >= 0),
    currency VARCHAR(8) NOT NULL DEFAULT 'USD',
    avg_daily_spend NUMERIC(16, 2) NOT NULL DEFAULT 500.00,
    risk_score NUMERIC(5, 2) NOT NULL DEFAULT 12.50 CHECK (risk_score >= 0 AND risk_score <= 100),
    status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE'
        CHECK (status IN ('ACTIVE', 'RESTRICTED', 'FROZEN', 'UNDER_AUDIT')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ----------------------------------------------------------------------------
-- 2. MERCHANTS: Processing Profiles & Category Risk Multipliers
-- ----------------------------------------------------------------------------
CREATE TABLE merchants (
    id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    category VARCHAR(64) NOT NULL,
    mcc_code VARCHAR(8) NOT NULL,
    default_risk_weight NUMERIC(4, 2) NOT NULL DEFAULT 1.0 CHECK (default_risk_weight >= 0.5),
    country VARCHAR(4) NOT NULL DEFAULT 'US',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ----------------------------------------------------------------------------
-- 3. TRANSACTIONS: High-Frequency Authorized / Flagged Ledger
-- ----------------------------------------------------------------------------
CREATE TABLE transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id UUID NOT NULL REFERENCES accounts(id) ON DELETE RESTRICT,
    merchant_id VARCHAR(64) NOT NULL REFERENCES merchants(id) ON DELETE RESTRICT,
    amount NUMERIC(16, 2) NOT NULL CHECK (amount > 0),
    currency VARCHAR(8) NOT NULL DEFAULT 'USD',
    channel VARCHAR(32) NOT NULL DEFAULT 'ONLINE'
        CHECK (channel IN ('ONLINE', 'POS', 'ATM', 'WIRE', 'CRYPTO_ONRAMP')),
    ip_address VARCHAR(45) NOT NULL,
    device_fingerprint VARCHAR(64) NOT NULL,
    geo_country VARCHAR(4) NOT NULL,
    geo_city VARCHAR(64) NOT NULL,
    fraud_score NUMERIC(5, 2) NOT NULL DEFAULT 0.0 CHECK (fraud_score >= 0 AND fraud_score <= 100),
    decision VARCHAR(32) NOT NULL DEFAULT 'APPROVED'
        CHECK (decision IN ('APPROVED', 'FLAGGED', 'BLOCKED')),
    rules_triggered TEXT[] DEFAULT ARRAY[]::TEXT[],
    eval_latency_ms NUMERIC(8, 3) NOT NULL DEFAULT 1.15,
    idempotency_key VARCHAR(128) UNIQUE NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_tx_account_created ON transactions (account_id, created_at DESC);
CREATE INDEX idx_tx_fingerprint ON transactions (device_fingerprint);
CREATE INDEX idx_tx_decision ON transactions (decision);
CREATE INDEX idx_tx_ip ON transactions (ip_address);

-- ----------------------------------------------------------------------------
-- 4. FRAUD AUDIT LEDGER: Immutable Regulatory Event Stream
-- ----------------------------------------------------------------------------
CREATE TABLE fraud_audit_ledger (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transaction_id UUID NOT NULL REFERENCES transactions(id) ON DELETE CASCADE,
    account_id UUID NOT NULL,
    action_taken VARCHAR(64) NOT NULL,
    risk_factors JSONB NOT NULL,
    investigated_by VARCHAR(64) NOT NULL DEFAULT 'AI_STREAM_DEFENDER',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_audit_tx ON fraud_audit_ledger (transaction_id);

-- ----------------------------------------------------------------------------
-- 5. TELEMETRY STREAM METRICS: Performance & Throughput Monitoring
-- ----------------------------------------------------------------------------
CREATE TABLE telemetry_stream_metrics (
    id BIGSERIAL PRIMARY KEY,
    tps NUMERIC(10, 2) NOT NULL DEFAULT 0.0,
    p50_latency_ms NUMERIC(8, 3) NOT NULL DEFAULT 0.0,
    p95_latency_ms NUMERIC(8, 3) NOT NULL DEFAULT 0.0,
    p99_latency_ms NUMERIC(8, 3) NOT NULL DEFAULT 0.0,
    fraud_block_rate NUMERIC(5, 2) NOT NULL DEFAULT 0.0,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================================
-- SEED DATA: High-Value Verified Accounts & Risk-Tiered Merchants
-- ============================================================================

INSERT INTO accounts (id, account_number, owner_name, email, balance, avg_daily_spend, risk_score, status) VALUES
('b0000001-0000-0000-0000-000000000001', 'ACC-84920194', 'Alexander Wright', 'alex.wright@quantum-capital.com', 250000.00, 1800.00, 8.5, 'ACTIVE'),
('b0000002-0000-0000-0000-000000000002', 'ACC-73819203', 'Victoria Sterling', 'v.sterling@meridian-partners.co', 140000.00, 950.00, 11.0, 'ACTIVE'),
('b0000003-0000-0000-0000-000000000003', 'ACC-49102934', 'Devon Thorne', 'devon.thorne@apex-fund.ch', 420000.00, 3200.00, 14.2, 'ACTIVE'),
('b0000004-0000-0000-0000-000000000004', 'ACC-10293847', 'Kaito Tanaka', 'tanaka.k@neo-tokyo-ventures.jp', 89000.00, 620.00, 9.8, 'ACTIVE'),
('b0000005-0000-0000-0000-000000000005', 'ACC-99812734', 'Compromised Test Account', 'compromised@sandbox-audit.io', 12500.00, 200.00, 78.5, 'UNDER_AUDIT');

INSERT INTO merchants (id, name, category, mcc_code, default_risk_weight, country) VALUES
('mer_apple_pay_direct', 'Apple Global Online Store', 'Consumer Electronics', '5732', 1.00, 'US'),
('mer_binance_fiat_bridge', 'Binance Instant Fiat Ramp', 'Crypto Exchange', '6051', 2.85, 'MT'),
('mer_emirates_air_first', 'Emirates First Class Desk', 'Aviation / Travel', '3008', 1.40, 'AE'),
('mer_harrods_knightsbridge', 'Harrods Knightsbridge Retail', 'Luxury Department Store', '5311', 1.25, 'GB'),
('mer_cloud_compute_aws', 'AWS Cloud Infrastructure Services', 'Cloud Computing', '7372', 1.00, 'US'),
('mer_darknet_card_test', 'Shady VPN Testing Gateway', 'High Risk Foreign Gateway', '7995', 4.50, 'RU');

INSERT INTO transactions (
    id, account_id, merchant_id, amount, currency, channel, ip_address, device_fingerprint,
    geo_country, geo_city, fraud_score, decision, rules_triggered, eval_latency_ms, idempotency_key, created_at
) VALUES
('c0000001-0000-0000-0000-000000000001', 'b0000001-0000-0000-0000-000000000001', 'mer_apple_pay_direct', 2899.00, 'USD', 'ONLINE', '198.51.100.24', 'fp_macbook_pro_m3_98f1', 'US', 'New York', 12.0, 'APPROVED', ARRAY['KNOWN_DEVICE_MATCH'], 1.25, 'TX-IDEM-000001', NOW() - INTERVAL '20 minutes'),
('c0000002-0000-0000-0000-000000000002', 'b0000002-0000-0000-0000-000000000002', 'mer_harrods_knightsbridge', 4500.00, 'USD', 'POS', '185.12.34.89', 'fp_iphone_16_promax_21a4', 'GB', 'London', 18.5, 'APPROVED', ARRAY['MERCHANT_REPUTATION_HIGH'], 1.08, 'TX-IDEM-000002', NOW() - INTERVAL '15 minutes'),
('c0000003-0000-0000-0000-000000000003', 'b0000005-0000-0000-0000-000000000005', 'mer_binance_fiat_bridge', 9800.00, 'USD', 'CRYPTO_ONRAMP', '91.200.12.44', 'fp_tor_exit_node_77c2', 'RU', 'Moscow', 94.5, 'BLOCKED', ARRAY['IMPOSSIBLE_TRAVEL_VELOCITY', 'HIGH_RISK_CRYPTO_MCC', 'TOR_EXIT_NODE'], 0.94, 'TX-IDEM-000003', NOW() - INTERVAL '3 minutes');
