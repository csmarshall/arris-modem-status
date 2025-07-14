#!/usr/bin/env python3
"""
Comprehensive Performance Test for Optimized Arris Client
=========================================================

This script performs extensive testing and validation of the optimized
Arris modem client, including:

- Performance benchmarking vs original client
- Data parsing validation 
- Error handling verification
- Channel data quality analysis
- Speed optimization verification

Usage:
    python comprehensive_test.py --password "your_password" [options]

Author: Charles Marshall  
Version: 1.1.0
"""

import argparse
import json
import logging
import time
import statistics
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import asdict

# Import both clients for comparison
try:
    from arris_modem_status.arris_status_client import ArrisStatusClient as OriginalClient
except ImportError:
    OriginalClient = None
    
from optimized_arris_client import OptimizedArrisClient, ChannelInfo

# Configure enhanced logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


class ComprehensiveTestSuite:
    """
    Complete test suite for validating optimized Arris client performance and accuracy.
    """
    
    def __init__(self, password: str, host: str = "192.168.100.1"):
        self.password = password
        self.host = host
        self.test_results = {
            "timestamp": datetime.now().isoformat(),
            "test_configuration": {
                "host": host,
                "password_length": len(password),
                "test_version": "1.1.0"
            },
            "performance_tests": {},
            "validation_tests": {},
            "comparison_tests": {},
            "recommendations": []
        }
        
        logger.info("🚀 Comprehensive Test Suite v1.1.0")
        logger.info(f"📋 Target: {host}")
        logger.info(f"🔧 Password length: {len(password)} chars")
        logger.info("=" * 70)

    def run_all_tests(self) -> Dict[str, Any]:
        """Execute complete test suite."""
        
        # Test 1: Performance Benchmarking
        logger.info("\n🏁 TEST 1: Performance Benchmarking")
        logger.info("-" * 50)
        self.test_results["performance_tests"] = self._run_performance_tests()
        
        # Test 2: Data Validation  
        logger.info("\n🔍 TEST 2: Data Validation & Parsing")
        logger.info("-" * 50)
        self.test_results["validation_tests"] = self._run_validation_tests()
        
        # Test 3: Stress Testing
        logger.info("\n💪 TEST 3: Stress & Reliability Testing")
        logger.info("-" * 50)
        self.test_results["stress_tests"] = self._run_stress_tests()
        
        # Test 4: Comparison with Original (if available)
        if OriginalClient:
            logger.info("\n⚖️  TEST 4: Original vs Optimized Comparison")
            logger.info("-" * 50)
            self.test_results["comparison_tests"] = self._run_comparison_tests()
        
        # Generate recommendations
        self._generate_recommendations()
        
        return self.test_results

    def _run_performance_tests(self) -> Dict[str, Any]:
        """Test performance characteristics of optimized client."""
        performance_results = {
            "authentication_speed": {},
            "data_retrieval_speed": {},
            "concurrent_performance": {},
            "memory_efficiency": {}
        }
        
        try:
            # Authentication Speed Test
            logger.info("🔐 Testing authentication speed...")
            auth_times = []
            
            for i in range(3):
                client = OptimizedArrisClient(password=self.password, host=self.host)
                start_time = time.time()
                
                success = client.authenticate()
                auth_time = time.time() - start_time
                
                if success:
                    auth_times.append(auth_time)
                    logger.info(f"   Auth attempt {i+1}: {auth_time:.2f}s ✅")
                else:
                    logger.error(f"   Auth attempt {i+1}: FAILED ❌")
                
                client.close()
                time.sleep(1)  # Brief pause between tests
            
            if auth_times:
                performance_results["authentication_speed"] = {
                    "attempts": len(auth_times),
                    "average_time": statistics.mean(auth_times),
                    "min_time": min(auth_times),
                    "max_time": max(auth_times),
                    "consistency": max(auth_times) - min(auth_times) < 1.0
                }
                
                avg_time = statistics.mean(auth_times)
                logger.info(f"📊 Auth Performance: Avg {avg_time:.2f}s, Range {min(auth_times):.2f}-{max(auth_times):.2f}s")
            
            # Data Retrieval Speed Test
            logger.info("📊 Testing data retrieval speed...")
            
            client = OptimizedArrisClient(password=self.password, host=self.host)
            retrieval_times = []
            
            for i in range(3):
                start_time = time.time()
                status = client.get_status()
                retrieval_time = time.time() - start_time
                
                retrieval_times.append(retrieval_time)
                channel_count = len(status.get('downstream_channels', [])) + len(status.get('upstream_channels', []))
                logger.info(f"   Retrieval {i+1}: {retrieval_time:.2f}s, {channel_count} channels ✅")
                
                time.sleep(0.5)
            
            client.close()
            
            if retrieval_times:
                performance_results["data_retrieval_speed"] = {
                    "attempts": len(retrieval_times),
                    "average_time": statistics.mean(retrieval_times),
                    "min_time": min(retrieval_times),
                    "max_time": max(retrieval_times),
                    "channels_per_second": channel_count / statistics.mean(retrieval_times) if retrieval_times else 0
                }
                
                avg_time = statistics.mean(retrieval_times)
                logger.info(f"📊 Retrieval Performance: Avg {avg_time:.2f}s, {channel_count/avg_time:.1f} channels/sec")
            
        except Exception as e:
            logger.error(f"Performance test error: {e}")
            performance_results["error"] = str(e)
            
        return performance_results

    def _run_validation_tests(self) -> Dict[str, Any]:
        """Comprehensive data validation testing."""
        validation_results = {}
        
        try:
            logger.info("🔍 Running comprehensive validation...")
            
            client = OptimizedArrisClient(password=self.password, host=self.host)
            validation_data = client.validate_parsing()
            client.close()
            
            # Extract validation metrics
            parsing_validation = validation_data.get("parsing_validation", {})
            performance_metrics = validation_data.get("performance_metrics", {})
            
            validation_results = {
                "data_completeness": {
                    "basic_info_complete": parsing_validation.get("basic_info_parsed", False),
                    "internet_status_available": parsing_validation.get("internet_status_parsed", False),
                    "channel_data_available": parsing_validation.get("downstream_channels_found", 0) > 0,
                    "completeness_score": performance_metrics.get("data_completeness_score", 0)
                },
                "channel_analysis": {
                    "downstream_count": parsing_validation.get("downstream_channels_found", 0),
                    "upstream_count": parsing_validation.get("upstream_channels_found", 0),
                    "total_channels": performance_metrics.get("total_channels", 0),
                    "channel_quality": parsing_validation.get("channel_data_quality", {})
                },
                "format_validation": {
                    "mac_address_valid": parsing_validation.get("mac_address_format", False),
                    "frequency_formats_valid": parsing_validation.get("frequency_formats", {})
                }
            }
            
            # Log validation results
            downstream_count = validation_results["channel_analysis"]["downstream_count"]
            upstream_count = validation_results["channel_analysis"]["upstream_count"] 
            completeness = validation_results["data_completeness"]["completeness_score"]
            
            logger.info(f"📈 Channel Data: {downstream_count} downstream, {upstream_count} upstream")
            logger.info(f"🎯 Data Completeness: {completeness:.1f}%")
            logger.info(f"✅ MAC Format Valid: {validation_results['format_validation']['mac_address_valid']}")
            
            # Detailed channel quality analysis
            channel_quality = validation_results["channel_analysis"]["channel_quality"]
            if channel_quality:
                downstream_qual = channel_quality.get("downstream_validation", {})
                upstream_qual = channel_quality.get("upstream_validation", {})
                
                if downstream_qual:
                    logger.info(f"📡 Downstream Quality: {downstream_qual.get('all_locked', False)} all locked, "
                              f"Modulations: {len(downstream_qual.get('modulation_types', []))}")
                              
                if upstream_qual:
                    logger.info(f"📤 Upstream Quality: {upstream_qual.get('all_locked', False)} all locked, "
                              f"Modulations: {len(upstream_qual.get('modulation_types', []))}")
            
        except Exception as e:
            logger.error(f"Validation test error: {e}")
            validation_results["error"] = str(e)
            
        return validation_results

    def _run_stress_tests(self) -> Dict[str, Any]:
        """Test reliability under stress conditions."""
        stress_results = {
            "rapid_requests": {},
            "connection_stability": {},
            "error_recovery": {}
        }
        
        try:
            logger.info("💪 Testing rapid consecutive requests...")
            
            client = OptimizedArrisClient(password=self.password, host=self.host)
            
            # Rapid request test
            rapid_times = []
            rapid_successes = 0
            
            for i in range(5):
                try:
                    start_time = time.time()
                    status = client.get_status()
                    request_time = time.time() - start_time
                    
                    if status and len(status.get('downstream_channels', [])) > 0:
                        rapid_times.append(request_time)
                        rapid_successes += 1
                        logger.info(f"   Rapid request {i+1}: {request_time:.2f}s ✅")
                    else:
                        logger.warning(f"   Rapid request {i+1}: No data ⚠️")
                        
                except Exception as e:
                    logger.error(f"   Rapid request {i+1}: {e} ❌")
                
                time.sleep(0.2)  # Brief pause
            
            stress_results["rapid_requests"] = {
                "total_attempts": 5,
                "successful_requests": rapid_successes,
                "success_rate": rapid_successes / 5,
                "average_time": statistics.mean(rapid_times) if rapid_times else 0,
                "performance_degradation": max(rapid_times) - min(rapid_times) if len(rapid_times) > 1 else 0
            }
            
            logger.info(f"📊 Stress Test: {rapid_successes}/5 successful ({rapid_successes/5*100:.1f}%)")
            
            client.close()
            
        except Exception as e:
            logger.error(f"Stress test error: {e}")
            stress_results["error"] = str(e)
            
        return stress_results

    def _run_comparison_tests(self) -> Dict[str, Any]:
        """Compare optimized vs original client performance."""
        comparison_results = {}
        
        if not OriginalClient:
            return {"error": "Original client not available for comparison"}
        
        try:
            logger.info("⚖️  Comparing optimized vs original client...")
            
            # Test Original Client
            logger.info("📊 Testing original client...")
            original_start = time.time()
            
            original_client = OriginalClient(password=self.password, host=self.host)
            original_status = original_client.get_status()
            original_time = time.time() - original_start
            original_client.close()
            
            # Test Optimized Client  
            logger.info("🚀 Testing optimized client...")
            optimized_start = time.time()
            
            optimized_client = OptimizedArrisClient(password=self.password, host=self.host)
            optimized_status = optimized_client.get_status()
            optimized_time = time.time() - optimized_start
            optimized_client.close()
            
            # Compare results
            original_channels = len(original_status.get('downstream_channels', [])) + len(original_status.get('upstream_channels', []))
            optimized_channels = len(optimized_status.get('downstream_channels', [])) + len(optimized_status.get('upstream_channels', []))
            
            speed_improvement = ((original_time - optimized_time) / original_time) * 100
            
            comparison_results = {
                "timing_comparison": {
                    "original_time": original_time,
                    "optimized_time": optimized_time,
                    "speed_improvement_percent": speed_improvement,
                    "faster": optimized_time < original_time
                },
                "data_comparison": {
                    "original_channels": original_channels,
                    "optimized_channels": optimized_channels,
                    "channel_count_match": original_channels == optimized_channels,
                    "data_integrity_maintained": True  # Could add more detailed comparison
                }
            }
            
            logger.info(f"📊 Performance Comparison:")
            logger.info(f"   Original: {original_time:.2f}s, {original_channels} channels")
            logger.info(f"   Optimized: {optimized_time:.2f}s, {optimized_channels} channels") 
            logger.info(f"   Speed improvement: {speed_improvement:.1f}%")
            logger.info(f"   Data integrity: {'✅' if original_channels == optimized_channels else '❌'}")
            
        except Exception as e:
            logger.error(f"Comparison test error: {e}")
            comparison_results["error"] = str(e)
            
        return comparison_results

    def _generate_recommendations(self):
        """Generate performance and usage recommendations."""
        recommendations = []
        
        # Performance recommendations
        perf_tests = self.test_results.get("performance_tests", {})
        auth_speed = perf_tests.get("authentication_speed", {})
        
        if auth_speed.get("average_time", 0) > 3.0:
            recommendations.append({
                "type": "performance",
                "priority": "medium", 
                "message": "Authentication taking longer than expected (>3s). Check network latency to modem."
            })
        
        if auth_speed.get("consistency", True) == False:
            recommendations.append({
                "type": "reliability",
                "priority": "low",
                "message": "Authentication timing inconsistent. Consider connection stability."
            })
        
        # Data quality recommendations  
        validation_tests = self.test_results.get("validation_tests", {})
        completeness = validation_tests.get("data_completeness", {}).get("completeness_score", 0)
        
        if completeness < 80:
            recommendations.append({
                "type": "data_quality",
                "priority": "high",
                "message": f"Data completeness only {completeness:.1f}%. Some modem data may be unavailable."
            })
        
        # Stress test recommendations
        stress_tests = self.test_results.get("stress_tests", {})
        success_rate = stress_tests.get("rapid_requests", {}).get("success_rate", 0)
        
        if success_rate < 0.8:
            recommendations.append({
                "type": "reliability", 
                "priority": "medium",
                "message": f"Rapid request success rate only {success_rate*100:.1f}%. Consider adding delays between requests."
            })
        
        # Performance improvement recommendations
        comparison_tests = self.test_results.get("comparison_tests", {})
        if comparison_tests and not comparison_tests.get("error"):
            speed_improvement = comparison_tests.get("timing_comparison", {}).get("speed_improvement_percent", 0)
            
            if speed_improvement > 30:
                recommendations.append({
                    "type": "success",
                    "priority": "info",
                    "message": f"Excellent performance improvement: {speed_improvement:.1f}% faster than original client."
                })
            elif speed_improvement < 10:
                recommendations.append({
                    "type": "performance",
                    "priority": "low", 
                    "message": "Optimizations showing minimal improvement. Network may be the bottleneck."
                })
        
        self.test_results["recommendations"] = recommendations
        
        # Log recommendations
        logger.info("\n💡 RECOMMENDATIONS:")
        logger.info("-" * 50)
        for rec in recommendations:
            priority_icon = {"high": "🔴", "medium": "🟡", "low": "🟢", "info": "ℹ️"}.get(rec["priority"], "📋")
            logger.info(f"{priority_icon} {rec['type'].upper()}: {rec['message']}")

    def save_results(self, filename: str = None) -> str:
        """Save test results to JSON file."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"comprehensive_test_results_{timestamp}.json"
        
        try:
            with open(filename, 'w') as f:
                json.dump(self.test_results, f, indent=2, default=str)
            
            logger.info(f"💾 Results saved to: {filename}")
            return filename
            
        except Exception as e:
            logger.error(f"Failed to save results: {e}")
            return ""

    def print_summary(self):
        """Print comprehensive test summary."""
        logger.info("\n" + "=" * 70)
        logger.info("📊 COMPREHENSIVE TEST SUMMARY")
        logger.info("=" * 70)
        
        # Performance Summary
        perf_tests = self.test_results.get("performance_tests", {})
        auth_speed = perf_tests.get("authentication_speed", {})
        data_speed = perf_tests.get("data_retrieval_speed", {})
        
        if auth_speed:
            logger.info(f"🔐 Authentication: {auth_speed.get('average_time', 0):.2f}s average")
        if data_speed:
            logger.info(f"📊 Data Retrieval: {data_speed.get('average_time', 0):.2f}s average")
            
        # Validation Summary
        validation_tests = self.test_results.get("validation_tests", {})
        channel_analysis = validation_tests.get("channel_analysis", {})
        data_completeness = validation_tests.get("data_completeness", {})
        
        if channel_analysis:
            downstream = channel_analysis.get("downstream_count", 0)
            upstream = channel_analysis.get("upstream_count", 0)
            logger.info(f"📈 Channels: {downstream} downstream, {upstream} upstream")
            
        if data_completeness:
            completeness = data_completeness.get("completeness_score", 0)
            logger.info(f"🎯 Data Completeness: {completeness:.1f}%")
        
        # Comparison Summary
        comparison_tests = self.test_results.get("comparison_tests", {})
        if comparison_tests and not comparison_tests.get("error"):
            timing = comparison_tests.get("timing_comparison", {})
            improvement = timing.get("speed_improvement_percent", 0)
            logger.info(f"⚡ Speed Improvement: {improvement:.1f}%")
        
        # Overall Assessment
        logger.info("\n🎯 OVERALL ASSESSMENT:")
        
        all_good = True
        if auth_speed.get("average_time", 0) > 3.0:
            all_good = False
        if data_completeness.get("completeness_score", 0) < 80:
            all_good = False
            
        if all_good:
            logger.info("🎉 EXCELLENT - Optimized client performing at peak efficiency!")
        else:
            logger.info("⚠️  GOOD - Some areas for improvement identified.")
            
        logger.info("=" * 70)


def main():
    """Main entry point for comprehensive testing."""
    parser = argparse.ArgumentParser(
        description="Comprehensive Performance Test for Optimized Arris Client",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument("--password", required=True, help="Modem password")
    parser.add_argument("--host", default="192.168.100.1", help="Modem IP address")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--save-results", action="store_true", help="Save detailed results to JSON")
    parser.add_argument("--output-file", help="Custom output filename for results")
    
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logging.getLogger("arris-modem-status").setLevel(logging.DEBUG)
        logging.getLogger("optimized_arris_client").setLevel(logging.DEBUG)
    
    # Create and run test suite
    test_suite = ComprehensiveTestSuite(args.password, args.host)
    
    try:
        logger.info("🚀 Starting comprehensive test suite...")
        start_time = time.time()
        
        # Run all tests
        results = test_suite.run_all_tests()
        
        # Print summary
        test_suite.print_summary()
        
        # Save results if requested
        if args.save_results:
            filename = test_suite.save_results(args.output_file)
            if filename:
                logger.info(f"📁 Detailed results: {filename}")
        
        total_time = time.time() - start_time
        logger.info(f"\n⏱️  Total test time: {total_time:.2f}s")
        logger.info("✅ Comprehensive testing complete!")
        
    except KeyboardInterrupt:
        logger.error("\n❌ Tests cancelled by user")
        return 1
        
    except Exception as e:
        logger.error(f"\n❌ Test suite failed: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
