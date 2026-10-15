#ifndef FRAUD_EVALUATOR_H
#define FRAUD_EVALUATOR_H

#include <string>
#include <vector>
#include <cstdint>

#ifdef __cplusplus
extern "C" {
#endif

// Struct for C FFI interoperability with Python ctypes
struct TransactionInput {
    double amount;
    double account_avg_daily_spend;
    double merchant_risk_weight;
    int32_t velocity_60s_count;
    int32_t is_tor_or_proxy;
    int32_t is_new_device;
    double distance_km;
    double time_delta_seconds;
};

struct EvaluationResult {
    double fraud_score; // 0.0 to 100.0
    int32_t decision;   // 0 = APPROVED, 1 = FLAGGED, 2 = BLOCKED
    char primary_rule[64];
    double latency_microseconds;
};

// Exported C functions for Python ctypes integration
double c_evaluate_transaction(
    double amount,
    double account_avg_daily_spend,
    double merchant_risk_weight,
    int32_t velocity_60s_count,
    int32_t is_tor_or_proxy,
    int32_t is_new_device,
    double distance_km,
    double time_delta_seconds,
    char* out_decision,
    char* out_primary_rule
);

void c_batch_evaluate(
    const TransactionInput* inputs,
    EvaluationResult* outputs,
    int32_t count
);

#ifdef __cplusplus
}
#endif

#endif // FRAUD_EVALUATOR_H
