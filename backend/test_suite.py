"""
HYCON Test Suite - All-in-One
==============================
Complete testing suite with token generation, backend & frontend tests in ONE file.
Works on Windows, macOS, and Linux.

Usage:
    python test_suite.py                    # Run ALL tests (backend + frontend)
    python test_suite.py --backend-only     # Only backend tests
    python test_suite.py --frontend-only    # Only frontend tests
    python test_suite.py --concurrency-only # Only concurrency tests
    python test_suite.py --api-only         # Only API response tests
    python test_suite.py --setup            # Generate tokens and exit
    python test_suite.py --verbose          # Detailed output
"""

import argparse
import asyncio
import aiohttp
import requests
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


def print_header(text):
    """Print formatted header."""
    print(f"\n{'=' * 80}")
    print(f"{text}")
    print(f"{'=' * 80}\n")


# ============================================================================
# Token Generation (Built-in)
# ============================================================================

def get_token(base_url: str, email: str, password: str) -> dict:
    """Login and get JWT token."""
    try:
        response = requests.post(
            f"{base_url}/auth/login",
            json={"email": email, "password": password},
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            data = response.json()
            return {
                "success": True,
                "email": email,
                "token": data.get("access_token"),
                "user": data.get("user", {})
            }
        else:
            return {"success": False, "email": email, "error": response.json()}
    except Exception as e:
        return {"success": False, "email": email, "error": str(e)}


def generate_tokens(base_url: str):
    """Generate tokens for all test users."""
    print("🔑 Generating test tokens...")
    
    users = [
        ("admin@hycon.com", "admin123", "Admin"),
        ("user@hycon.com", "user123", "User"),
    ]
    
    tokens = {}
    
    for email, password, role in users:
        result = get_token(base_url, email, password)
        
        if result["success"]:
            tokens[role.lower()] = result["token"]
            print(f"  ✓ {role}: {email}")
        else:
            print(f"  ✗ {role}: {email} - {result.get('error')}")
            return None
    
    # Save to file
    token_file = Path(__file__).parent / "test_tokens.txt"
    with open(token_file, "w") as f:
        f.write(f"ADMIN_TOKEN={tokens['admin']}\n")
        f.write(f"USER_TOKENS={tokens['user']}\n")
    
    print(f"\n✅ Tokens saved to {token_file}\n")
    return tokens


def read_tokens():
    """Read tokens from test_tokens.txt or generate new ones."""
    token_file = Path(__file__).parent / "test_tokens.txt"
    
    if not token_file.exists():
        return None
    
    admin_token = None
    user_tokens = []
    
    with open(token_file) as f:
        for line in f:
            if line.startswith("ADMIN_TOKEN="):
                admin_token = line.split("=", 1)[1].strip()
            elif line.startswith("USER_TOKENS="):
                tokens_str = line.split("=", 1)[1].strip()
                user_tokens = [t.strip() for t in tokens_str.split(",")]
    
    if admin_token and user_tokens:
        return admin_token, user_tokens
    return None


# ============================================================================
# TEST 1: Concurrent Session Starts (Race Condition Prevention)
# ============================================================================

async def test_concurrent_session_start(base_url, admin_token, user_tokens, equipment_id):
    """Test that only one session can be started when multiple requests are made simultaneously."""
    print("TEST: Concurrent Session Starts")
    print("-" * 80)
    
    async with aiohttp.ClientSession() as session:
        # Cleanup: End any active sessions first
        try:
            active_sessions = await session.get(
                f"{base_url}/sessions/",
                params={"status": "active"},
                headers={"Authorization": f"Bearer {admin_token}"}
            )
            if active_sessions.status == 200:
                sessions_data = await active_sessions.json()
                for sess in sessions_data:
                    if sess.get("equipment_id") == equipment_id:
                        await session.post(
                            f"{base_url}/sessions/{sess['id']}/end",
                            headers={"Authorization": f"Bearer {admin_token}"}
                        )
        except:
            pass  # Ignore cleanup errors
        
        # Use 10 concurrent requests
        tasks = []
        for i in range(10):
            token = user_tokens[i % len(user_tokens)]
            tasks.append(
                session.post(
                    f"{base_url}/sessions/start",
                    json={"equipment_id": equipment_id},
                    headers={"Authorization": f"Bearer {token}"}
                )
            )
        
        start_time = asyncio.get_event_loop().time()
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = asyncio.get_event_loop().time()
        
        # Analyze results
        successes = 0
        failures = 0
        error_messages = []
        
        for response in responses:
            if isinstance(response, Exception):
                failures += 1
                error_messages.append(str(response))
                continue
            
            data = await response.json()
            if response.status == 200:
                successes += 1
            else:
                failures += 1
                error_messages.append(data.get("detail", "Unknown error"))
        
        print(f"Concurrent requests: {len(tasks)}")
        print(f"Time taken: {end_time - start_time:.2f}s")
        print(f"Successes: {successes}")
        print(f"Failures: {failures}")
        
        # Validation
        passed = True
        
        if successes != 1:
            print(f"✗ FAIL: Expected exactly 1 success, got {successes}")
            passed = False
        else:
            print("✓ PASS: Exactly 1 session started (race condition prevented)")
        
        # Check error messages
        valid_errors = sum(1 for msg in error_messages if 
                          any(phrase in msg.lower() for phrase in 
                              ['in use', 'in_use', 'already in use', 'already have an active session']))
        
        print(f"\nSample error messages:")
        for i, msg in enumerate(error_messages[:3], 1):
            print(f"  Error {i}: {msg}")
        
        if valid_errors == failures:
            print("✓ PASS: All failures returned correct error messages")
        else:
            print(f"✗ FAIL: Expected {failures} error messages, got {valid_errors} valid ones")
            passed = False
        
        return passed


# ============================================================================
# TEST 2: Overlapping Past Usage Detection
# ============================================================================

async def test_overlapping_past_usage(base_url, admin_token, user_tokens, equipment_id):
    """Test that overlapping time periods are correctly detected and rejected."""
    print("\nTEST: Overlapping Past Usage Detection")
    print("-" * 80)
    
    async with aiohttp.ClientSession() as session:
        # Create base time period
        now = datetime.now(timezone.utc)
        base_start = now - timedelta(hours=2)
        base_end = now - timedelta(hours=1)
        
        # Log first past usage
        past_usage_data = [
            {
                "equipment_id": equipment_id,
                "start_time": base_start.isoformat(),
                "end_time": base_end.isoformat(),
                "description": "Base session"
            },
            # Overlapping session (should fail)
            {
                "equipment_id": equipment_id,
                "start_time": (base_start - timedelta(minutes=30)).isoformat(),
                "end_time": (base_start + timedelta(minutes=30)).isoformat(),
                "description": "Overlapping session"
            },
            # Non-overlapping session (should succeed)
            {
                "equipment_id": equipment_id,
                "start_time": (base_end + timedelta(hours=1)).isoformat(),
                "end_time": (base_end + timedelta(hours=2)).isoformat(),
                "description": "Non-overlapping session"
            }
        ]
        
        successes = 0
        failures = 0
        error_messages = []
        
        for data in past_usage_data:
            response = await session.post(
                f"{base_url}/sessions/log-past-usage",
                json=data,
                headers={"Authorization": f"Bearer {admin_token}"}
            )
            
            result = await response.json()
            
            if response.status == 200:
                successes += 1
            else:
                failures += 1
                error_messages.append(result.get("detail", "Unknown error"))
        
        print(f"Total past usage logs attempted: {len(past_usage_data)}")
        print(f"Successes: {successes}")
        print(f"Failures: {failures}")
        
        passed = True
        
        if failures >= 1:
            print("\n✓ PASS: Overlapping session correctly detected and rejected")
            
            # Check for overlap error message
            overlap_errors = [msg for msg in error_messages if 'overlap' in msg.lower()]
            
            print(f"\nPast usage error messages:")
            for i, msg in enumerate(error_messages, 1):
                print(f"  Failure {i}: {msg}")
            
            if overlap_errors:
                print("✓ PASS: Overlap error message correctly returned")
            else:
                print("✗ FAIL: No overlap error message found")
                passed = False
        else:
            print("✗ FAIL: Expected at least 1 failure for overlapping session")
            passed = False
        
        return passed


# ============================================================================
# TEST 3: Connection Pool Stress Test
# ============================================================================

async def test_connection_pool_stress(base_url, admin_token, num_requests=100):
    """Test connection pool handling under stress."""
    print("\nTEST: Connection Pool Stress Test")
    print("-" * 80)
    
    async with aiohttp.ClientSession() as session:
        tasks = []
        
        # Create many concurrent health check requests
        for _ in range(num_requests):
            tasks.append(
                session.get(
                    f"{base_url}/health",
                    headers={"Authorization": f"Bearer {admin_token}"}
                )
            )
        
        start_time = asyncio.get_event_loop().time()
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = asyncio.get_event_loop().time()
        
        successes = sum(1 for r in responses if not isinstance(r, Exception) and r.status == 200)
        errors = len(responses) - successes
        
        time_taken = end_time - start_time
        req_per_sec = num_requests / time_taken if time_taken > 0 else 0
        
        print(f"Concurrent requests: {num_requests}")
        print(f"Time taken: {time_taken:.2f}s")
        print(f"Requests/second: {req_per_sec:.2f}")
        print(f"Successes: {successes}")
        print(f"Errors: {errors}")
        
        passed = True
        
        if successes == num_requests:
            print("✓ PASS: All requests completed successfully")
        else:
            print(f"✗ FAIL: {errors} requests failed")
            passed = False
        
        success_rate = (successes / num_requests) * 100
        if success_rate >= 95:
            print(f"✓ PASS: {success_rate:.1f}% success rate achieved")
        else:
            print(f"✗ FAIL: Only {success_rate:.1f}% success rate")
            passed = False
        
        return passed


# ============================================================================
# TEST 4: API Response Validation
# ============================================================================

async def test_api_responses(base_url, admin_token, user_tokens, equipment_id):
    """Test API response structure and error handling."""
    print("\nTEST: API Response Validation")
    print("-" * 80)
    
    async with aiohttp.ClientSession() as session:
        passed = True
        
        # Test 1: Health check
        print("Testing health endpoint...")
        response = await session.get(f"{base_url}/health")
        data = await response.json()
        
        if response.status == 200 and data.get("status") == "healthy":
            print("✓ PASS: Health endpoint working")
        else:
            print("✗ FAIL: Health endpoint failed")
            passed = False
        
        # Test 2: Equipment list
        print("Testing equipment list...")
        response = await session.get(
            f"{base_url}/equipment/",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        data = await response.json()
        
        if response.status == 200 and isinstance(data, list):
            print(f"✓ PASS: Equipment list returned {len(data)} items")
        else:
            print("✗ FAIL: Equipment list failed")
            passed = False
        
        # Test 3: Invalid token
        print("Testing invalid token handling...")
        response = await session.get(
            f"{base_url}/equipment/",
            headers={"Authorization": "Bearer invalid_token"}
        )
        
        if response.status == 401:
            print("✓ PASS: Invalid token correctly rejected")
        else:
            print(f"✗ FAIL: Expected 401, got {response.status}")
            passed = False
        
        return passed


# ============================================================================
# TEST 5: Frontend Tests
# ============================================================================

def test_frontend(verbose=False):
    """Run frontend tests if they exist."""
    print("\nTEST: Frontend Tests")
    print("-" * 80)
    
    frontend_dir = Path(__file__).parent.parent / "frontend"
    
    if not frontend_dir.exists():
        print("⚠️  Frontend directory not found")
        return True  # Not a failure
    
    # Check if package.json has test script
    package_json = frontend_dir / "package.json"
    if not package_json.exists():
        print("⚠️  No package.json found in frontend")
        return True
    
    # Check if test script exists in package.json
    import json
    try:
        with open(package_json) as f:
            pkg = json.load(f)
            if "test" not in pkg.get("scripts", {}):
                print("⚠️  No test script configured in package.json")
                print("   To add tests:")
                print("   1. npm install --save-dev vitest @testing-library/react @testing-library/jest-dom")
                print("   2. Add to package.json: \"test\": \"vitest\"")
                return True  # Not a failure, just not set up yet
    except:
        pass
    
    # Try to run tests
    print(f"Running frontend tests from {frontend_dir}...")
    
    result = subprocess.run(
        ["npm", "test"],
        cwd=frontend_dir,
        capture_output=not verbose,
        text=True
    )
    
    if result.returncode == 0:
        print("✓ PASS: Frontend tests passed")
        return True
    elif "Missing script" in (result.stdout + result.stderr) or "No tests found" in (result.stdout + result.stderr):
        print("⚠️  No frontend tests configured yet")
        print("   To add tests:")
        print("   1. npm install --save-dev vitest @testing-library/react @testing-library/jest-dom")
        print("   2. Add to package.json: \"test\": \"vitest\"")
        return True  # Not a failure
    else:
        print("✗ FAIL: Frontend tests failed")
        if not verbose and result.stderr:
            print(result.stderr[:500])
        return False


# ============================================================================
# Main Test Runner
# ============================================================================

async def main():
    parser = argparse.ArgumentParser(
        description="HYCON All-in-One Test Suite",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument("--base-url", default="http://localhost:8000", help="Base URL for API")
    parser.add_argument("--equipment-id", type=int, default=1, help="Equipment ID to test")
    parser.add_argument("--backend-only", action="store_true", help="Run only backend tests")
    parser.add_argument("--frontend-only", action="store_true", help="Run only frontend tests")
    parser.add_argument("--concurrency-only", action="store_true", help="Run only concurrency tests")
    parser.add_argument("--api-only", action="store_true", help="Run only API tests")
    parser.add_argument("--setup", action="store_true", help="Generate tokens and exit")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    # Setup mode - just generate tokens
    if args.setup:
        print_header("Token Setup")
        tokens = generate_tokens(args.base_url)
        sys.exit(0 if tokens else 1)
    
    print_header("HYCON Test Suite")
    print(f"Base URL: {args.base_url}")
    
    # Read or generate tokens
    token_data = read_tokens()
    if not token_data:
        print("⚠️  No tokens found. Generating...")
        token_dict = generate_tokens(args.base_url)
        if not token_dict:
            print("❌ Failed to generate tokens")
            sys.exit(1)
        admin_token = token_dict['admin']
        user_tokens = [token_dict['user']]
    else:
        admin_token, user_tokens = token_data
    
    print(f"User Tokens: {len(user_tokens)}")
    print(f"Equipment ID: {args.equipment_id}\n")
    
    # Determine what to test
    run_backend = not args.frontend_only
    run_frontend = args.frontend_only or not (args.backend_only or args.concurrency_only or args.api_only)
    
    # Run tests
    results = []
    
    # Backend tests
    if run_backend and not args.api_only:
        # Concurrency tests
        results.append(("Concurrent Session Starts", 
                       await test_concurrent_session_start(args.base_url, admin_token, user_tokens, args.equipment_id)))
        
        results.append(("Overlapping Past Usage", 
                       await test_overlapping_past_usage(args.base_url, admin_token, user_tokens, args.equipment_id)))
        
        results.append(("Connection Pool Stress", 
                       await test_connection_pool_stress(args.base_url, admin_token)))
    
    if run_backend and not args.concurrency_only:
        # API tests
        results.append(("API Response Validation", 
                       await test_api_responses(args.base_url, admin_token, user_tokens, args.equipment_id)))
    
    # Frontend tests
    if run_frontend:
        results.append(("Frontend Tests", test_frontend(args.verbose)))
    
    # Print summary
    print_header("TEST SUMMARY")
    
    passed = sum(1 for _, p in results if p)
    failed = len(results) - passed
    
    for test_name, test_passed in results:
        status = "✓ PASSED" if test_passed else "✗ FAILED"
        print(f"{test_name:.<50} {status}")
    
    print(f"\nTotal Tests: {len(results)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    
    if failed == 0:
        print("\n🎉 All tests passed!")
    else:
        print(f"\n❌ {failed} test(s) failed")
    
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    asyncio.run(main())
