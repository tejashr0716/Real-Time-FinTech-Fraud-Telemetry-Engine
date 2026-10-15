#include "fraud_evaluator.h"
#include <chrono>
#include <cmath>
#include <cstring>
#include <algorithm>

namespace {

inline double compute_fraud_score(
    double amount,
    double account_avg_daily_spend,
    double merchant_risk_weight,
    int32_t velocity_60s_count,
    int32_t is_tor_or_proxy,
    int32_t is_new_device,
    double distance_km,
    double time_delta_seconds,
    std::string& primary_rule
) {
    double score = 5.0; // Baseline normal risk
    primary_rule = "BASELINE_CLEAR";

    // 1. Critical Rule: TOR / Anonymous Proxy Gateway (+50 points)
    if (is_tor_or_proxy) {
        score += 55.0;
        primary_rule = "TOR_OR_ANON_PROXY";
    }

    // 2. Critical Rule: Impossible Geographic Travel Velocity (> 900 km/h)
    if (time_delta_seconds > 0.0 && distance_km > 100.0) {
        double speed_kmh = (distance_km / time_delta_seconds) * 3600.0;
        if (speed_kmh > 950.0) {
            score += 75.0;
            primary_rule = "IMPOSSIBLE_TRAVEL_VELOCITY";
        } else if (speed_kmh > 500.0) {
            score += 30.0;
            if (primary_rule == "BASELINE_CLEAR") primary_rule = "SUSPICIOUS_FLIGHT_VELOCITY";
        }
    }

    // 3. Velocity Spike: Too many transactions in 60-second window
    if (velocity_60s_count >= 5) {
        score += 45.0;
        if (primary_rule == "BASELINE_CLEAR") primary_rule = "CARD_VELOCITY_SPIKE";
    } else if (velocity_60s_count >= 3) {
        score += 20.0;
        if (primary_rule == "BASELINE_CLEAR") primary_rule = "BURST_FREQUENCY";
    }

    // 4. Large Deviation from Account Average Daily Spend
    if (account_avg_daily_spend > 0.0) {
        double ratio = amount / account_avg_daily_spend;
        if (ratio > 10.0) {
            score += 35.0;
            if (primary_rule == "BASELINE_CLEAR") primary_rule = "EXTREME_DEVIATION_FROM_AVG";
        } else if (ratio > 4.0) {
            score += 18.0;
            if (primary_rule == "BASELINE_CLEAR") primary_rule = "MODERATE_DEVIATION_FROM_AVG";
        }
    }

    // 5. Merchant Risk Multiplier
    if (merchant_risk_weight > 1.5) {
        score += (merchant_risk_weight - 1.0) * 12.0;
        if (primary_rule == "BASELINE_CLEAR" && merchant_risk_weight >= 2.5) {
            primary_rule = "HIGH_RISK_MERCHANT_MCC";
        }
    }

    // 6. Untrusted / New Device Fingerprint
    if (is_new_device) {
        score += 10.0;
    }

    // 7. Micro-Deposit Card Testing Attack Detection (< $2.00)
    if (amount <= 2.0 && velocity_60s_count >= 2) {
        score += 40.0;
        primary_rule = "MICRO_DEPOSIT_CARD_TESTING";
    }

    return std::min(100.0, std::max(0.0, score));
}

} // anonymous namespace

extern "C" {

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
) {
    std::string rule_str;
    double score = compute_fraud_score(
        amount, account_avg_daily_spend, merchant_risk_weight,
        velocity_60s_count, is_tor_or_proxy, is_new_device,
        distance_km, time_delta_seconds, rule_str
    );

    const char* decision_str = "APPROVED";
    if (score >= 75.0) {
        decision_str = "BLOCKED";
    } else if (score >= 40.0) {
        decision_str = "FLAGGED";
    }

    if (out_decision) {
        std::strncpy(out_decision, decision_str, 31);
        out_decision[31] = '\0';
    }
    if (out_primary_rule) {
        std::strncpy(out_primary_rule, rule_str.c_str(), 63);
        out_primary_rule[63] = '\0';
    }

    return score;
}

void c_batch_evaluate(
    const TransactionInput* inputs,
    EvaluationResult* outputs,
    int32_t count
) {
    for (int32_t i = 0; i < count; ++i) {
        auto t0 = std::chrono::high_resolution_clock::now();

        std::string rule_str;
        double score = compute_fraud_score(
            inputs[i].amount,
            inputs[i].account_avg_daily_spend,
            inputs[i].merchant_risk_weight,
            inputs[i].velocity_60s_count,
            inputs[i].is_tor_or_proxy,
            inputs[i].is_new_device,
            inputs[i].distance_km,
            inputs[i].time_delta_seconds,
            rule_str
        );

        auto t1 = std::chrono::high_resolution_clock::now();
        double latency_us = std::chrono::duration<double, std::micro>(t1 - t0).count();

        outputs[i].fraud_score = score;
        if (score >= 75.0) {
            outputs[i].decision = 2; // BLOCKED
        } else if (score >= 40.0) {
            outputs[i].decision = 1; // FLAGGED
        } else {
            outputs[i].decision = 0; // APPROVED
        }
        std::strncpy(outputs[i].primary_rule, rule_str.c_str(), 63);
        outputs[i].primary_rule[63] = '\0';
        outputs[i].latency_microseconds = latency_us;
    }
}

}
