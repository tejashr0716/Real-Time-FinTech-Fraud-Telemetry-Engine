import pytest
from app.services.cpp_engine import cpp_engine

def test_cpp_engine_is_accelerated():
    assert cpp_engine.is_loaded is True

def test_normal_low_risk_transaction_approved():
    score, decision, rule, lat_us, c_acc = cpp_engine.evaluate(
        amount=120.0,
        account_avg_daily_spend=450.0,
        merchant_risk_weight=1.0,
        velocity_60s_count=0,
        is_tor_or_proxy=False,
        is_new_device=False,
        distance_km=5.0,
        time_delta_seconds=7200.0
    )
    assert decision == "APPROVED"
    assert score < 25.0
    assert c_acc is True
    assert lat_us < 1000.0 # Sub-millisecond

def test_tor_proxy_attack_blocked():
    score, decision, rule, lat_us, c_acc = cpp_engine.evaluate(
        amount=500.0,
        account_avg_daily_spend=450.0,
        merchant_risk_weight=1.2,
        velocity_60s_count=0,
        is_tor_or_proxy=True,
        is_new_device=False,
        distance_km=0.0,
        time_delta_seconds=3600.0
    )
    assert score >= 60.0
    assert rule == "TOR_OR_ANON_PROXY"

def test_impossible_geographic_travel_velocity():
    # 2,000 km in 300 seconds = 24,000 km/h (Supersonic Impossible Speed)
    score, decision, rule, lat_us, c_acc = cpp_engine.evaluate(
        amount=1500.0,
        account_avg_daily_spend=500.0,
        merchant_risk_weight=1.0,
        velocity_60s_count=0,
        is_tor_or_proxy=False,
        is_new_device=False,
        distance_km=2000.0,
        time_delta_seconds=300.0
    )
    assert decision == "BLOCKED"
    assert rule == "IMPOSSIBLE_TRAVEL_VELOCITY"
    assert score >= 70.0

def test_micro_deposit_card_testing_detection():
    # $1.50 charged repeatedly with high velocity
    score, decision, rule, lat_us, c_acc = cpp_engine.evaluate(
        amount=1.50,
        account_avg_daily_spend=400.0,
        merchant_risk_weight=1.0,
        velocity_60s_count=3,
        is_tor_or_proxy=False,
        is_new_device=False,
        distance_km=0.0,
        time_delta_seconds=3600.0
    )
    assert rule == "MICRO_DEPOSIT_CARD_TESTING"
    assert score >= 45.0
