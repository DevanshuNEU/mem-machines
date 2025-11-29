#!/usr/bin/env python3
# =============================================================================
# Load Testing Script
# =============================================================================
"""
Load test for the Memory Machines Ingest API.

Simulates the "chaos script" that will be used for evaluation:
- 1000 RPM (requests per minute)
- Mixed JSON and text payloads
- Multiple tenants

Usage:
    python load_test.py --url https://YOUR_API_URL --rpm 1000 --duration 60

Requirements:
    pip install httpx asyncio
"""

import argparse
import asyncio
import json
import random
import string
import time
from dataclasses import dataclass
from datetime import datetime
from typing import List

import httpx


# =============================================================================
# Configuration
# =============================================================================

TENANTS = ["acme_corp", "beta_inc", "gamma_ltd", "delta_co", "epsilon_io"]

SAMPLE_TEXTS = [
    "User 555-0199 accessed the system at {timestamp}",
    "Login attempt from IP 192.168.1.{ip} for user {user}@example.com",
    "Transaction {txn_id} processed for amount ${amount}",
    "Error: Connection timeout after {timeout}ms",
    "API call to /api/v1/{endpoint} completed in {latency}ms",
    "User {user} updated profile settings",
    "Session expired for user with SSN 123-45-{ssn}",
    "Database query executed in {query_time}ms",
]


@dataclass
class TestResult:
    """Result of a single test request."""
    success: bool
    status_code: int
    latency_ms: float
    tenant_id: str
    content_type: str
    error: str = None


# =============================================================================
# Test Data Generation
# =============================================================================

def generate_text() -> str:
    """Generate a random log text."""
    template = random.choice(SAMPLE_TEXTS)
    return template.format(
        timestamp=datetime.now().isoformat(),
        ip=random.randint(1, 255),
        user="".join(random.choices(string.ascii_lowercase, k=8)),
        txn_id="".join(random.choices(string.ascii_uppercase + string.digits, k=10)),
        amount=random.randint(10, 10000),
        timeout=random.randint(100, 5000),
        endpoint=random.choice(["users", "orders", "products", "analytics"]),
        latency=random.randint(10, 500),
        ssn=random.randint(1000, 9999),
        query_time=random.randint(1, 100),
    )


def generate_json_payload() -> dict:
    """Generate a JSON payload."""
    return {
        "tenant_id": random.choice(TENANTS),
        "log_id": f"log_{''.join(random.choices(string.ascii_lowercase + string.digits, k=16))}",
        "text": generate_text(),
    }


def generate_text_payload() -> tuple:
    """Generate a text payload with headers."""
    return (
        generate_text(),
        random.choice(TENANTS),
    )


# =============================================================================
# Load Test Runner
# =============================================================================

async def send_request(
    client: httpx.AsyncClient,
    url: str,
    use_json: bool,
) -> TestResult:
    """Send a single request to the API."""
    tenant_id = ""
    content_type = ""
    
    try:
        start = time.perf_counter()
        
        if use_json:
            payload = generate_json_payload()
            tenant_id = payload["tenant_id"]
            content_type = "application/json"
            
            response = await client.post(
                f"{url}/ingest",
                json=payload,
                headers={"Content-Type": "application/json"},
            )
        else:
            text, tenant_id = generate_text_payload()
            content_type = "text/plain"
            
            response = await client.post(
                f"{url}/ingest",
                content=text,
                headers={
                    "Content-Type": "text/plain",
                    "X-Tenant-ID": tenant_id,
                },
            )
        
        latency = (time.perf_counter() - start) * 1000
        
        return TestResult(
            success=response.status_code == 202,
            status_code=response.status_code,
            latency_ms=latency,
            tenant_id=tenant_id,
            content_type=content_type,
        )
        
    except Exception as e:
        return TestResult(
            success=False,
            status_code=0,
            latency_ms=0,
            tenant_id=tenant_id,
            content_type=content_type,
            error=str(e),
        )


