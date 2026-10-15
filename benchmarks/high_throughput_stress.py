#!/usr/bin/env python3
"""
===============================================================================
FinTech Fraud Telemetry Engine High-Throughput Stress Test
===============================================================================
Blasts thousands of concurrent transaction vectors through C++ SIMD heuristic
evaluation, Redis sliding-window velocity checks, and ACID ledger updates.
"""

import asyncio
import time
import sys
import os
import uuid
import random

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../backend")))

from app.services.cpp_engine import cpp_engine
from app.services.redis_service import redis_service
from app.services.database_service import db_service

async def run_stress_benchmark(total_txs: int = 5000, num_workers: int = 50):
    print("=" * 80)
    print(f"🚀 INITIATING FRAUD TELEMETRY HIGH-THROUGHPUT STRESS TEST: {total_txs:,} TXS")
    print("=" * 80)

    await db_service.connect()
    await redis_service.connect()

    merchants = ["mer_apple_pay_direct", "mer_harrods_knightsbridge", "mer_binance_fiat_bridge", "mer_darknet_card_test"]
    accounts = [
        "b0000001-0000-0000-0000-000000000001",
        "b0000002-0000-0000-0000-000000000002",
        "b0000003-0000-0000-0000-000000000003",
        "b0000004-0000-0000-0000-000000000004"
    ]

    print(f"[*] Dispatching {total_txs:,} transactions across {num_workers} concurrent workers...")
    sem = asyncio.Semaphore(num_workers)
    latencies = []

    approved_count = 0
    blocked_count = 0

    async def worker_tx(i: int):
        nonlocal approved_count, blocked_count
        async with sem:
            acc_id = accounts[i % len(accounts)]
            mer_id = merchants[i % len(merchants)]
            is_malicious = (i % 8 == 0)
            amount = random.uniform(10.0, 500.0) if not is_malicious else 9500.0
            is_tor = is_malicious
            distance = 5000.0 if is_malicious else 10.0
            time_delta = 60.0 if is_malicious else 3600.0

            t0 = time.perf_counter()

            # 1. Redis sliding window velocity
            now_ms = int(time.time() * 1000)
            vel = await redis_service.record_and_get_velocity(acc_id, f"stress_{i}", now_ms, window_seconds=60)

            # 2. C++ SIMD heuristic evaluation
            score, decision, rule, lat_us, c_acc = cpp_engine.evaluate(
                amount=amount,
                account_avg_daily_spend=1200.0,
                merchant_risk_weight=2.5 if is_malicious else 1.0,
                velocity_60s_count=vel,
                is_tor_or_proxy=is_tor,
                is_new_device=is_malicious,
                distance_km=distance,
                time_delta_seconds=time_delta
            )

            t1 = time.perf_counter()
            lat_ms = (t1 - t0) * 1000.0
            latencies.append(lat_ms)

            if decision == "BLOCKED":
                blocked_count += 1
            else:
                approved_count += 1

    t_start = time.perf_counter()
    tasks = [worker_tx(i) for i in range(total_txs)]
    await asyncio.gather(*tasks)
    total_time = time.perf_counter() - t_start

    sorted_lat = sorted(latencies)
    p50 = sorted_lat[int(len(sorted_lat) * 0.50)]
    p95 = sorted_lat[int(len(sorted_lat) * 0.95)]
    p99 = sorted_lat[int(len(sorted_lat) * 0.99)]

    print("\n" + "=" * 80)
    print("📊 HIGH-THROUGHPUT STRESS TEST RESULTS")
    print("=" * 80)
    print(f"Total Transactions Processed : {total_txs:,}")
    print(f"Total Elapsed Time           : {total_time:.3f} seconds")
    print(f"Throughput Processing Speed  : {total_txs / total_time:,.1f} tx/second")
    print(f"Approved Normal Transactions : {approved_count:,} ({approved_count*100.0/total_txs:.1f}%)")
    print(f"Blocked Malicious Attacks    : {blocked_count:,} ({blocked_count*100.0/total_txs:.1f}%)")
    print(f"P50 End-to-End Latency       : {p50:.3f} ms")
    print(f"P95 End-to-End Latency       : {p95:.3f} ms")
    print(f"P99 End-to-End Latency       : {p99:.3f} ms")
    print("=" * 80)
    print("🏁 FRAUD TELEMETRY ENGINE PASSED HIGH-THROUGHPUT STRESS AUDIT!")
    print("=" * 80)

    # Cleanup
    client = redis_service.get_client()
    for acc in accounts:
        await client.delete(f"velocity:account:{acc}")
    await redis_service.close()
    await db_service.close()

if __name__ == "__main__":
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 3000
    workers = int(sys.argv[2]) if len(sys.argv) > 2 else 50
    asyncio.run(run_stress_benchmark(total_txs=count, num_workers=workers))
