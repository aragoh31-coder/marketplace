"""
Messaging Service
Handles all messaging-related business logic and operations.
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


class MessagingService(BaseService):
    """Service for managing messaging and communication operations."""

    service_name = "messaging_service"
    version = "1.0.0"
    description = "Messaging and communication service"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._conversation_cache = {}
        self._message_cache = {}

    def initialize(self) -> bool:
        """Initialize the messaging service."""
        try:
            # Set up any connections or validate configuration
            logger.info("Messaging service initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize messaging service: {e}")
            return False

    def cleanup(self) -> bool:
        """Clean up the messaging service."""
        try:
            # Clear caches
            self._conversation_cache.clear()
            self._message_cache.clear()
            logger.info("Messaging service cleaned up successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to cleanup messaging service: {e}")
            return False

    def get_required_config(self) -> List[str]:
        """Get required configuration keys."""
        return ["max_message_length", "conversation_timeout_days"]

    def get_conversation_by_id(self, conversation_id: str) -> Optional[Any]:
        """Get conversation by ID with caching."""
        cache_key = f"conversation:{conversation_id}"

        # Try cache first
        cached_conversation = self.get_cached(cache_key)
        if cached_conversation:
            return cached_conversation

        try:
            from messaging.models import Conversation

            conversation = Conversation.objects.get(id=conversation_id)

            # Cache conversation for 5 minutes
            self.set_cached(cache_key, conversation, timeout=300)
            return conversation

        except Exception as e:
            logger.error(f"Failed to get conversation {conversation_id}: {e}")
            return None

    def get_or_create_conversation(self, user1_id: str, user2_id: str, order_id: str = None) -> Tuple[Any, bool]:
        """Get existing conversation or create a new one."""
        try:
            from messaging.models import Conversation

            # Try to find existing conversation
            existing_conversation = Conversation.objects.filter(
                models.Q(user1_id=user1_id, user2_id=user2_id) | models.Q(user1_id=user2_id, user2_id=user1_id)
            ).first()

            if existing_conversation:
                return existing_conversation, False

            # Create new conversation
            conversation = Conversation.objects.create(user1_id=user1_id, user2_id=user2_id, order_id=order_id)

            # Clear caches
            self.clear_cache(f"user_conversations:{user1_id}")
            self.clear_cache(f"user_conversations:{user2_id}")

            logger.info(f"New conversation created: {conversation.id} between {user1_id} and {user2_id}")
            return conversation, True

        except Exception as e:
            logger.error(f"Failed to get or create conversation between {user1_id} and {user2_id}: {e}")
            return None, False

    def get_user_conversations(self, user_id: str, **filters) -> List[Any]:
        """Get conversations for a user with optional filters."""
        try:
            from messaging.models import Conversation

            queryset = Conversation.objects.filter(models.Q(user1_id=user_id) | models.Q(user2_id=user_id))

            # Apply filters
            if filters.get("active_only", False):
                queryset = queryset.filter(is_active=True)

            if filters.get("has_unread", False):
                queryset = queryset.filter(
                    models.Q(user1_id=user_id, user1_unread_count__gt=0)
                    | models.Q(user2_id=user_id, user2_unread_count__gt=0)
                )

            # Order by last message time
            conversations = queryset.order_by("-last_message_at")

            # Apply limit if specified
            if filters.get("limit"):
                conversations = conversations[: filters["limit"]]

            return list(conversations)

        except Exception as e:
            logger.error(f"Failed to get conversations for user {user_id}: {e}")
            return []

    def send_message(
        self, conversation_id: str, sender_id: str, content: str, message_type: str = "text", **kwargs
    ) -> Tuple[Any, bool, str]:
        """Send a message in a conversation."""
        try:
            from messaging.models import Conversation, Message

            conversation = self.get_conversation_by_id(conversation_id)
            if not conversation:
                return None, False, "Conversation not found"

            # Validate sender is part of conversation
            if str(sender_id) not in [str(conversation.user1_id), str(conversation.user2_id)]:
                return None, False, "You can only send messages to conversations you're part of"

            # Validate message content
            max_length = self.get_config("max_message_length", 1000)
            if len(content) > max_length:
                return None, False, f"Message too long. Maximum {max_length} characters allowed."

            with transaction.atomic():
                # Create message
                message = Message.objects.create(
                    conversation_id=conversation_id,
                    sender_id=sender_id,
                    content=content,
                    message_type=message_type,
                    **kwargs,
                )

                # Update conversation
                conversation.last_message_at = timezone.now()
                conversation.last_message_id = message.id

                # Update unread count for other user
                if str(sender_id) == str(conversation.user1_id):
                    conversation.user2_unread_count += 1
                else:
                    conversation.user1_unread_count += 1

                conversation.save()

                # Clear caches
                self.clear_cache(f"conversation:{conversation_id}")
                self.clear_cache(f"user_conversations:{conversation.user1_id}")
                self.clear_cache(f"user_conversations:{conversation.user2_id}")

                logger.info(f"Message sent successfully: {message.id} in conversation {conversation_id}")
                return message, True, "Message sent successfully"

        except Exception as e:
            logger.error(f"Failed to send message in conversation {conversation_id}: {e}")
            return None, False, str(e)

    def get_conversation_messages(self, conversation_id: str, **filters) -> List[Dict[str, Any]]:
        """Get messages for a conversation with optional filters."""
        try:
            from messaging.models import Message

            queryset = Message.objects.filter(conversation_id=conversation_id)

            # Apply filters
            if filters.get("message_type"):
                queryset = queryset.filter(message_type=filters["message_type"])

            if filters.get("date_from"):
                queryset = queryset.filter(created_at__gte=filters["date_from"])

            if filters.get("date_to"):
                queryset = queryset.filter(created_at__lte=filters["date_to"])

            # Order by creation time
            messages = queryset.order_by("created_at")

            # Apply limit if specified
            if filters.get("limit"):
                messages = messages[: filters["limit"]]

            return [
                {
                    "id": str(m.id),
                    "sender_id": str(m.sender_id),
                    "content": m.content,
                    "message_type": m.message_type,
                    "created_at": m.created_at.isoformat(),
                    "is_read": m.is_read,
                    "metadata": m.metadata if hasattr(m, "metadata") else {},
                }
                for m in messages
            ]

        except Exception as e:
            logger.error(f"Failed to get messages for conversation {conversation_id}: {e}")
            return []

    def mark_messages_as_read(self, conversation_id: str, user_id: str) -> Tuple[bool, str]:
        """Mark all messages in a conversation as read for a user."""
        try:
            from messaging.models import Conversation, Message

            conversation = self.get_conversation_by_id(conversation_id)
            if not conversation:
                return False, "Conversation not found"

            # Validate user is part of conversation
            if str(user_id) not in [str(conversation.user1_id), str(conversation.user2_id)]:
                return False, "You can only mark messages as read in conversations you're part of"

            with transaction.atomic():
                # Mark messages as read
                unread_messages = Message.objects.filter(
                    conversation_id=conversation_id, sender_id__ne=user_id, is_read=False
                )

                unread_count = unread_messages.count()
                unread_messages.update(is_read=True)

                # Update conversation unread count
                if str(user_id) == str(conversation.user1_id):
                    conversation.user1_unread_count = 0
                else:
                    conversation.user2_unread_count = 0

                conversation.save()

                # Clear caches
                self.clear_cache(f"conversation:{conversation_id}")
                self.clear_cache(f"user_conversations:{user_id}")

                logger.info(f"Marked {unread_count} messages as read in conversation {conversation_id}")
                return True, f"Marked {unread_count} messages as read"

        except Exception as e:
            logger.error(f"Failed to mark messages as read in conversation {conversation_id}: {e}")
            return False, str(e)

    def delete_message(self, message_id: str, user_id: str) -> Tuple[bool, str]:
        """Delete a message (only by sender)."""
        try:
            from messaging.models import Message

            message = Message.objects.get(id=message_id)

            # Check if user is the sender
            if str(message.sender_id) != str(user_id):
                return False, "You can only delete your own messages"

            # Check if message is too old to delete
            max_age_hours = self.get_config("message_deletion_max_age_hours", 24)
            if timezone.now() - message.created_at > timezone.timedelta(hours=max_age_hours):
                return False, f"Messages can only be deleted within {max_age_hours} hours"

            conversation_id = message.conversation_id

            with transaction.atomic():
                # Delete message
                message.delete()

                # Update conversation if this was the last message
                from messaging.models import Conversation

                conversation = Conversation.objects.get(id=conversation_id)

                if conversation.last_message_id == message_id:
                    # Find new last message
                    last_message = (
                        Message.objects.filter(conversation_id=conversation_id).order_by("-created_at").first()
                    )
                    if last_message:
                        conversation.last_message_at = last_message.created_at
                        conversation.last_message_id = last_message.id
                    else:
                        conversation.last_message_at = conversation.created_at
                        conversation.last_message_id = None

                    conversation.save()

                # Clear caches
                self.clear_cache(f"conversation:{conversation_id}")

                logger.info(f"Message {message_id} deleted successfully")
                return True, "Message deleted successfully"

        except Exception as e:
            logger.error(f"Failed to delete message {message_id}: {e}")
            return False, str(e)

    def get_unread_count(self, user_id: str) -> int:
        """Get total unread message count for a user."""
        try:
            from messaging.models import Conversation

            conversations = Conversation.objects.filter(models.Q(user1_id=user_id) | models.Q(user2_id=user_id))

            total_unread = 0
            for conversation in conversations:
                if str(user_id) == str(conversation.user1_id):
                    total_unread += conversation.user1_unread_count
                else:
                    total_unread += conversation.user2_unread_count

            return total_unread

        except Exception as e:
            logger.error(f"Failed to get unread count for user {user_id}: {e}")
            return 0

    def search_messages(self, user_id: str, query: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Search messages for a user."""
        try:
            from messaging.models import Conversation, Message

            # Get conversations user is part of
            user_conversations = Conversation.objects.filter(models.Q(user1_id=user_id) | models.Q(user2_id=user_id))

            conversation_ids = [str(c.id) for c in user_conversations]

            # Search messages in user's conversations
            messages = Message.objects.filter(conversation_id__in=conversation_ids, content__icontains=query).order_by(
                "-created_at"
            )[:limit]

            return [
                {
                    "id": str(m.id),
                    "conversation_id": str(m.conversation_id),
                    "sender_id": str(m.sender_id),
                    "content": m.content,
                    "message_type": m.message_type,
                    "created_at": m.created_at.isoformat(),
                    "is_read": m.is_read,
                }
                for m in messages
            ]

        except Exception as e:
            logger.error(f"Failed to search messages for user {user_id}: {e}")
            return []

    def get_conversation_summary(self, conversation_id: str) -> Dict[str, Any]:
        """Get comprehensive conversation summary."""
        try:
            conversation = self.get_conversation_by_id(conversation_id)
            if not conversation:
                return {}

            # Get recent messages
            messages = self.get_conversation_messages(conversation_id, limit=10)

            # Get participant info
            from core.services.user_service import UserService

            user_service = UserService()

            user1_info = user_service.get_user_statistics(str(conversation.user1_id))
            user2_info = user_service.get_user_statistics(str(conversation.user2_id))

            return {
                "id": str(conversation.id),
                "user1": user1_info,
                "user2": user2_info,
                "order_id": str(conversation.order_id) if conversation.order_id else None,
                "is_active": conversation.is_active,
                "created_at": conversation.created_at.isoformat(),
                "last_message_at": conversation.last_message_at.isoformat() if conversation.last_message_at else None,
                "user1_unread_count": conversation.user1_unread_count,
                "user2_unread_count": conversation.user2_unread_count,
                "recent_messages": messages,
                "total_messages": len(messages),
            }

        except Exception as e:
            logger.error(f"Failed to get conversation summary for {conversation_id}: {e}")
            return {}

    def archive_conversation(self, conversation_id: str, user_id: str) -> Tuple[bool, str]:
        """Archive a conversation for a user."""
        try:
            from messaging.models import Conversation

            conversation = self.get_conversation_by_id(conversation_id)
            if not conversation:
                return False, "Conversation not found"

            # Validate user is part of conversation
            if str(user_id) not in [str(conversation.user1_id), str(conversation.user2_id)]:
                return False, "You can only archive conversations you're part of"

            # Mark as archived for the user
            if str(user_id) == str(conversation.user1_id):
                conversation.user1_archived = True
            else:
                conversation.user2_archived = True

            conversation.save()

            # Clear caches
            self.clear_cache(f"conversation:{conversation_id}")
            self.clear_cache(f"user_conversations:{user_id}")

            logger.info(f"Conversation {conversation_id} archived for user {user_id}")
            return True, "Conversation archived successfully"

        except Exception as e:
            logger.error(f"Failed to archive conversation {conversation_id}: {e}")
            return False, str(e)

    def get_messaging_statistics(self, user_id: str = None) -> Dict[str, Any]:
        """Get messaging statistics."""
        try:
            from messaging.models import Conversation, Message

            queryset = Conversation.objects.all()
            message_queryset = Message.objects.all()

            if user_id:
                queryset = queryset.filter(models.Q(user1_id=user_id) | models.Q(user2_id=user_id))
                message_queryset = message_queryset.filter(conversation__in=queryset)

            total_conversations = queryset.count()
            active_conversations = queryset.filter(is_active=True).count()
            total_messages = message_queryset.count()

            # Message type distribution
            type_counts = {}
            for msg_type in message_queryset.values_list("message_type", flat=True).distinct():
                type_counts[msg_type] = message_queryset.filter(message_type=msg_type).count()

            # Monthly trends (last 12 months)
            monthly_trends = {}
            for i in range(12):
                month_start = timezone.now().replace(day=1) - timezone.timedelta(days=30 * i)
                month_end = month_start.replace(day=28) + timezone.timedelta(days=4)
                month_end = month_end.replace(day=1) - timezone.timedelta(days=1)

                month_messages = message_queryset.filter(created_at__gte=month_start, created_at__lte=month_end)

                monthly_trends[month_start.strftime("%Y-%m")] = {
                    "messages": month_messages.count(),
                    "conversations": queryset.filter(
                        models.Q(created_at__gte=month_start, created_at__lte=month_end)
                        | models.Q(last_message_at__gte=month_start, last_message_at__lte=month_end)
                    ).count(),
                }

            return {
                "total_conversations": total_conversations,
                "active_conversations": active_conversations,
                "total_messages": total_messages,
                "message_type_distribution": type_counts,
                "monthly_trends": monthly_trends,
            }

        except Exception as e:
            logger.error(f"Failed to get messaging statistics: {e}")
            return {}

    def get_service_health(self) -> Dict[str, Any]:
        """Get service health status."""
        try:
            from messaging.models import Conversation, Message

            total_conversations = Conversation.objects.count()
            active_conversations = Conversation.objects.filter(is_active=True).count()
            total_messages = Message.objects.count()
            unread_messages = Message.objects.filter(is_read=False).count()

            return {
                "total_conversations": total_conversations,
                "active_conversations": active_conversations,
                "total_messages": total_messages,
                "unread_messages": unread_messages,
                "conversation_cache_size": len(self._conversation_cache),
                "message_cache_size": len(self._message_cache),
            }
        except Exception as e:
            logger.error(f"Failed to get service health: {e}")
            return {"error": str(e)}
