"""
Support Service
Handles all support-related business logic and operations.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import models, transaction
from django.utils import timezone

from .base_service import BaseService

logger = logging.getLogger(__name__)
User = get_user_model()


class SupportService(BaseService):
    """Service for managing support tickets and operations."""

    service_name = "support_service"
    version = "1.0.0"
    description = "Support ticket management service"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._ticket_cache = {}
        self._category_cache = {}

    def initialize(self) -> bool:
        """Initialize the support service."""
        try:
            # Set up any connections or validate configuration
            logger.info("Support service initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize support service: {e}")
            return False

    def cleanup(self) -> bool:
        """Clean up the support service."""
        try:
            # Clear caches
            self._ticket_cache.clear()
            self._category_cache.clear()
            logger.info("Support service cleaned up successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to cleanup support service: {e}")
            return False

    def get_required_config(self) -> List[str]:
        """Get required configuration keys."""
        return ["max_ticket_attachments", "ticket_response_timeout_hours"]

    def get_ticket_by_id(self, ticket_id: str) -> Optional[Any]:
        """Get support ticket by ID with caching."""
        cache_key = f"ticket:{ticket_id}"

        # Try cache first
        cached_ticket = self.get_cached(cache_key)
        if cached_ticket:
            return cached_ticket

        try:
            from support.models import SupportTicket

            ticket = SupportTicket.objects.get(id=ticket_id)

            # Cache ticket for 5 minutes
            self.set_cached(cache_key, ticket, timeout=300)
            return ticket

        except Exception as e:
            logger.error(f"Failed to get ticket {ticket_id}: {e}")
            return None

    def create_ticket(
        self, user_id: str, subject: str, description: str, category: str, priority: str = "medium", **kwargs
    ) -> Tuple[Any, bool, str]:
        """Create a new support ticket."""
        try:
            from support.models import SupportTicket

            with transaction.atomic():
                # Validate priority
                valid_priorities = ["low", "medium", "high", "urgent"]
                if priority not in valid_priorities:
                    return None, False, f"Invalid priority. Must be one of: {', '.join(valid_priorities)}"

                # Create ticket
                ticket = SupportTicket.objects.create(
                    user_id=user_id,
                    subject=subject,
                    description=description,
                    category=category,
                    priority=priority,
                    status="open",
                    **kwargs,
                )

                # Clear caches
                self.clear_cache(f"user_tickets:{user_id}")

                logger.info(f"Support ticket created successfully: {ticket.id} by user {user_id}")
                return ticket, True, "Support ticket created successfully"

        except Exception as e:
            logger.error(f"Failed to create support ticket for user {user_id}: {e}")
            return None, False, str(e)

    def update_ticket_status(
        self, ticket_id: str, new_status: str, admin_user_id: str = None, notes: str = ""
    ) -> Tuple[bool, str]:
        """Update ticket status."""
        try:
            ticket = self.get_ticket_by_id(ticket_id)
            if not ticket:
                return False, "Ticket not found"

            # Validate status transition
            valid_transitions = self._get_valid_status_transitions(ticket.status)
            if new_status not in valid_transitions:
                return False, f"Invalid status transition from {ticket.status} to {new_status}"

            with transaction.atomic():
                old_status = ticket.status
                ticket.status = new_status

                # Update status-specific fields
                if new_status == "in_progress":
                    ticket.assigned_to_id = admin_user_id
                    ticket.started_at = timezone.now()
                elif new_status == "resolved":
                    ticket.resolved_at = timezone.now()
                    ticket.resolved_by_id = admin_user_id
                elif new_status == "closed":
                    ticket.closed_at = timezone.now()
                    ticket.closed_by_id = admin_user_id

                ticket.save()

                # Log status change
                self._log_ticket_status_change(ticket_id, old_status, new_status, admin_user_id, notes)

                # Clear caches
                self.clear_cache(f"ticket:{ticket_id}")
                self.clear_cache(f"user_tickets:{ticket.user_id}")

                logger.info(f"Ticket {ticket_id} status updated: {old_status} -> {new_status}")
                return True, f"Ticket status updated to {new_status}"

        except Exception as e:
            logger.error(f"Failed to update ticket status for {ticket_id}: {e}")
            return False, str(e)

    def _get_valid_status_transitions(self, current_status: str) -> List[str]:
        """Get valid status transitions from current status."""
        transitions = {
            "open": ["in_progress", "closed"],
            "in_progress": ["resolved", "closed"],
            "resolved": ["closed"],
            "closed": [],  # Final state
        }
        return transitions.get(current_status, [])

    def add_ticket_response(
        self, ticket_id: str, user_id: str, content: str, is_internal: bool = False, **kwargs
    ) -> Tuple[Any, bool, str]:
        """Add a response to a support ticket."""
        try:
            from support.models import TicketResponse

            ticket = self.get_ticket_by_id(ticket_id)
            if not ticket:
                return None, False, "Ticket not found"

            # Check if user can respond to this ticket
            if not is_internal and str(user_id) != str(ticket.user_id):
                return None, False, "You can only respond to your own tickets"

            with transaction.atomic():
                # Create response
                response = TicketResponse.objects.create(
                    ticket_id=ticket_id, user_id=user_id, content=content, is_internal=is_internal, **kwargs
                )

                # Update ticket
                ticket.last_response_at = timezone.now()
                ticket.last_response_by_id = user_id
                ticket.response_count += 1

                # If user responded, mark as waiting for staff
                if not is_internal:
                    ticket.status = "waiting_for_staff"

                ticket.save()

                # Clear caches
                self.clear_cache(f"ticket:{ticket_id}")
                self.clear_cache(f"user_tickets:{ticket.user_id}")

                logger.info(f"Response added to ticket {ticket_id} by user {user_id}")
                return response, True, "Response added successfully"

        except Exception as e:
            logger.error(f"Failed to add response to ticket {ticket_id}: {e}")
            return None, False, str(e)

    def get_ticket_responses(self, ticket_id: str, include_internal: bool = False) -> List[Dict[str, Any]]:
        """Get responses for a support ticket."""
        try:
            from support.models import TicketResponse

            queryset = TicketResponse.objects.filter(ticket_id=ticket_id)

            if not include_internal:
                queryset = queryset.filter(is_internal=False)

            responses = queryset.order_by("created_at")

            return [
                {
                    "id": str(r.id),
                    "user_id": str(r.user_id),
                    "content": r.content,
                    "is_internal": r.is_internal,
                    "created_at": r.created_at.isoformat(),
                    "metadata": r.metadata if hasattr(r, "metadata") else {},
                }
                for r in responses
            ]

        except Exception as e:
            logger.error(f"Failed to get responses for ticket {ticket_id}: {e}")
            return []

    def get_user_tickets(self, user_id: str, **filters) -> List[Any]:
        """Get support tickets for a user with optional filters."""
        try:
            from support.models import SupportTicket

            queryset = SupportTicket.objects.filter(user_id=user_id)

            # Apply filters
            if filters.get("status"):
                queryset = queryset.filter(status=filters["status"])

            if filters.get("category"):
                queryset = queryset.filter(category=filters["category"])

            if filters.get("priority"):
                queryset = queryset.filter(priority=filters["priority"])

            if filters.get("active_only", False):
                queryset = queryset.exclude(status__in=["resolved", "closed"])

            # Order by creation date
            tickets = queryset.order_by("-created_at")

            # Apply limit if specified
            if filters.get("limit"):
                tickets = tickets[: filters["limit"]]

            return list(tickets)

        except Exception as e:
            logger.error(f"Failed to get tickets for user {user_id}: {e}")
            return []

    def get_all_tickets(self, **filters) -> List[Any]:
        """Get all support tickets with optional filters (admin function)."""
        try:
            from support.models import SupportTicket

            queryset = SupportTicket.objects.all()

            # Apply filters
            if filters.get("status"):
                queryset = queryset.filter(status=filters["status"])

            if filters.get("category"):
                queryset = queryset.filter(category=filters["category"])

            if filters.get("priority"):
                queryset = queryset.filter(priority=filters["priority"])

            if filters.get("assigned_to"):
                queryset = queryset.filter(assigned_to_id=filters["assigned_to"])

            if filters.get("date_from"):
                queryset = queryset.filter(created_at__gte=filters["date_from"])

            if filters.get("date_to"):
                queryset = queryset.filter(created_at__lte=filters["date_to"])

            # Order by priority and creation date
            tickets = queryset.order_by("-priority", "-created_at")

            # Apply limit if specified
            if filters.get("limit"):
                tickets = tickets[: filters["limit"]]

            return list(tickets)

        except Exception as e:
            logger.error(f"Failed to get all tickets: {e}")
            return []

    def assign_ticket(self, ticket_id: str, admin_user_id: str) -> Tuple[bool, str]:
        """Assign a ticket to an admin user."""
        try:
            ticket = self.get_ticket_by_id(ticket_id)
            if not ticket:
                return False, "Ticket not found"

            # Check if ticket is already assigned
            if ticket.assigned_to_id and str(ticket.assigned_to_id) == str(admin_user_id):
                return False, "Ticket is already assigned to you"

            with transaction.atomic():
                ticket.assigned_to_id = admin_user_id
                ticket.assigned_at = timezone.now()

                # Update status if it was open
                if ticket.status == "open":
                    ticket.status = "in_progress"
                    ticket.started_at = timezone.now()

                ticket.save()

                # Clear caches
                self.clear_cache(f"ticket:{ticket_id}")

                logger.info(f"Ticket {ticket_id} assigned to admin {admin_user_id}")
                return True, "Ticket assigned successfully"

        except Exception as e:
            logger.error(f"Failed to assign ticket {ticket_id}: {e}")
            return False, str(e)

    def get_ticket_categories(self) -> List[str]:
        """Get all available ticket categories."""
        try:
            from support.models import SupportTicket

            categories = SupportTicket.objects.values_list("category", flat=True).distinct()
            return list(categories)

        except Exception as e:
            logger.error(f"Failed to get ticket categories: {e}")
            return []

    def get_ticket_summary(self, ticket_id: str) -> Dict[str, Any]:
        """Get comprehensive ticket summary."""
        try:
            ticket = self.get_ticket_by_id(ticket_id)
            if not ticket:
                return {}

            # Get responses
            responses = self.get_ticket_responses(ticket_id, include_internal=True)

            return {
                "id": str(ticket.id),
                "user_id": str(ticket.user_id),
                "subject": ticket.subject,
                "description": ticket.description,
                "category": ticket.category,
                "priority": ticket.priority,
                "status": ticket.status,
                "assigned_to_id": str(ticket.assigned_to_id) if ticket.assigned_to_id else None,
                "responses": responses,
                "response_count": ticket.response_count,
                "created_at": ticket.created_at.isoformat(),
                "updated_at": ticket.updated_at.isoformat() if hasattr(ticket, "updated_at") else None,
                "started_at": (
                    ticket.started_at.isoformat() if hasattr(ticket, "started_at") and ticket.started_at else None
                ),
                "resolved_at": (
                    ticket.resolved_at.isoformat() if hasattr(ticket, "resolved_at") and ticket.resolved_at else None
                ),
                "closed_at": (
                    ticket.closed_at.isoformat() if hasattr(ticket, "closed_at") and ticket.closed_at else None
                ),
                "last_response_at": (
                    ticket.last_response_at.isoformat()
                    if hasattr(ticket, "last_response_at") and ticket.last_response_at
                    else None
                ),
            }

        except Exception as e:
            logger.error(f"Failed to get ticket summary for {ticket_id}: {e}")
            return {}

    def get_support_statistics(self, user_id: str = None) -> Dict[str, Any]:
        """Get support statistics."""
        try:
            from support.models import SupportTicket

            queryset = SupportTicket.objects.all()

            if user_id:
                queryset = queryset.filter(user_id=user_id)

            total_tickets = queryset.count()
            open_tickets = queryset.filter(status="open").count()
            in_progress = queryset.filter(status="in_progress").count()
            resolved_tickets = queryset.filter(status="resolved").count()
            closed_tickets = queryset.filter(status="closed").count()

            # Priority distribution
            priority_counts = {}
            for priority in ["low", "medium", "high", "urgent"]:
                priority_counts[priority] = queryset.filter(priority=priority).count()

            # Category distribution
            category_counts = {}
            for category in queryset.values_list("category", flat=True).distinct():
                category_counts[category] = queryset.filter(category=category).count()

            # Monthly trends (last 12 months)
            monthly_trends = {}
            for i in range(12):
                month_start = timezone.now().replace(day=1) - timezone.timedelta(days=30 * i)
                month_end = month_start.replace(day=28) + timezone.timedelta(days=4)
                month_end = month_end.replace(day=1) - timezone.timedelta(days=1)

                month_tickets = queryset.filter(created_at__gte=month_start, created_at__lte=month_end)

                monthly_trends[month_start.strftime("%Y-%m")] = {
                    "tickets": month_tickets.count(),
                    "resolved": month_tickets.filter(status="resolved").count(),
                }

            return {
                "total_tickets": total_tickets,
                "status_distribution": {
                    "open": open_tickets,
                    "in_progress": in_progress,
                    "resolved": resolved_tickets,
                    "closed": closed_tickets,
                },
                "priority_distribution": priority_counts,
                "category_distribution": category_counts,
                "monthly_trends": monthly_trends,
            }

        except Exception as e:
            logger.error(f"Failed to get support statistics: {e}")
            return {}

    def search_tickets(self, query: str = "", user_id: str = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Search support tickets."""
        try:
            from support.models import SupportTicket

            queryset = SupportTicket.objects.all()

            if user_id:
                queryset = queryset.filter(user_id=user_id)

            # Apply search query
            if query:
                queryset = queryset.filter(
                    models.Q(subject__icontains=query)
                    | models.Q(description__icontains=query)
                    | models.Q(category__icontains=query)
                )

            # Order by priority and creation date
            tickets = queryset.order_by("-priority", "-created_at")[:limit]

            return [
                {
                    "id": str(t.id),
                    "user_id": str(t.user_id),
                    "subject": t.subject,
                    "category": t.category,
                    "priority": t.priority,
                    "status": t.status,
                    "created_at": t.created_at.isoformat(),
                    "response_count": t.response_count,
                }
                for t in tickets
            ]

        except Exception as e:
            logger.error(f"Failed to search tickets: {e}")
            return []

    def _log_ticket_status_change(
        self, ticket_id: str, old_status: str, new_status: str, admin_user_id: str = None, notes: str = ""
    ) -> None:
        """Log ticket status change for audit purposes."""
        try:
            from support.models import TicketStatusLog

            TicketStatusLog.objects.create(
                ticket_id=ticket_id,
                old_status=old_status,
                new_status=new_status,
                changed_by_id=admin_user_id,
                notes=notes,
                timestamp=timezone.now(),
            )

        except Exception as e:
            logger.error(f"Failed to log ticket status change: {e}")

    def get_service_health(self) -> Dict[str, Any]:
        """Get service health status."""
        try:
            from support.models import SupportTicket

            total_tickets = SupportTicket.objects.count()
            open_tickets = SupportTicket.objects.filter(status="open").count()
            in_progress = SupportTicket.objects.filter(status="in_progress").count()
            urgent_tickets = SupportTicket.objects.filter(priority="urgent").count()

            return {
                "total_tickets": total_tickets,
                "open_tickets": open_tickets,
                "in_progress": in_progress,
                "urgent_tickets": urgent_tickets,
                "ticket_cache_size": len(self._ticket_cache),
                "category_cache_size": len(self._category_cache),
            }
        except Exception as e:
            logger.error(f"Failed to get service health: {e}")
            return {"error": str(e)}
