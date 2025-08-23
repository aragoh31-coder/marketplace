import os

from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "marketplace.settings")

app = Celery("marketplace")

app.config_from_object("django.conf:settings", namespace="CELERY")

# Discover tasks from all apps
app.autodiscover_tasks([
    "core", "vendors", "accounts", "orders", "products", 
    "disputes", "wallets", "messaging", "support"
])

# Configure Celery Beat schedule
app.conf.beat_schedule = {
    # Daily maintenance tasks - run at 2 AM
    'daily-maintenance': {
        'task': 'core.tasks.daily_maintenance',
        'schedule': crontab(hour=2, minute=0),
    },
    
    # Refresh analytics every 6 hours
    'refresh-analytics': {
        'task': 'core.tasks.refresh_all_analytics',
        'schedule': crontab(minute=0, hour='*/6'),
    },
    
    # Update price predictions daily at 6 AM
    'update-price-predictions': {
        'task': 'core.tasks.update_price_predictions',
        'schedule': crontab(hour=6, minute=0),
    },
    
    # Refresh user recommendations daily at 8 AM
    'refresh-recommendations': {
        'task': 'core.tasks.refresh_user_recommendations',
        'schedule': crontab(hour=8, minute=0),
    },
    
    # Build user preference profiles daily at 10 AM
    'build-user-profiles': {
        'task': 'core.tasks.build_user_preference_profiles',
        'schedule': crontab(hour=10, minute=0),
    },
    
    # Process pending disputes every 4 hours
    'process-disputes': {
        'task': 'core.tasks.process_pending_disputes',
        'schedule': crontab(minute=0, hour='*/4'),
    },
    
    # Clean up expired data daily at 3 AM
    'cleanup-expired-data': {
        'task': 'core.tasks.cleanup_expired_data',
        'schedule': crontab(hour=3, minute=0),
    },
    
    # Weekly analytics report - every Sunday at 9 AM
    'weekly-analytics-report': {
        'task': 'core.tasks.weekly_analytics_report',
        'schedule': crontab(day_of_week=0, hour=9, minute=0),
    },
    
    # Export analytics data weekly - every Monday at 1 AM
    'export-analytics-data': {
        'task': 'core.tasks.export_analytics_data',
        'schedule': crontab(day_of_week=1, hour=1, minute=0),
    },
}

# Task routing configuration
app.conf.task_routes = {
    'core.tasks.*': {'queue': 'core'},
    '*.tasks.*': {'queue': 'default'},
}

# Task result backend configuration
app.conf.result_backend = 'django-db'

# Task serialization
app.conf.task_serializer = 'json'
app.conf.accept_content = ['json']
app.conf.result_serializer = 'json'
app.conf.timezone = 'UTC'

# Task execution settings
app.conf.task_always_eager = False  # Set to True for testing
app.conf.task_eager_propagates = True

# Worker settings
app.conf.worker_prefetch_multiplier = 1
app.conf.worker_max_tasks_per_child = 1000

# Task time limits
app.conf.task_soft_time_limit = 300  # 5 minutes
app.conf.task_time_limit = 600       # 10 minutes

# Rate limiting
app.conf.task_annotations = {
    'core.tasks.refresh_all_analytics': {'rate_limit': '10/m'},
    'core.tasks.update_price_predictions': {'rate_limit': '5/m'},
    'core.tasks.refresh_user_recommendations': {'rate_limit': '20/m'},
    'core.tasks.build_user_preference_profiles': {'rate_limit': '10/m'},
    'core.tasks.process_pending_disputes': {'rate_limit': '15/m'},
}

@app.task(bind=True)
def debug_task(self):
    print(f"Request: {self.request!r}")


# Health check task
@app.task(bind=True)
def health_check(self):
    """Simple health check task for monitoring."""
    return {
        'status': 'healthy',
        'timestamp': self.request.id,
        'worker': self.request.hostname
    }


# Task monitoring
@app.task(bind=True)
def monitor_task_health(self):
    """Monitor the health of all scheduled tasks."""
    from django.utils import timezone
    from django.db import connection
    
    try:
        # Check database connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        
        # Check if core models exist
        from core.models import LoyaltyPoints, VendorAnalytics
        loyalty_count = LoyaltyPoints.objects.count()
        analytics_count = VendorAnalytics.objects.count()
        
        return {
            'status': 'healthy',
            'database': 'connected',
            'loyalty_records': loyalty_count,
            'analytics_records': analytics_count,
            'timestamp': timezone.now().isoformat()
        }
    except Exception as e:
        return {
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': timezone.now().isoformat()
        }


# Add monitoring task to beat schedule
app.conf.beat_schedule['monitor-task-health'] = {
    'task': 'marketplace.celery.monitor_task_health',
    'schedule': crontab(minute='*/15'),  # Every 15 minutes
}
