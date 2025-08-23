"""
Performance Monitoring System
Provides comprehensive performance monitoring, metrics collection, and alerting for services.
"""

import time
import psutil
import threading
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Callable
from collections import defaultdict, deque
from functools import wraps
import logging
import json

logger = logging.getLogger(__name__)


class MetricsCollector:
    """Collects and aggregates performance metrics."""
    
    def __init__(self, max_samples: int = 1000):
        self.max_samples = max_samples
        self._metrics = defaultdict(lambda: {
            'response_times': deque(maxlen=max_samples),
            'error_rates': deque(maxlen=max_samples),
            'request_counts': deque(maxlen=max_samples),
            'memory_usage': deque(maxlen=max_samples),
            'cpu_usage': deque(maxlen=max_samples),
            'last_updated': time.time()
        })
        self._lock = threading.RLock()
    
    def record_request(self, service_name: str, method_name: str, 
                      execution_time: float, success: bool, memory_mb: float = None):
        """Record a service request metric."""
        with self._lock:
            key = f"{service_name}.{method_name}"
            metrics = self._metrics[key]
            
            # Record response time
            metrics['response_times'].append(execution_time)
            
            # Record error rate
            metrics['error_rates'].append(0 if success else 1)
            
            # Record request count
            current_time = time.time()
            metrics['request_counts'].append(current_time)
            
            # Record memory usage if provided
            if memory_mb is not None:
                metrics['memory_usage'].append(memory_mb)
            
            # Record CPU usage
            try:
                cpu_percent = psutil.cpu_percent(interval=0.1)
                metrics['cpu_usage'].append(cpu_percent)
            except Exception as e:
                # Log the error instead of silently passing
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Could not get CPU usage: {e}")
                # Continue with execution even if CPU monitoring fails
            
            metrics['last_updated'] = current_time
    
    def get_metrics_summary(self, service_name: str = None, 
                           time_window: int = 3600) -> Dict[str, Any]:
        """Get aggregated metrics summary."""
        with self._lock:
            summary = {}
            current_time = time.time()
            cutoff_time = current_time - time_window
            
            for key, metrics in self._metrics.items():
                if service_name and not key.startswith(service_name):
                    continue
                
                # Filter metrics by time window
                recent_times = [t for t in metrics['response_times'] if t is not None]
                recent_errors = metrics['error_rates']
                recent_requests = [t for t in metrics['request_counts'] if t >= cutoff_time]
                recent_memory = [m for m in metrics['memory_usage'] if m is not None]
                recent_cpu = [c for c in metrics['cpu_usage'] if c is not None]
                
                if not recent_times:
                    continue
                
                # Calculate statistics
                avg_response_time = sum(recent_times) / len(recent_times)
                p95_response_time = self._percentile(recent_times, 0.95)
                p99_response_time = self._percentile(recent_times, 0.99)
                error_rate = (sum(recent_errors) / len(recent_errors)) * 100 if recent_errors else 0
                requests_per_minute = len(recent_requests) / (time_window / 60)
                
                summary[key] = {
                    'avg_response_time_ms': round(avg_response_time * 1000, 2),
                    'p95_response_time_ms': round(p95_response_time * 1000, 2),
                    'p99_response_time_ms': round(p99_response_time * 1000, 2),
                    'error_rate_percent': round(error_rate, 2),
                    'requests_per_minute': round(requests_per_minute, 2),
                    'total_requests': len(recent_requests),
                    'avg_memory_mb': round(sum(recent_memory) / len(recent_memory), 2) if recent_memory else 0,
                    'avg_cpu_percent': round(sum(recent_cpu) / len(recent_cpu), 2) if recent_cpu else 0,
                    'last_updated': datetime.fromtimestamp(metrics['last_updated']).isoformat()
                }
            
            return summary
    
    def _percentile(self, data: List[float], percentile: float) -> float:
        """Calculate percentile of a dataset."""
        if not data:
            return 0.0
        
        sorted_data = sorted(data)
        index = int(percentile * len(sorted_data))
        if index >= len(sorted_data):
            index = len(sorted_data) - 1
        return sorted_data[index]
    
    def clear_old_metrics(self, max_age_hours: int = 24):
        """Clear metrics older than specified age."""
        with self._lock:
            cutoff_time = time.time() - (max_age_hours * 3600)
            for key in list(self._metrics.keys()):
                metrics = self._metrics[key]
                if metrics['last_updated'] < cutoff_time:
                    del self._metrics[key]


