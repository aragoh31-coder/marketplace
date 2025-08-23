"""
Service Manager
Coordinates services and provides high-level service operations.
"""

import logging
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Type

from ..architecture.exceptions import ServiceError, ServiceNotFoundError
from .base_service import BaseService
from .service_registry import ServiceRegistry

logger = logging.getLogger(__name__)


class ServiceManager:
    """
    Manages the lifecycle and coordination of services in the system.
    """

    def __init__(self):
        """Initialize the service manager."""
        self._monitoring = False
        self._monitor_thread = None
        self._health_check_interval = 60  # seconds
        self._service_callbacks: Dict[str, List[Callable]] = {}
        self._circuit_breakers: Dict[str, Dict[str, Any]] = {}

    def start_monitoring(self, interval: int = None) -> None:
        """Start monitoring services for health and availability."""
        if self._monitoring:
            logger.warning("Service monitoring is already running")
            return

        if interval:
            self._health_check_interval = interval

        self._monitoring = True
        self._monitor_thread = threading.Thread(target=self._monitor_services, daemon=True)
        self._monitor_thread.start()

        logger.info(f"Started service monitoring with {self._health_check_interval}s interval")

    def stop_monitoring(self) -> None:
        """Stop monitoring services."""
        if not self._monitoring:
            return

        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)

        logger.info("Stopped service monitoring")

    def _monitor_services(self) -> None:
        """Monitor services in a background thread."""
        while self._monitoring:
            try:
                self._check_all_services()
                time.sleep(self._health_check_interval)
            except Exception as e:
                logger.error(f"Service monitoring error: {e}")
                time.sleep(10)  # Wait before retrying

    def _check_all_services(self) -> None:
        """Check health of all services."""
        services = ServiceRegistry.get_all_services()

        for service_name, service in services.items():
            try:
                # Get current health status
                old_healthy = getattr(service, "_last_known_healthy", None)
                current_health = service.get_health_status()
                current_healthy = current_health["healthy"]

                # Check if health status changed
                if old_healthy is not None and old_healthy != current_healthy:
                    self._notify_service_health_change(service_name, current_healthy)

                # Update last known health status
                service._last_known_healthy = current_healthy

                # Update circuit breaker if needed
                self._update_circuit_breaker(service_name, current_healthy)

            except Exception as e:
                logger.error(f"Health check failed for service {service_name}: {e}")
                self._update_circuit_breaker(service_name, False)

    def _notify_service_health_change(self, service_name: str, healthy: bool) -> None:
        """Notify callbacks about service health changes."""
        if service_name in self._service_callbacks:
            for callback in self._service_callbacks[service_name]:
                try:
                    callback(service_name, healthy)
                except Exception as e:
                    logger.error(f"Service callback error for {service_name}: {e}")

    def _update_circuit_breaker(self, service_name: str, healthy: bool) -> None:
        """Update circuit breaker state for a service."""
        if service_name not in self._circuit_breakers:
            self._circuit_breakers[service_name] = {
                "failure_count": 0,
                "success_count": 0,
                "state": "CLOSED",  # CLOSED, OPEN, HALF_OPEN
                "last_failure_time": 0,
                "threshold": 5,  # Number of failures before opening
                "timeout": 60,  # Seconds to wait before half-opening
            }

        cb = self._circuit_breakers[service_name]
        current_time = time.time()

        if healthy:
            cb["success_count"] += 1
            cb["failure_count"] = 0

            if cb["state"] == "HALF_OPEN":
                cb["state"] = "CLOSED"
                logger.info(f"Circuit breaker for {service_name} closed (service recovered)")
        else:
            cb["failure_count"] += 1
            cb["last_failure_time"] = current_time

            if cb["failure_count"] >= cb["threshold"] and cb["state"] == "CLOSED":
                cb["state"] = "OPEN"
                logger.warning(f"Circuit breaker for {service_name} opened (too many failures)")

    def register_service_callback(self, service_name: str, callback: Callable) -> None:
        """Register a callback for service health changes."""
        if service_name not in self._service_callbacks:
            self._service_callbacks[service_name] = []

        self._service_callbacks[service_name].append(callback)
        logger.info(f"Registered callback for service {service_name}")

    def unregister_service_callback(self, service_name: str, callback: Callable) -> None:
        """Unregister a callback for service health changes."""
        if service_name in self._service_callbacks:
            try:
                self._service_callbacks[service_name].remove(callback)
                logger.info(f"Unregistered callback for service {service_name}")
            except ValueError:
                logger.warning(f"Callback not found for service {service_name}")

    def get_circuit_breaker_state(self, service_name: str) -> Dict[str, Any]:
        """Get circuit breaker state for a service."""
        return self._circuit_breakers.get(service_name, {}).copy()

    def is_service_available(self, service_name: str) -> bool:
        """Check if a service is available (considering circuit breaker)."""
        service = ServiceRegistry.get_service(service_name)
        if not service:
            return False

        # Check circuit breaker state
        cb = self._circuit_breakers.get(service_name, {})
        if cb.get("state") == "OPEN":
            # Check if timeout has passed
            if time.time() - cb.get("last_failure_time", 0) > cb.get("timeout", 60):
                cb["state"] = "HALF_OPEN"
                logger.info(f"Circuit breaker for {service_name} half-opened")
            else:
                return False

        return service.is_available()

    def call_service_with_fallback(
        self, service_name: str, operation: str, fallback_service: str = None, *args, **kwargs
    ) -> Any:
        """
        Call a service operation with fallback support.

        Args:
            service_name: Primary service to call
            operation: Operation to perform
            fallback_service: Fallback service if primary fails
            *args: Arguments for the operation
            **kwargs: Keyword arguments for the operation

        Returns:
            Result of the operation

        Raises:
            ServiceError: If both primary and fallback services fail
        """
        # Try primary service
        try:
            if self.is_service_available(service_name):
                service = ServiceRegistry.get_service(service_name)
                if hasattr(service, operation):
                    method = getattr(service, operation)
                    return method(*args, **kwargs)
                else:
                    raise ServiceError(f"Operation {operation} not found on service {service_name}")
            else:
                raise ServiceError(f"Service {service_name} is not available")
        except Exception as e:
            logger.warning(f"Primary service {service_name} failed: {e}")

            # Try fallback service
            if fallback_service:
                try:
                    if self.is_service_available(fallback_service):
                        service = ServiceRegistry.get_service(fallback_service)
                        if hasattr(service, operation):
                            method = getattr(service, operation)
                            logger.info(f"Using fallback service {fallback_service}")
                            return method(*args, **kwargs)
                        else:
                            raise ServiceError(
                                f"Operation {operation} not found on fallback service {fallback_service}"
                            )
                    else:
                        raise ServiceError(f"Fallback service {fallback_service} is not available")
                except Exception as fallback_error:
                    logger.error(f"Fallback service {fallback_service} also failed: {fallback_error}")
                    raise ServiceError(f"Both primary and fallback services failed: {e}, {fallback_error}")
            else:
                raise ServiceError(f"Primary service failed and no fallback available: {e}")

    def get_service_dependencies_graph(self) -> Dict[str, List[str]]:
        """Get a graph of service dependencies."""
        # This is a simplified implementation
        # In a real system, you might want to track actual service dependencies
        return ServiceRegistry.get_service_dependencies()

    def validate_service_architecture(self) -> Dict[str, Any]:
        """Validate the overall service architecture."""
        issues = ServiceRegistry.validate_service_dependencies()
        health_summary = ServiceRegistry.get_service_health_summary()

        # Check for circular dependencies
        dependencies = self.get_service_dependencies_graph()
        circular_deps = self._detect_circular_dependencies(dependencies)

        # Check for orphaned services
        orphaned_services = self._find_orphaned_services(dependencies)

        return {
            "issues": issues,
            "health_summary": health_summary,
            "circular_dependencies": circular_deps,
            "orphaned_services": orphaned_services,
            "overall_status": "HEALTHY" if not issues and health_summary["overall_health"] > 0.8 else "DEGRADED",
        }

    def _detect_circular_dependencies(self, dependencies: Dict[str, List[str]]) -> List[List[str]]:
        """Detect circular dependencies in the service graph."""
        # Simple implementation - in production you might want a more sophisticated algorithm
        circular = []
        visited = set()

        def dfs(service: str, path: List[str]):
            if service in path:
                circular.append(path[path.index(service) :] + [service])
                return

            if service in visited:
                return

            visited.add(service)
            path.append(service)

            for dep in dependencies.get(service, []):
                dfs(dep, path.copy())

        for service in dependencies:
            if service not in visited:
                dfs(service, [])

        return circular

    def _find_orphaned_services(self, dependencies: Dict[str, List[str]]) -> List[str]:
        """Find services that are not depended upon by any other service."""
        all_deps = set()
        for deps in dependencies.values():
            all_deps.update(deps)

        return [service for service in dependencies if service not in all_deps]

    def get_service_metrics_summary(self) -> Dict[str, Any]:
        """Get a summary of all service metrics."""
        metrics = ServiceRegistry.get_service_metrics()

        # Aggregate metrics
        total_requests = 0
        total_errors = 0
        total_cache_hits = 0
        total_cache_misses = 0

        for service_metrics in metrics.values():
            if isinstance(service_metrics, dict):
                total_requests += service_metrics.get("request_count", 0)
                total_errors += service_metrics.get("error_count", 0)
                total_cache_hits += service_metrics.get("cache_hits", 0)
                total_cache_misses += service_metrics.get("cache_misses", 0)

        cache_hit_rate = (
            total_cache_hits / (total_cache_hits + total_cache_misses)
            if (total_cache_hits + total_cache_misses) > 0
            else 0
        )
        error_rate = total_errors / total_requests if total_requests > 0 else 0

        return {
            "total_requests": total_requests,
            "total_errors": total_errors,
            "total_cache_hits": total_cache_hits,
            "total_cache_misses": total_cache_misses,
            "cache_hit_rate": cache_hit_rate,
            "error_rate": error_rate,
            "service_count": len(metrics),
            "detailed_metrics": metrics,
        }

    def shutdown(self) -> None:
        """Shutdown the service manager."""
        logger.info("Shutting down service manager...")

        # Stop monitoring
        self.stop_monitoring()

        # Clear callbacks
        self._service_callbacks.clear()

        # Clear circuit breakers
        self._circuit_breakers.clear()

        logger.info("Service manager shutdown complete")


# Global service manager instance
service_manager = ServiceManager()