async def run_load_test(
    url: str,
    rpm: int,
    duration_seconds: int,
) -> List[TestResult]:
    """Run the load test."""
    results: List[TestResult] = []
    interval = 60.0 / rpm  # Seconds between requests
    
    print(f"\n{'='*60}")
    print(f"Memory Machines Load Test")
    print(f"{'='*60}")
    print(f"Target URL: {url}")
    print(f"Target RPM: {rpm}")
    print(f"Duration: {duration_seconds} seconds")
    print(f"Request interval: {interval*1000:.1f}ms")
    print(f"{'='*60}\n")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        start_time = time.perf_counter()
        request_count = 0
        
        while (time.perf_counter() - start_time) < duration_seconds:
            # Alternate between JSON and text payloads
            use_json = request_count % 2 == 0
            
            # Send request
            result = await send_request(client, url, use_json)
            results.append(result)
            request_count += 1
            
            # Progress update every 100 requests
            if request_count % 100 == 0:
                elapsed = time.perf_counter() - start_time
                current_rpm = (request_count / elapsed) * 60
                success_rate = sum(1 for r in results if r.success) / len(results) * 100
                print(f"  Sent {request_count} requests | "
                      f"Actual RPM: {current_rpm:.0f} | "
                      f"Success: {success_rate:.1f}%")
            
            # Wait for next request
            await asyncio.sleep(interval)
    
    return results


def print_results(results: List[TestResult]) -> None:
    """Print test results summary."""
    total = len(results)
    successful = sum(1 for r in results if r.success)
    failed = total - successful
    
    latencies = [r.latency_ms for r in results if r.success]
    avg_latency = sum(latencies) / len(latencies) if latencies else 0
    min_latency = min(latencies) if latencies else 0
    max_latency = max(latencies) if latencies else 0
    
    # Calculate p50, p95, p99
    sorted_latencies = sorted(latencies)
    p50 = sorted_latencies[int(len(sorted_latencies) * 0.50)] if sorted_latencies else 0
    p95 = sorted_latencies[int(len(sorted_latencies) * 0.95)] if sorted_latencies else 0
    p99 = sorted_latencies[int(len(sorted_latencies) * 0.99)] if sorted_latencies else 0
    
    # Count by tenant
    tenant_counts = {}
    for r in results:
        tenant_counts[r.tenant_id] = tenant_counts.get(r.tenant_id, 0) + 1
    
    # Count by content type
    json_count = sum(1 for r in results if r.content_type == "application/json")
    text_count = sum(1 for r in results if r.content_type == "text/plain")
    
    print(f"\n{'='*60}")
    print("RESULTS SUMMARY")
    print(f"{'='*60}")
    print(f"\nTotal Requests:     {total}")
    print(f"Successful (202):   {successful} ({successful/total*100:.1f}%)")
    print(f"Failed:             {failed} ({failed/total*100:.1f}%)")
    print(f"\nLatency (ms):")
    print(f"  Average:          {avg_latency:.1f}")
    print(f"  Min:              {min_latency:.1f}")
    print(f"  Max:              {max_latency:.1f}")
    print(f"  p50:              {p50:.1f}")
    print(f"  p95:              {p95:.1f}")
    print(f"  p99:              {p99:.1f}")
    print(f"\nPayload Distribution:")
    print(f"  JSON:             {json_count} ({json_count/total*100:.1f}%)")
    print(f"  Text:             {text_count} ({text_count/total*100:.1f}%)")
    print(f"\nTenant Distribution:")
    for tenant, count in sorted(tenant_counts.items()):
        print(f"  {tenant}: {count} ({count/total*100:.1f}%)")
    
    # Show errors if any
    errors = [r for r in results if r.error]
    if errors:
        print(f"\nErrors ({len(errors)}):")
        error_types = {}
        for r in errors:
            error_types[r.error] = error_types.get(r.error, 0) + 1
        for error, count in error_types.items():
            print(f"  {error}: {count}")
    
    print(f"\n{'='*60}")
    if successful / total >= 0.99:
        print("✅ PASS: >99% success rate")
    else:
        print("❌ FAIL: <99% success rate")
    print(f"{'='*60}\n")


# =============================================================================
# Main
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="Load test for Memory Machines API")
    parser.add_argument("--url", required=True, help="Base URL of the Ingest API")
    parser.add_argument("--rpm", type=int, default=1000, help="Requests per minute")
    parser.add_argument("--duration", type=int, default=60, help="Test duration in seconds")
    
    args = parser.parse_args()
    
    # Remove trailing slash
    url = args.url.rstrip("/")
    
    # Run the test
    results = asyncio.run(run_load_test(url, args.rpm, args.duration))
    
    # Print results
    print_results(results)


if __name__ == "__main__":
    main()
