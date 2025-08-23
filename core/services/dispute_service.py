"""
Dispute Service
Handles all dispute-related business logic and operations.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import models, transaction
from django.utils import timezone

from .base_service import BaseService

logger = logging.getLogger(__name__)
User = get_user_model()


class DisputeService(BaseService):
    """Service for managing disputes and dispute operations."""

    service_name = "dispute_service"
    version = "1.0.0"
    description = "Dispute management and operations service"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._dispute_cache = {}
        self._evidence_cache = {}

    def initialize(self) -> bool:
        """Initialize the dispute service."""
        try:
            # Set up any connections or validate configuration
            logger.info("Dispute service initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize dispute service: {e}")
            return False

    def cleanup(self) -> bool:
        """Clean up the dispute service."""
        try:
            # Clear caches
            self._dispute_cache.clear()
            self._evidence_cache.clear()
            logger.info("Dispute service cleaned up successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to cleanup dispute service: {e}")
            return False

    def get_required_config(self) -> List[str]:
        """Get required configuration keys."""
        return ["dispute_timeout_days", "max_evidence_files"]

    def get_dispute_by_id(self, dispute_id: str) -> Optional[Any]:
        """Get dispute by ID with caching."""
        cache_key = f"dispute:{dispute_id}"

        # Try cache first
        cached_dispute = self.get_cached(cache_key)
        if cached_dispute:
            return cached_dispute

        try:
            from disputes.models import Dispute

            dispute = Dispute.objects.get(id=dispute_id)

            # Cache dispute for 5 minutes
            self.set_cached(cache_key, dispute, timeout=300)
            return dispute

        except Exception as e:
            logger.error(f"Failed to get dispute {dispute_id}: {e}")
            return None

    def get_disputes_by_user(self, user_id: str, **filters) -> List[Any]:
        """Get disputes by user with optional filters."""
        try:
            from disputes.models import Dispute

            queryset = Dispute.objects.filter(models.Q(user_id=user_id) | models.Q(vendor_id=user_id))

            # Apply filters
            if filters.get("status"):
                queryset = queryset.filter(status=filters["status"])

            if filters.get("active_only", False):
                queryset = queryset.exclude(status__in=["resolved", "closed"])

            if filters.get("type"):
                queryset = queryset.filter(dispute_type=filters["type"])

            # Order by creation date
            disputes = queryset.order_by("-created_at")

            # Apply limit if specified
            if filters.get("limit"):
                disputes = disputes[: filters["limit"]]

            return list(disputes)

        except Exception as e:
            logger.error(f"Failed to get disputes for user {user_id}: {e}")
            return []

    def create_dispute(
        self, user_id: str, order_id: str, dispute_type: str, description: str, **kwargs
    ) -> Tuple[Any, bool, str]:
        """Create a new dispute."""
        try:
            from core.services.order_service import OrderService
            from disputes.models import Dispute

            with transaction.atomic():
                # Validate order exists and belongs to user
                order_service = OrderService()
                order = order_service.get_order_by_id(order_id)

                if not order:
                    return None, False, "Order not found"

                if str(order.user_id) != user_id:
                    return None, False, "You can only create disputes for your own orders"

                # Check if order is in a disputable state
                if order.status not in ["shipped", "processing"]:
                    return None, False, f"Order cannot be disputed in status: {order.status}"

                # Check if dispute already exists for this order
                existing_dispute = Dispute.objects.filter(order_id=order_id).first()
                if existing_dispute:
                    return None, False, "A dispute already exists for this order"

                # Create dispute
                dispute = Dispute.objects.create(
                    user_id=user_id,
                    order_id=order_id,
                    vendor_id=order.vendor_id,
                    dispute_type=dispute_type,
                    description=description,
                    status="open",
                    **kwargs,
                )

                # Update order status to disputed
                order_service.update_order_status(order_id, "disputed", user_id, f"Dispute created: {dispute_type}")

                # Clear caches
                self.clear_cache(f"user_disputes:{user_id}")
                self.clear_cache(f"vendor_disputes:{order.vendor_id}")

                logger.info(f"Dispute created successfully: {dispute.id} for order {order_id}")
                return dispute, True, "Dispute created successfully"

        except Exception as e:
            logger.error(f"Failed to create dispute for order {order_id}: {e}")
            return None, False, str(e)

    def update_dispute_status(
        self, dispute_id: str, new_status: str, admin_user_id: str = None, resolution: str = "", winner_id: str = None
    ) -> Tuple[bool, str]:
        """Update dispute status."""
        try:
            dispute = self.get_dispute_by_id(dispute_id)
            if not dispute:
                return False, "Dispute not found"

            # Validate status transition
            valid_transitions = self._get_valid_status_transitions(dispute.status)
            if new_status not in valid_transitions:
                return False, f"Invalid status transition from {dispute.status} to {new_status}"

            with transaction.atomic():
                old_status = dispute.status
                dispute.status = new_status

                # Update status-specific fields
                if new_status == "under_review":
                    dispute.review_started = timezone.now()
                elif new_status == "resolved":
                    dispute.resolved_at = timezone.now()
                    dispute.resolution = resolution
                    dispute.winner_id = winner_id
                    # Handle dispute resolution
                    self._resolve_dispute(dispute)
                elif new_status == "closed":
                    dispute.closed_at = timezone.now()

                dispute.save()

                # Log status change
                self._log_dispute_status_change(dispute_id, old_status, new_status, admin_user_id, resolution)

                # Clear caches
                self.clear_cache(f"dispute:{dispute_id}")
                self.clear_cache(f"user_disputes:{dispute.user_id}")
                self.clear_cache(f"vendor_disputes:{dispute.vendor_id}")

                logger.info(f"Dispute {dispute_id} status updated: {old_status} -> {new_status}")
                return True, f"Dispute status updated to {new_status}"

        except Exception as e:
            logger.error(f"Failed to update dispute status for {dispute_id}: {e}")
            return False, str(e)

    def _get_valid_status_transitions(self, current_status: str) -> List[str]:
        """Get valid status transitions from current status."""
        transitions = {
            "open": ["under_review", "closed"],
            "under_review": ["resolved", "closed"],
            "resolved": ["closed"],
            "closed": [],  # Final state
        }
        return transitions.get(current_status, [])

    def _resolve_dispute(self, dispute: Any) -> None:
        """Handle dispute resolution."""
        try:
            from core.services.order_service import OrderService
            from core.services.wallet_service import WalletService

            order_service = OrderService()
            wallet_service = WalletService()

            if dispute.winner_id == str(dispute.user_id):
                # User wins - refund order
                order_service.update_order_status(
                    str(dispute.order_id), "cancelled", dispute.user_id, "Dispute resolved in favor of user"
                )
            elif dispute.winner_id == str(dispute.vendor_id):
                # Vendor wins - complete order
                order_service.update_order_status(
                    str(dispute.order_id), "completed", dispute.vendor_id, "Dispute resolved in favor of vendor"
                )
            else:
                # Split decision - partial refund
                self._handle_partial_refund(dispute)

        except Exception as e:
            logger.error(f"Failed to resolve dispute {dispute.id}: {e}")

    def _handle_partial_refund(self, dispute: Any) -> None:
        """Handle partial refund for split dispute resolution."""
        try:
            from core.services.order_service import OrderService
            from core.services.wallet_service import WalletService

            order_service = OrderService()
            wallet_service = WalletService()

            order = order_service.get_order_by_id(str(dispute.order_id))
            if not order:
                return

            # Calculate partial refund (e.g., 50% back to user)
            refund_amount = order.total_amount / 2

            # Release partial amount from escrow to user
            wallet_service.release_from_escrow(
                str(order.user_id), order.currency.lower(), refund_amount, f"dispute_partial_refund_{dispute.id}"
            )

            # Release remaining amount to vendor
            remaining_amount = order.total_amount - refund_amount
            wallet_service.release_from_escrow(
                str(order.user_id), order.currency.lower(), remaining_amount, f"dispute_vendor_payment_{dispute.id}"
            )

            wallet_service.add_funds(
                str(order.vendor_id), order.currency.lower(), remaining_amount, f"dispute_resolution_{dispute.id}"
            )

            # Update order status
            order_service.update_order_status(
                str(order.id), "completed", dispute.user_id, "Dispute resolved with partial refund"
            )

            logger.info(f"Partial refund processed for dispute {dispute.id}")

        except Exception as e:
            logger.error(f"Failed to handle partial refund for dispute {dispute.id}: {e}")

    def add_evidence(
        self, dispute_id: str, user_id: str, evidence_type: str, description: str, file_path: str = None
    ) -> Tuple[Any, bool, str]:
        """Add evidence to a dispute."""
        try:
            from disputes.models import DisputeEvidence

            dispute = self.get_dispute_by_id(dispute_id)
            if not dispute:
                return None, False, "Dispute not found"

            # Check if user is involved in the dispute
            if str(user_id) not in [str(dispute.user_id), str(dispute.vendor_id)]:
                return None, False, "You can only add evidence to disputes you're involved in"

            # Check evidence limit
            existing_evidence = DisputeEvidence.objects.filter(dispute_id=dispute_id).count()
            max_evidence = self.get_config("max_evidence_files", 10)

            if existing_evidence >= max_evidence:
                return None, False, f"Evidence limit reached. Maximum {max_evidence} files allowed."

            # Create evidence
            evidence = DisputeEvidence.objects.create(
                dispute_id=dispute_id,
                user_id=user_id,
                evidence_type=evidence_type,
                description=description,
                file_path=file_path,
            )

            # Clear caches
            self.clear_cache(f"dispute_evidence:{dispute_id}")

            logger.info(f"Evidence added to dispute {dispute_id}: {evidence_type}")
            return evidence, True, "Evidence added successfully"

        except Exception as e:
            logger.error(f"Failed to add evidence to dispute {dispute_id}: {e}")
            return None, False, str(e)

    def get_dispute_evidence(self, dispute_id: str) -> List[Dict[str, Any]]:
        """Get evidence for a dispute."""
        try:
            from disputes.models import DisputeEvidence

            evidence = DisputeEvidence.objects.filter(dispute_id=dispute_id).order_by("created_at")

            return [
                {
                    "id": str(e.id),
                    "user_id": str(e.user_id),
                    "evidence_type": e.evidence_type,
                    "description": e.description,
                    "file_path": e.file_path,
                    "created_at": e.created_at.isoformat(),
                }
                for e in evidence
            ]

        except Exception as e:
            logger.error(f"Failed to get evidence for dispute {dispute_id}: {e}")
            return []

    def get_dispute_summary(self, dispute_id: str) -> Dict[str, Any]:
        """Get comprehensive dispute summary."""
        try:
            dispute = self.get_dispute_by_id(dispute_id)
            if not dispute:
                return {}

            # Get evidence
            evidence = self.get_dispute_evidence(dispute_id)

            return {
                "id": str(dispute.id),
                "user_id": str(dispute.user_id),
                "vendor_id": str(dispute.vendor_id),
                "order_id": str(dispute.order_id),
                "dispute_type": dispute.dispute_type,
                "description": dispute.description,
                "status": dispute.status,
                "evidence": evidence,
                "created_at": dispute.created_at.isoformat(),
                "updated_at": dispute.updated_at.isoformat() if hasattr(dispute, "updated_at") else None,
                "review_started": (
                    dispute.review_started.isoformat()
                    if hasattr(dispute, "review_started") and dispute.review_started
                    else None
                ),
                "resolved_at": (
                    dispute.resolved_at.isoformat() if hasattr(dispute, "resolved_at") and dispute.resolved_at else None
                ),
                "closed_at": (
                    dispute.closed_at.isoformat() if hasattr(dispute, "closed_at") and dispute.closed_at else None
                ),
                "resolution": dispute.resolution if hasattr(dispute, "resolution") else None,
                "winner_id": dispute.winner_id if hasattr(dispute, "winner_id") else None,
            }

        except Exception as e:
            logger.error(f"Failed to get dispute summary for {dispute_id}: {e}")
            return {}

    def get_dispute_statistics(self, user_id: str = None) -> Dict[str, Any]:
        """Get dispute statistics."""
        try:
            from disputes.models import Dispute

            queryset = Dispute.objects.all()

            if user_id:
                queryset = queryset.filter(models.Q(user_id=user_id) | models.Q(vendor_id=user_id))

            total_disputes = queryset.count()
            open_disputes = queryset.filter(status="open").count()
            under_review = queryset.filter(status="under_review").count()
            resolved_disputes = queryset.filter(status="resolved").count()
            closed_disputes = queryset.filter(status="closed").count()

            # Type distribution
            type_counts = {}
            for dispute_type in queryset.values_list("dispute_type", flat=True).distinct():
                type_counts[dispute_type] = queryset.filter(dispute_type=dispute_type).count()

            # Monthly trends (last 12 months)
            monthly_trends = {}
            for i in range(12):
                month_start = timezone.now().replace(day=1) - timezone.timedelta(days=30 * i)
                month_end = month_start.replace(day=28) + timezone.timedelta(days=4)
                month_end = month_end.replace(day=1) - timezone.timedelta(days=1)

                month_disputes = queryset.filter(created_at__gte=month_start, created_at__lte=month_end)

                monthly_trends[month_start.strftime("%Y-%m")] = {
                    "disputes": month_disputes.count(),
                    "resolved": month_disputes.filter(status="resolved").count(),
                }

            return {
                "total_disputes": total_disputes,
                "status_distribution": {
                    "open": open_disputes,
                    "under_review": under_review,
                    "resolved": resolved_disputes,
                    "closed": closed_disputes,
                },
                "type_distribution": type_counts,
                "monthly_trends": monthly_trends,
            }

        except Exception as e:
            logger.error(f"Failed to get dispute statistics: {e}")
            return {}

    def escalate_dispute(self, dispute_id: str, user_id: str, reason: str) -> Tuple[bool, str]:
        """Escalate a dispute to admin review."""
        try:
            dispute = self.get_dispute_by_id(dispute_id)
            if not dispute:
                return False, "Dispute not found"

            # Check if user is involved in the dispute
            if str(user_id) not in [str(dispute.user_id), str(dispute.vendor_id)]:
                return False, "You can only escalate disputes you're involved in"

            # Check if dispute can be escalated
            if dispute.status not in ["open", "under_review"]:
                return False, f"Dispute cannot be escalated in status: {dispute.status}"

            # Update status to under_review
            return self.update_dispute_status(dispute_id, "under_review", user_id, f"Escalated: {reason}")

        except Exception as e:
            logger.error(f"Failed to escalate dispute {dispute_id}: {e}")
            return False, str(e)

    def _log_dispute_status_change(
        self, dispute_id: str, old_status: str, new_status: str, admin_user_id: str = None, resolution: str = ""
    ) -> None:
        """Log dispute status change for audit purposes."""
        try:
            from disputes.models import DisputeStatusLog

            DisputeStatusLog.objects.create(
                dispute_id=dispute_id,
                old_status=old_status,
                new_status=new_status,
                changed_by_id=admin_user_id,
                resolution=resolution,
                timestamp=timezone.now(),
            )

        except Exception as e:
            logger.error(f"Failed to log dispute status change: {e}")

    def get_service_health(self) -> Dict[str, Any]:
        """Get service health status."""
        try:
            from disputes.models import Dispute

            total_disputes = Dispute.objects.count()
            open_disputes = Dispute.objects.filter(status="open").count()
            under_review = Dispute.objects.filter(status="under_review").count()

            return {
                "total_disputes": total_disputes,
                "open_disputes": open_disputes,
                "under_review": under_review,
                "dispute_cache_size": len(self._dispute_cache),
                "evidence_cache_size": len(self._evidence_cache),
            }
        except Exception as e:
            logger.error(f"Failed to get service health: {e}")
            return {"error": str(e)}

    def auto_resolve_dispute(self, dispute_id: str) -> Dict[str, Any]:
        """Automated dispute resolution based on evidence weight and patterns"""
        try:
            dispute = self.get_dispute_by_id(dispute_id)
            if not dispute:
                return {"success": False, "error": "Dispute not found"}
            
            if dispute.status != "INVESTIGATING":
                return {"success": False, "error": "Dispute not in investigating status"}
            
            # Get all evidence
            evidence_list = dispute.evidence.all()
            if len(evidence_list) < 2:
                return {"success": False, "error": "Insufficient evidence for automated resolution"}
            
            # Score evidence for both parties
            buyer_score = 0
            vendor_score = 0
            
            for evidence in evidence_list:
                score = self._score_evidence(evidence)
                if evidence.submitted_by == dispute.complainant:
                    buyer_score += score
                elif evidence.submitted_by == dispute.respondent:
                    vendor_score += score
            
            # Analyze order patterns
            order_analysis = self._analyze_order_patterns(dispute.order)
            buyer_score += order_analysis.get("buyer_bonus", 0)
            vendor_score += order_analysis.get("vendor_bonus", 0)
            
            # Determine winner based on evidence strength
            confidence_threshold = 1.5  # Winner must have 50% more evidence
            winner = None
            resolution = ""
            
            if buyer_score > vendor_score * confidence_threshold:
                winner = dispute.complainant
                resolution = f"Automated resolution: Buyer evidence significantly stronger (Score: {buyer_score} vs {vendor_score}). Refund granted."
                # Release funds from escrow back to buyer
                self._handle_buyer_victory(dispute)
                
            elif vendor_score > buyer_score * confidence_threshold:
                winner = dispute.respondent  
                resolution = f"Automated resolution: Vendor evidence significantly stronger (Score: {vendor_score} vs {buyer_score}). Funds released to vendor."
                # Release funds from escrow to vendor
                self._handle_vendor_victory(dispute)
                
            else:
                resolution = f"Automated resolution: Evidence inconclusive (Buyer: {buyer_score}, Vendor: {vendor_score}). Manual review required."
                # Flag for manual review
                dispute.status = "MANUAL_REVIEW"
                dispute.save()
                
                return {
                    "success": True,
                    "auto_resolved": False,
                    "manual_review": True,
                    "buyer_score": buyer_score,
                    "vendor_score": vendor_score,
                    "resolution": resolution
                }
            
            # Update dispute with resolution
            if winner:
                dispute.status = "RESOLVED"
                dispute.winner_id = winner.id
                dispute.resolution = resolution
                dispute.resolved_at = timezone.now()
                dispute.save()
                
                # Update order status
                dispute.order.status = "disputed_resolved"
                dispute.order.save()
            
            logger.info(f"Dispute {dispute_id} auto-resolved: Winner={winner.id if winner else 'None'}")
            
            return {
                "success": True,
                "auto_resolved": winner is not None,
                "winner_id": winner.id if winner else None,
                "buyer_score": buyer_score,
                "vendor_score": vendor_score,
                "resolution": resolution
            }
            
        except Exception as e:
            logger.error(f"Failed to auto-resolve dispute {dispute_id}: {e}")
            return {"success": False, "error": str(e)}
    
    def _score_evidence(self, evidence) -> float:
        """Score individual evidence based on type, quality, and timing"""
        score = 0.0
        
        # Base score for evidence submission
        score += 10.0
        
        # Bonus for detailed descriptions
        if len(evidence.description) > 100:
            score += 5.0
        if len(evidence.description) > 300:
            score += 10.0
        
        # Bonus for file attachments
        if evidence.file_attachment:
            score += 15.0
        
        # Bonus for early submission (within first 24 hours)
        if evidence.created_at <= evidence.dispute.created_at + timedelta(hours=24):
            score += 8.0
        
        # Penalty for very late submission (after 7 days)
        if evidence.created_at > evidence.dispute.created_at + timedelta(days=7):
            score -= 5.0
        
        # Bonus for structured evidence (contains keywords)
        description_lower = evidence.description.lower()
        structured_keywords = [
            'tracking', 'receipt', 'screenshot', 'conversation', 'transaction',
            'proof', 'evidence', 'documentation', 'record', 'timestamp'
        ]
        
        for keyword in structured_keywords:
            if keyword in description_lower:
                score += 3.0
        
        return max(score, 0.0)  # Ensure non-negative score
    
    def _analyze_order_patterns(self, order) -> Dict[str, float]:
        """Analyze order and user patterns for additional context"""
        analysis = {"buyer_bonus": 0.0, "vendor_bonus": 0.0}
        
        try:
            # Buyer history analysis
            buyer = order.buyer
            buyer_orders = Order.objects.filter(buyer=buyer, status="completed").count()
            buyer_disputes = Dispute.objects.filter(complainant=buyer).count()
            
            # Bonus for established buyers with good history
            if buyer_orders >= 5 and buyer_disputes <= 1:
                analysis["buyer_bonus"] += 10.0
            elif buyer_orders >= 10 and buyer_disputes == 0:
                analysis["buyer_bonus"] += 20.0
            
            # Penalty for dispute-heavy buyers
            if buyer_orders > 0 and (buyer_disputes / buyer_orders) > 0.3:
                analysis["buyer_bonus"] -= 15.0
            
            # Vendor history analysis
            vendor = order.items.first().product.vendor if order.items.exists() else None
            if vendor:
                vendor_orders = Order.objects.filter(
                    items__product__vendor=vendor, 
                    status="completed"
                ).distinct().count()
                vendor_disputes = Dispute.objects.filter(respondent=vendor.user).count()
                
                # Bonus for established vendors with good history
                if vendor_orders >= 10 and vendor_disputes <= 2:
                    analysis["vendor_bonus"] += 15.0
                elif vendor_orders >= 50 and vendor_disputes <= 5:
                    analysis["vendor_bonus"] += 25.0
                
                # Penalty for dispute-heavy vendors
                if vendor_orders > 0 and (vendor_disputes / vendor_orders) > 0.2:
                    analysis["vendor_bonus"] -= 20.0
            
            # Order value considerations
            order_value = float(order.total_amount or 0)
            if order_value > 1000:  # High-value orders get more scrutiny
                analysis["buyer_bonus"] += 5.0
                analysis["vendor_bonus"] += 5.0
            
        except Exception as e:
            logger.error(f"Error analyzing order patterns: {e}")
        
        return analysis
    
    def _handle_buyer_victory(self, dispute):
        """Handle escrow release when buyer wins dispute"""
        try:
            from core.services.wallet_service import WalletService
            wallet_service = WalletService()
            
            order = dispute.order
            # Release funds from escrow back to buyer
            for item in order.items.all():
                amount = item.quantity * item.price
                currency = "btc"  # Default, should be determined by order
                
                success, msg = wallet_service.release_from_escrow(
                    str(order.buyer.id), currency, amount, str(order.id)
                )
                
                if not success:
                    logger.error(f"Failed to release escrow to buyer: {msg}")
                    
        except Exception as e:
            logger.error(f"Error handling buyer victory: {e}")
    
    def _handle_vendor_victory(self, dispute):
        """Handle escrow release when vendor wins dispute"""
        try:
            from core.services.wallet_service import WalletService
            wallet_service = WalletService()
            
            order = dispute.order
            # Release funds from escrow to vendor
            vendor = order.items.first().product.vendor.user if order.items.exists() else None
            
            if vendor:
                for item in order.items.all():
                    amount = item.quantity * item.price
                    currency = "btc"  # Default, should be determined by order
                    
                    # Release from buyer's escrow
                    wallet_service.release_from_escrow(
                        str(order.buyer.id), currency, amount, str(order.id)
                    )
                    
                    # Add to vendor's balance
                    wallet_service.add_balance(str(vendor.id), currency, amount)
                    
        except Exception as e:
            logger.error(f"Error handling vendor victory: {e}")
