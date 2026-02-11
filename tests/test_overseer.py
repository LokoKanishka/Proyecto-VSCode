#!/usr/bin/env python3
"""
Test script for the Overseer autonomous cognitive system.

This validates that:
1. Overseer can initialize properly
2. Autonomous cycle can execute without crashing
3. Safety guards prevent dangerous actions
4. Status reporting works correctly
"""

import ray
import asyncio
import sys
from loguru import logger

logger.remove()
logger.add(sys.stdout, level="INFO")


async def test_overseer_initialization():
    """Test 1: Overseer can be created and initialized"""
    logger.info("Test 1: Initializing Overseer...")
    
    try:
        from src.core.overseer import Overseer, get_or_create_overseer
        
        # Initialize Ray if not already running
        if not ray.is_initialized():
            ray.init(namespace="lucy", ignore_reinit_error=True)
        
        # Create Overseer
        overseer = get_or_create_overseer()
        status = await overseer.status.remote()
        
        assert status["state"] == "DORMANT", f"Expected DORMANT, got {status['state']}"
        assert status["autonomous_enabled"] == False
        assert status["cycle_count"] == 0
        
        logger.info("✅ Test 1 PASSED: Overseer initialized successfully")
        return True
    except Exception as e:
        logger.error(f"❌ Test 1 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_overseer_intent_setting():
    """Test 2: Overseer can receive and store intent"""
    logger.info("Test 2: Setting intent...")
    
    try:
        overseer = ray.get_actor("Overseer")
        
        test_intent = "Monitor system and report any anomalies"
        result = await overseer.set_intent.remote(test_intent)
        
        status = await overseer.status.remote()
        assert status["world_model"]["user_intent"] == test_intent
        
        logger.info("✅ Test 2 PASSED: Intent set successfully")
        return True
    except Exception as e:
        logger.error(f"❌ Test 2 FAILED: {e}")
        return False


async def test_overseer_safety_guards():
    """Test 3: Safety guards reject dangerous plans"""
    logger.info("Test 3: Testing safety guards...")
    
    try:
        overseer = ray.get_actor("Overseer")
        
        # These should be rejected by safety critic
        dangerous_plans = [
            ["rm -rf /home/user/important_data"],
            ["sudo shutdown now"],
            ["delete all files"],
        ]
        
        for plan in dangerous_plans:
            # Access private method for testing (not ideal, but acceptable for verification)
            # In production code, this would be tested indirectly
            is_safe = overseer._is_safe_plan.remote(plan)
            result = await is_safe
            assert result == False, f"Dangerous plan not rejected: {plan}"
        
        logger.info("✅ Test 3 PASSED: Safety guards working correctly")
        return True
    except Exception as e:
        logger.error(f"❌ Test 3 FAILED: {e}")
        return False


async def test_overseer_autonomous_cycle():
    """Test 4: Autonomous cycle can execute without errors"""
    logger.info("Test 4: Running short autonomous cycle...")
    
    try:
        overseer = ray.get_actor("Overseer")
        
        # Run a very short cycle (3 iterations)
        # This should complete without crashing
        future = overseer.autonomous_cycle.remote(max_iterations=3)
        result = await future
        
        logger.info(f"Cycle result: {result}")
        
        status = await overseer.status.remote()
        assert status["cycle_count"] >= 3, f"Expected at least 3 cycles, got {status['cycle_count']}"
        assert status["state"] == "DORMANT", "Overseer should return to DORMANT after cycle"
        
        logger.info("✅ Test 4 PASSED: Autonomous cycle completed successfully")
        return True
    except Exception as e:
        logger.error(f"❌ Test 4 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_overseer_stop_command():
    """Test 5: Emergency stop works correctly"""
    logger.info("Test 5: Testing emergency stop...")
    
    try:
        overseer = ray.get_actor("Overseer")
        
        # Start a long cycle in background
        overseer.autonomous_cycle.remote(max_iterations=100)
        
        # Wait a bit to ensure it starts
        await asyncio.sleep(2)
        
        # Send stop signal
        result = await overseer.stop_autonomous.remote()
        logger.info(f"Stop result: {result}")
        
        # Verify it stopped
        await asyncio.sleep(1)
        status = await overseer.status.remote()
        assert status["autonomous_enabled"] == False
        
        logger.info("✅ Test 5 PASSED: Emergency stop works correctly")
        return True
    except Exception as e:
        logger.error(f"❌ Test 5 FAILED: {e}")
        return False


async def main():
    """Run all tests"""
    logger.info("="*60)
    logger.info("OVERSEER VERIFICATION TESTS")
    logger.info("="*60)
    
    tests = [
        ("Initialization", test_overseer_initialization),
        ("Intent Setting", test_overseer_intent_setting),
        ("Safety Guards", test_overseer_safety_guards),
        ("Autonomous Cycle", test_overseer_autonomous_cycle),
        ("Emergency Stop", test_overseer_stop_command),
    ]
    
    results = []
    for name, test_func in tests:
        logger.info(f"\n--- Running: {name} ---")
        try:
            result = await test_func()
            results.append((name, result))
        except Exception as e:
            logger.error(f"Test {name} crashed: {e}")
            results.append((name, False))
    
    # Summary
    logger.info("\n" + "="*60)
    logger.info("TEST SUMMARY")
    logger.info("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{status}: {name}")
    
    logger.info(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All tests passed! Overseer is operational.")
        return 0
    else:
        logger.error("⚠️ Some tests failed. Review logs above.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
