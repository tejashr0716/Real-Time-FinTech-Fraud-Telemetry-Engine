import os
import ctypes
import time
import logging
from typing import Tuple, List
from app.config import settings

logger = logging.getLogger("cpp_engine")

class CPPEngine:
    def __init__(self):
        self.lib = None
        self.is_loaded = False
        self._load_library()

    def _load_library(self):
        # Search candidate paths for the compiled shared library
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        candidate_paths = [
            settings.CPP_LIB_PATH,
            os.path.join(base_dir, "cpp", "libfraud_evaluator.dylib"),
            os.path.join(base_dir, "cpp", "libfraud_evaluator.so"),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "libfraud_evaluator.dylib"),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "libfraud_evaluator.so"),
        ]

        for path in candidate_paths:
            if path and os.path.exists(path):
                try:
                    self.lib = ctypes.CDLL(path)
                    self._setup_function_signatures()
                    self.is_loaded = True
                    logger.info(f"Loaded C++ Native Fraud Evaluator library from: {path}")
                    return
                except Exception as e:
                    logger.warning(f"Failed to load C++ library at {path}: {e}")

        logger.warning("C++ native shared library not found. Falling back to high-speed Python heuristic engine.")

    def _setup_function_signatures(self):
        # double c_evaluate_transaction(double, double, double, int32, int32, int32, double, double, char*, char*)
        self.lib.c_evaluate_transaction.argtypes = [
            ctypes.c_double, # amount
            ctypes.c_double, # account_avg_daily_spend
            ctypes.c_double, # merchant_risk_weight
            ctypes.c_int32,  # velocity_60s_count
            ctypes.c_int32,  # is_tor_or_proxy
            ctypes.c_int32,  # is_new_device
            ctypes.c_double, # distance_km
            ctypes.c_double, # time_delta_seconds
            ctypes.c_char_p, # out_decision
            ctypes.c_char_p  # out_primary_rule
        ]
        self.lib.c_evaluate_transaction.restype = ctypes.c_double

    def evaluate(
        self,
        amount: float,
        account_avg_daily_spend: float,
        merchant_risk_weight: float,
        velocity_60s_count: int,
        is_tor_or_proxy: bool,
        is_new_device: bool,
        distance_km: float = 0.0,
        time_delta_seconds: float = 3600.0
    ) -> Tuple[float, str, str, float, bool]:
        t0 = time.perf_counter()

        if self.is_loaded:
            out_decision = ctypes.create_string_buffer(32)
            out_rule = ctypes.create_string_buffer(64)

            score = self.lib.c_evaluate_transaction(
                ctypes.c_double(amount),
                ctypes.c_double(account_avg_daily_spend),
                ctypes.c_double(merchant_risk_weight),
                ctypes.c_int32(velocity_60s_count),
                ctypes.c_int32(1 if is_tor_or_proxy else 0),
                ctypes.c_int32(1 if is_new_device else 0),
                ctypes.c_double(distance_km),
                ctypes.c_double(time_delta_seconds),
                out_decision,
                out_rule
            )
            t1 = time.perf_counter()
            latency_us = round((t1 - t0) * 1_000_000.0, 2)
            return round(score, 2), out_decision.value.decode("utf-8"), out_rule.value.decode("utf-8"), latency_us, True

        # Fallback pure-Python heuristic evaluation
        score = 5.0
        primary_rule = "BASELINE_CLEAR"

        if is_tor_or_proxy:
            score += 55.0
            primary_rule = "TOR_OR_ANON_PROXY"

        if time_delta_seconds > 0.0 and distance_km > 100.0:
            speed_kmh = (distance_km / time_delta_seconds) * 3600.0
            if speed_kmh > 950.0:
                score += 65.0
                primary_rule = "IMPOSSIBLE_TRAVEL_VELOCITY"
            elif speed_kmh > 500.0:
                score += 30.0
                if primary_rule == "BASELINE_CLEAR":
                    primary_rule = "SUSPICIOUS_FLIGHT_VELOCITY"

        if velocity_60s_count >= 5:
            score += 45.0
            if primary_rule == "BASELINE_CLEAR":
                primary_rule = "CARD_VELOCITY_SPIKE"
        elif velocity_60s_count >= 3:
            score += 20.0
            if primary_rule == "BASELINE_CLEAR":
                primary_rule = "BURST_FREQUENCY"

        if account_avg_daily_spend > 0.0:
            ratio = amount / account_avg_daily_spend
            if ratio > 10.0:
                score += 35.0
                if primary_rule == "BASELINE_CLEAR":
                    primary_rule = "EXTREME_DEVIATION_FROM_AVG"
            elif ratio > 4.0:
                score += 18.0
                if primary_rule == "BASELINE_CLEAR":
                    primary_rule = "MODERATE_DEVIATION_FROM_AVG"

        if merchant_risk_weight > 1.5:
            score += (merchant_risk_weight - 1.0) * 12.0
            if primary_rule == "BASELINE_CLEAR" and merchant_risk_weight >= 2.5:
                primary_rule = "HIGH_RISK_MERCHANT_MCC"

        if is_new_device:
            score += 10.0

        if amount <= 2.0 and velocity_60s_count >= 2:
            score += 40.0
            primary_rule = "MICRO_DEPOSIT_CARD_TESTING"

        score = min(100.0, max(0.0, score))
        decision = "APPROVED"
        if score >= settings.FRAUD_THRESHOLD_BLOCK:
            decision = "BLOCKED"
        elif score >= settings.FRAUD_THRESHOLD_FLAG:
            decision = "FLAGGED"

        t1 = time.perf_counter()
        latency_us = round((t1 - t0) * 1_000_000.0, 2)
        return round(score, 2), decision, primary_rule, latency_us, False

cpp_engine = CPPEngine()