class AlertManager:
    """Manages performance alerts and notifications."""
    
    def __init__(self):
        self._alert_rules = []
        self._alert_history = deque(maxlen=1000)
        self._callbacks = []
        self._lock = threading.RLock()
    
    def add_alert_rule(self, name: str, condition: Callable[[Dict], bool], 
                      severity: str = "warning", cooldown: int = 300):
        """Add an alert rule."""
        with self._lock:
            self._alert_rules.append({
                'name': name,
                'condition': condition,
                'severity': severity,
                'cooldown': cooldown,
                'last_triggered': 0
            })
    
    def add_alert_callback(self, callback: Callable[[Dict], None]):
        """Add callback for when alerts are triggered."""
        self._callbacks.append(callback)
    
    def check_alerts(self, metrics: Dict[str, Any]):
        """Check all alert rules against current metrics."""
        current_time = time.time()
        
        with self._lock:
            for rule in self._alert_rules:
                if current_time - rule['last_triggered'] < rule['cooldown']:
                    continue
                
                try:
                    if rule['condition'](metrics):
                        alert = {
                            'name': rule['name'],
                            'severity': rule['severity'],
                            'timestamp': datetime.now().isoformat(),
                            'metrics': metrics,
                            'message': f"Alert triggered: {rule['name']}"
                        }
                        
                        self._alert_history.append(alert)
                        rule['last_triggered'] = current_time
                        
                        # Notify callbacks
                        for callback in self._callbacks:
                            try:
                                callback(alert)
                            except Exception as e:
                                logger.error(f"Alert callback failed: {e}")
                
                except Exception as e:
                    logger.error(f"Alert rule '{rule['name']}' evaluation failed: {e}")
    
    def get_alert_history(self, limit: int = 100) -> List[Dict]:
        """Get recent alert history."""
        with self._lock:
            return list(self._alert_history)[-limit:]


