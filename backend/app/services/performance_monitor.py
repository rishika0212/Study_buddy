"""
Response time monitoring middleware for tracking performance against targets.

Monitors:
- Response times per endpoint
- Response times per task type
- Cache hit rates
- Queue depths for background tasks
"""

import time
from typing import Dict, Any, List
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from collections import defaultdict
import json
import os
from backend.app.config import settings
from backend.app.utils.logger import logger


@dataclass
class ResponseMetric:
    """Single response time metric."""
    timestamp: str
    endpoint: str
    method: str
    status_code: int
    response_time_ms: float
    task_type: str = None
    cache_hit: bool = False
    streaming: bool = False
    error: str = None


class PerformanceMonitor:
    """Monitors response times and performance metrics."""
    
    # Performance targets (milliseconds)
    TARGETS = {
        "simple_queries": 500,      # view progress, list topics
        "explanations": 2000,       # 2 seconds
        "question_gen": 3000,       # 3 seconds
        "mcq_eval": 1000,          # 1 second
        "qna_eval": 3000,          # 3 seconds
        "session_load": 1000,      # 1 second
    }

    def __init__(self):
        self.metrics: List[ResponseMetric] = []
        self.metrics_dir = os.path.join(settings.USER_DATA_DIRECTORY, "performance_metrics")
        os.makedirs(self.metrics_dir, exist_ok=True)
        self.metrics_file = os.path.join(self.metrics_dir, "metrics.jsonl")
        self.cache_stats = defaultdict(lambda: {"hits": 0, "misses": 0})
        self.endpoint_stats = defaultdict(list)
        self._load_metrics()

    def _load_metrics(self):
        """Load metrics from disk."""
        if os.path.exists(self.metrics_file):
            try:
                with open(self.metrics_file, "r") as f:
                    for line in f:
                        if line.strip():
                            data = json.loads(line)
                            self.metrics.append(ResponseMetric(**data))
                logger.info(f"Loaded {len(self.metrics)} performance metrics")
            except Exception as e:
                logger.error(f"Error loading metrics: {e}")

    def _save_metrics(self):
        """Save metrics to disk (append mode)."""
        try:
            with open(self.metrics_file, "a") as f:
                for metric in self.metrics[-10:]:  # Save last 10 metrics
                    f.write(json.dumps(asdict(metric)) + "\n")
        except Exception as e:
            logger.error(f"Error saving metrics: {e}")

    def record_response(
        self,
        endpoint: str,
        method: str,
        response_time_ms: float,
        status_code: int = 200,
        task_type: str = None,
        cache_hit: bool = False,
        streaming: bool = False,
        error: str = None
    ):
        """Record a response metric."""
        metric = ResponseMetric(
            timestamp=datetime.now().isoformat(),
            endpoint=endpoint,
            method=method,
            status_code=status_code,
            response_time_ms=response_time_ms,
            task_type=task_type,
            cache_hit=cache_hit,
            streaming=streaming,
            error=error
        )
        
        self.metrics.append(metric)
        self.endpoint_stats[endpoint].append(metric)
        
        # Check if exceeded target
        target = self._get_target_for_endpoint(endpoint)
        if target and response_time_ms > target:
            logger.warning(
                f"Slow response: {endpoint} took {response_time_ms}ms "
                f"(target: {target}ms)"
            )
        else:
            logger.info(
                f"Response recorded: {endpoint} {response_time_ms}ms "
                f"(cache_hit={cache_hit}, streaming={streaming})"
            )
        
        self._save_metrics()

    def record_cache_hit(self, cache_type: str):
        """Record a cache hit."""
        self.cache_stats[cache_type]["hits"] += 1

    def record_cache_miss(self, cache_type: str):
        """Record a cache miss."""
        self.cache_stats[cache_type]["misses"] += 1

    def get_cache_stats(self) -> Dict[str, Dict[str, int]]:
        """Get cache hit/miss statistics."""
        stats = {}
        for cache_type, counts in self.cache_stats.items():
            total = counts["hits"] + counts["misses"]
            hit_rate = (counts["hits"] / total * 100) if total > 0 else 0
            stats[cache_type] = {
                **counts,
                "total": total,
                "hit_rate_percent": round(hit_rate, 2)
            }
        return stats

    def get_endpoint_stats(self, endpoint: str = None) -> Dict[str, Any]:
        """
        Get performance statistics for endpoint(s).
        
        Args:
            endpoint: Specific endpoint to analyze, or None for all
        
        Returns:
            Dict with statistics
        """
        if endpoint:
            metrics = self.endpoint_stats.get(endpoint, [])
            return self._calculate_stats(metrics, endpoint)
        else:
            all_stats = {}
            for ep, metrics in self.endpoint_stats.items():
                all_stats[ep] = self._calculate_stats(metrics, ep)
            return all_stats

    def _calculate_stats(self, metrics: List[ResponseMetric], endpoint: str) -> Dict[str, Any]:
        """Calculate statistics for a list of metrics."""
        if not metrics:
            return {"endpoint": endpoint, "metrics_count": 0}
        
        times = [m.response_time_ms for m in metrics]
        cache_hits = sum(1 for m in metrics if m.cache_hit)
        errors = sum(1 for m in metrics if m.error)
        
        times.sort()
        
        return {
            "endpoint": endpoint,
            "metrics_count": len(metrics),
            "avg_response_time_ms": round(sum(times) / len(times), 2),
            "min_response_time_ms": times[0],
            "max_response_time_ms": times[-1],
            "p50_ms": times[len(times) // 2],
            "p95_ms": times[int(len(times) * 0.95)],
            "p99_ms": times[int(len(times) * 0.99)] if len(times) > 100 else None,
            "cache_hits": cache_hits,
            "cache_hit_rate_percent": round(cache_hits / len(metrics) * 100, 2),
            "errors": errors,
            "target_ms": self._get_target_for_endpoint(endpoint),
            "meets_target": self._check_meets_target(times, endpoint),
        }

    def get_performance_summary(self) -> Dict[str, Any]:
        """Get overall performance summary."""
        endpoint_stats = self.get_endpoint_stats()
        cache_stats = self.get_cache_stats()
        
        # Calculate overall metrics
        all_times = [m.response_time_ms for m in self.metrics]
        
        if not all_times:
            return {"summary": "No metrics collected yet"}
        
        meeting_targets = sum(
            1 for endpoint, stats in endpoint_stats.items()
            if stats.get("meets_target", False)
        )
        
        return {
            "total_requests": len(self.metrics),
            "endpoints_tracked": len(endpoint_stats),
            "endpoints_meeting_targets": meeting_targets,
            "overall_avg_response_time_ms": round(sum(all_times) / len(all_times), 2),
            "overall_p95_ms": sorted(all_times)[int(len(all_times) * 0.95)],
            "cache_stats": cache_stats,
            "endpoint_stats": endpoint_stats,
        }

    def _get_target_for_endpoint(self, endpoint: str) -> int:
        """Get performance target for an endpoint."""
        endpoint_lower = endpoint.lower()
        
        if "chat" in endpoint_lower or "message" in endpoint_lower:
            return self.TARGETS["explanations"]
        elif "mcq" in endpoint_lower or "assessment" in endpoint_lower:
            if "generate" in endpoint_lower:
                return self.TARGETS["question_gen"]
            elif "submit" in endpoint_lower:
                return self.TARGETS["mcq_eval"]
        elif "qna" in endpoint_lower:
            if "generate" in endpoint_lower:
                return self.TARGETS["question_gen"]
            elif "submit" in endpoint_lower:
                return self.TARGETS["qna_eval"]
        elif "session" in endpoint_lower or "user" in endpoint_lower:
            return self.TARGETS["session_load"]
        elif "progress" in endpoint_lower or "topics" in endpoint_lower:
            return self.TARGETS["simple_queries"]
        
        return 2000  # Default 2s

    def _check_meets_target(self, times: List[float], endpoint: str) -> bool:
        """Check if response times meet target."""
        if not times:
            return True
        
        target = self._get_target_for_endpoint(endpoint)
        p95 = times[int(len(times) * 0.95)]
        
        return p95 <= target

    def export_metrics_csv(self, filepath: str = None) -> str:
        """Export metrics to CSV."""
        if filepath is None:
            filepath = os.path.join(self.metrics_dir, "metrics_export.csv")
        
        try:
            import csv
            with open(filepath, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=[
                    "timestamp", "endpoint", "method", "status_code",
                    "response_time_ms", "task_type", "cache_hit", "error"
                ])
                writer.writeheader()
                for metric in self.metrics:
                    writer.writerow(asdict(metric))
            
            logger.info(f"Exported {len(self.metrics)} metrics to {filepath}")
            return filepath
        
        except Exception as e:
            logger.error(f"Error exporting metrics: {e}")
            return None


# Global instance
_performance_monitor = None


def get_performance_monitor() -> PerformanceMonitor:
    """Get or create global performance monitor."""
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor()
    return _performance_monitor


# Context manager for timing responses
class TimedResponse:
    """Context manager for timing responses."""
    
    def __init__(self, endpoint: str, method: str = "POST"):
        self.endpoint = endpoint
        self.method = method
        self.start_time = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        response_time_ms = (time.time() - self.start_time) * 1000
        status_code = 500 if exc_type else 200
        error = str(exc_type.__name__) if exc_type else None
        
        monitor = get_performance_monitor()
        monitor.record_response(
            endpoint=self.endpoint,
            method=self.method,
            response_time_ms=response_time_ms,
            status_code=status_code,
            error=error
        )