class PerformanceMonitor:
    """Main performance monitoring system."""
    
    def __init__(self):
        self.metrics_collector = MetricsCollector()
        self.alert_manager = AlertManager()
        self._monitoring_thread = None
        self._monitoring_active = False
        self._system_metrics = {}
        
        # Setup default alert rules
        self._setup_default_alerts()
    
    def start_monitoring(self, interval: int = 60):
        """Start continuous monitoring thread."""
        if self._monitoring_active:
            return
        
        self._monitoring_active = True
        self._monitoring_thread = threading.Thread(
            target=self._monitoring_loop,
            args=(interval,),
            daemon=True
        )
        self._monitoring_thread.start()
        logger.info("Performance monitoring started")
    
    def stop_monitoring(self):
        """Stop monitoring thread."""
        self._monitoring_active = False
        if self._monitoring_thread:
            self._monitoring_thread.join(timeout=5)
        logger.info("Performance monitoring stopped")
    
    def _monitoring_loop(self, interval: int):
        """Main monitoring loop."""
        while self._monitoring_active:
            try:
                # Collect system metrics
                self._collect_system_metrics()
                
                # Get service metrics
                service_metrics = self.metrics_collector.get_metrics_summary()
                
                # Check alerts
                combined_metrics = {
                    'system': self._system_metrics,
                    'services': service_metrics
                }
                self.alert_manager.check_alerts(combined_metrics)
                
                # Clean up old metrics
                self.metrics_collector.clear_old_metrics()
                
            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
            
            time.sleep(interval)
    
    def _collect_system_metrics(self):
        """Collect system-level metrics."""
        try:
            # Memory metrics
            memory = psutil.virtual_memory()
            self._system_metrics['memory'] = {
                'total_gb': round(memory.total / (1024**3), 2),
                'available_gb': round(memory.available / (1024**3), 2),
                'used_percent': memory.percent,
                'free_gb': round(memory.free / (1024**3), 2)
            }
            
            # CPU metrics
            self._system_metrics['cpu'] = {
                'percent': psutil.cpu_percent(interval=1),
                'count': psutil.cpu_count(),
                'load_avg': psutil.getloadavg() if hasattr(psutil, 'getloadavg') else [0, 0, 0]
            }
            
            # Disk metrics
            disk = psutil.disk_usage('/')
            self._system_metrics['disk'] = {
                'total_gb': round(disk.total / (1024**3), 2),
                'used_gb': round(disk.used / (1024**3), 2),
                'free_gb': round(disk.free / (1024**3), 2),
                'used_percent': round((disk.used / disk.total) * 100, 2)
            }
            
            # Process metrics
            process = psutil.Process()
            self._system_metrics['process'] = {
                'memory_mb': round(process.memory_info().rss / (1024**2), 2),
                'cpu_percent': process.cpu_percent(),
                'threads': process.num_threads(),
                'open_files': len(process.open_files()),
                'connections': len(process.connections())
            }
            
        except Exception as e:
            logger.error(f"System metrics collection failed: {e}")
    
    def _setup_default_alerts(self):
        """Setup default alert rules."""
        # High memory usage alert
        self.alert_manager.add_alert_rule(
            "high_memory_usage",
            lambda m: m.get('system', {}).get('memory', {}).get('used_percent', 0) > 85,
            severity="warning"
        )
        
        # High CPU usage alert
        self.alert_manager.add_alert_rule(
            "high_cpu_usage",
            lambda m: m.get('system', {}).get('cpu', {}).get('percent', 0) > 80,
            severity="warning"
        )
        
        # Slow response time alert
        def check_slow_responses(metrics):
            services = metrics.get('services', {})
            for service_name, service_metrics in services.items():
                if service_metrics.get('avg_response_time_ms', 0) > 5000:  # 5 seconds
                    return True
            return False
        
        self.alert_manager.add_alert_rule(
            "slow_response_times",
            check_slow_responses,
            severity="critical"
        )
        
        # High error rate alert
        def check_error_rates(metrics):
            services = metrics.get('services', {})
            for service_name, service_metrics in services.items():
                if service_metrics.get('error_rate_percent', 0) > 5:  # 5% error rate
                    return True
            return False
        
        self.alert_manager.add_alert_rule(
            "high_error_rate",
            check_error_rates,
            severity="critical"
        )
    
    def record_service_call(self, service_name: str, method_name: str,
                           execution_time: float, success: bool):
        """Record a service method call."""
        # Get current memory usage
        try:
            process = psutil.Process()
            memory_mb = process.memory_info().rss / (1024**2)
        except Exception:
            memory_mb = None
        
        self.metrics_collector.record_request(
            service_name, method_name, execution_time, success, memory_mb
        )
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get comprehensive dashboard data."""
        service_metrics = self.metrics_collector.get_metrics_summary()
        alert_history = self.alert_manager.get_alert_history(limit=50)
        
        return {
            'system_metrics': self._system_metrics,
            'service_metrics': service_metrics,
            'alert_history': alert_history,
            'monitoring_status': 'active' if self._monitoring_active else 'inactive',
            'timestamp': datetime.now().isoformat()
        }
    
    def export_metrics(self, format: str = 'json') -> str:
        """Export metrics in specified format."""
        data = self.get_dashboard_data()
        
        if format.lower() == 'json':
            return json.dumps(data, indent=2)
        elif format.lower() == 'prometheus':
            return self._export_prometheus_format(data)
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    def _export_prometheus_format(self, data: Dict) -> str:
        """Export metrics in Prometheus format."""
        lines = []
        
        # System metrics
        system = data.get('system_metrics', {})
        if 'memory' in system:
            lines.append(f"system_memory_used_percent {system['memory']['used_percent']}")
            lines.append(f"system_memory_available_gb {system['memory']['available_gb']}")
        
        if 'cpu' in system:
            lines.append(f"system_cpu_percent {system['cpu']['percent']}")
        
        if 'disk' in system:
            lines.append(f"system_disk_used_percent {system['disk']['used_percent']}")
        
        # Service metrics
        services = data.get('service_metrics', {})
        for service_name, metrics in services.items():
            service_name = service_name.replace('.', '_')
            lines.append(f"service_response_time_avg_ms{{service=\"{service_name}\"}} {metrics['avg_response_time_ms']}")
            lines.append(f"service_error_rate_percent{{service=\"{service_name}\"}} {metrics['error_rate_percent']}")
            lines.append(f"service_requests_per_minute{{service=\"{service_name}\"}} {metrics['requests_per_minute']}")
        
        return '\n'.join(lines)


# Global performance monitor instance
_performance_monitor = PerformanceMonitor()


def get_performance_monitor() -> PerformanceMonitor:
    """Get the global performance monitor instance."""
    return _performance_monitor


def performance_tracker(service_name: str):
    """Decorator to automatically track service method performance."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            success = True
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                raise
            finally:
                execution_time = time.perf_counter() - start_time
                _performance_monitor.record_service_call(
                    service_name, func.__name__, execution_time, success
                )
        return wrapper
    return decorator


def log_alert(alert: Dict):
    """Default alert callback that logs alerts."""
    logger.warning(f"PERFORMANCE ALERT: {alert['name']} - {alert['message']}")


# Setup default alert callback
_performance_monitor.alert_manager.add_alert_callback(log_alert)