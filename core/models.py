from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator

User = get_user_model()


class BroadcastMessage(models.Model):
    title = models.CharField(max_length=255)
    content = models.TextField()
    active = models.BooleanField(default=True)
    priority = models.CharField(
        max_length=20,
        choices=[("low", "Low"), ("medium", "Medium"), ("high", "High"), ("critical", "Critical")],
        default="medium",
    )
    target_audience = models.CharField(
        max_length=20,
        choices=[("all", "All Users"), ("vendors", "Vendors Only"), ("buyers", "Buyers Only"), ("staff", "Staff Only")],
        default="all",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        ordering = ["-priority", "-created_at"]

    def __str__(self):
        return f"{self.title} ({self.priority})"

    def is_active(self):
        if not self.active:
            return False
        if self.expires_at and self.expires_at < timezone.now():
            return False
        return True


class SystemSettings(models.Model):
    key = models.CharField(max_length=255, unique=True)
    value = models.TextField()
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.key}: {self.value[:50]}"

    class Meta:
        verbose_name_plural = "System Settings"


class SecurityLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    action = models.CharField(max_length=255)
    details = models.JSONField(default=dict)
    timestamp = models.DateTimeField(auto_now_add=True)
    severity = models.CharField(
        max_length=20,
        choices=[("info", "Info"), ("warning", "Warning"), ("error", "Error"), ("critical", "Critical")],
        default="info",
    )

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.action} - {self.user or self.ip_address} - {self.timestamp}"


# New models for advanced features

class LoyaltyPoints(models.Model):
    """Model to track user loyalty points and history."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='loyalty_points')
    points = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    level = models.CharField(
        max_length=20,
        choices=[
            ("bronze", "Bronze"),
            ("silver", "Silver"),
            ("gold", "Gold"),
            ("platinum", "Platinum"),
            ("diamond", "Diamond")
        ],
        default="bronze"
    )
    total_earned = models.IntegerField(default=0)
    total_spent = models.IntegerField(default=0)
    last_activity = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Loyalty Points"
        unique_together = ['user']

    def __str__(self):
        return f"{self.user.username} - {self.level} ({self.points} points)"


class LoyaltyTransaction(models.Model):
    """Model to track individual loyalty point transactions."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='loyalty_transactions')
    points = models.IntegerField()
    transaction_type = models.CharField(
        max_length=20,
        choices=[
            ("earned", "Earned"),
            ("spent", "Spent"),
            ("bonus", "Bonus"),
            ("penalty", "Penalty")
        ]
    )
    reason = models.CharField(max_length=255)
    order = models.ForeignKey('orders.Order', on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.transaction_type} {self.points} points"


class VendorAnalytics(models.Model):
    """Model to store vendor analytics data for caching and historical tracking."""
    vendor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='analytics')
    data_type = models.CharField(
        max_length=50,
        choices=[
            ("sales_performance", "Sales Performance"),
            ("product_performance", "Product Performance"),
            ("customer_insights", "Customer Insights"),
            ("quality_metrics", "Quality Metrics"),
            ("revenue_breakdown", "Revenue Breakdown"),
            ("geographic_insights", "Geographic Insights"),
            ("trend_analysis", "Trend Analysis"),
            ("recommendations", "Recommendations")
        ]
    )
    data = models.JSONField()
    period_start = models.DateTimeField()
    period_end = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        verbose_name_plural = "Vendor Analytics"
        unique_together = ['vendor', 'data_type', 'period_start', 'period_end']
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.vendor.username} - {self.data_type} ({self.period_start.date()})"

    def is_expired(self):
        return timezone.now() > self.expires_at


class ProductRecommendation(models.Model):
    """Model to store product recommendations for users."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='product_recommendations')
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE, related_name='recommendations')
    recommendation_type = models.CharField(
        max_length=30,
        choices=[
            ("collaborative", "Collaborative Filtering"),
            ("content_based", "Content Based"),
            ("trending", "Trending"),
            ("similar", "Similar Products")
        ]
    )
    confidence_score = models.FloatField(validators=[MinValueValidator(0.0), MaxValueValidator(1.0)])
    explanation = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        ordering = ['-confidence_score', '-created_at']
        unique_together = ['user', 'product', 'recommendation_type']

    def __str__(self):
        return f"{self.user.username} - {self.product.name} ({self.recommendation_type})"

    def is_expired(self):
        return timezone.now() > self.expires_at


class PricePrediction(models.Model):
    """Model to store price predictions and market insights."""
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE, related_name='price_predictions')
    predicted_price = models.DecimalField(max_digits=10, decimal_places=2)
    confidence_score = models.FloatField(validators=[MinValueValidator(0.0), MaxValueValidator(1.0)])
    prediction_type = models.CharField(
        max_length=30,
        choices=[
            ("conservative", "Conservative"),
            ("optimal", "Optimal"),
            ("aggressive", "Aggressive"),
            ("forecast", "Forecast")
        ]
    )
    market_conditions = models.JSONField()
    factors = models.JSONField()
    predicted_at = models.DateTimeField(auto_now_add=True)
    valid_until = models.DateTimeField()

    class Meta:
        ordering = ['-predicted_at']
        unique_together = ['product', 'prediction_type', 'predicted_at']

    def __str__(self):
        return f"{self.product.name} - {self.prediction_type} ({self.predicted_price})"

    def is_valid(self):
        return timezone.now() < self.valid_until


class UserPreferenceProfile(models.Model):
    """Model to store comprehensive user preference profiles."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='preference_profile')
    purchase_patterns = models.JSONField(default=dict)
    price_sensitivity = models.CharField(
        max_length=20,
        choices=[
            ("very_low", "Very Low"),
            ("low", "Low"),
            ("medium", "Medium"),
            ("high", "High"),
            ("very_high", "Very High")
        ],
        default="medium"
    )
    category_affinity = models.JSONField(default=dict)
    vendor_preferences = models.JSONField(default=dict)
    temporal_patterns = models.JSONField(default=dict)
    risk_profile = models.CharField(
        max_length=20,
        choices=[
            ("conservative", "Conservative"),
            ("moderate", "Moderate"),
            ("aggressive", "Aggressive")
        ],
        default="moderate"
    )
    loyalty_indicators = models.JSONField(default=dict)
    churn_risk = models.FloatField(validators=[MinValueValidator(0.0), MaxValueValidator(1.0)], default=0.5)
    last_updated = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "User Preference Profiles"

    def __str__(self):
        return f"{self.user.username} - Preference Profile"


class SearchQuery(models.Model):
    """Model to track search queries for personalization and analytics."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='search_queries', null=True, blank=True)
    query = models.CharField(max_length=500)
    filters = models.JSONField(default=dict)
    results_count = models.IntegerField()
    clicked_results = models.JSONField(default=list)
    session_id = models.CharField(max_length=100, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = "Search Queries"

    def __str__(self):
        return f"{self.query} ({self.results_count} results)"


class DisputeArbitration(models.Model):
    """Model to track automated dispute arbitration decisions."""
    dispute = models.ForeignKey('disputes.Dispute', on_delete=models.CASCADE, related_name='arbitrations')
    arbitrator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='arbitrations', null=True, blank=True)
    decision = models.CharField(
        max_length=20,
        choices=[
            ("buyer_wins", "Buyer Wins"),
            ("vendor_wins", "Vendor Wins"),
            ("split", "Split Decision"),
            ("inconclusive", "Inconclusive")
        ]
    )
    evidence_score = models.FloatField(validators=[MinValueValidator(0.0), MaxValueValidator(1.0)])
    order_pattern_score = models.FloatField(validators=[MinValueValidator(0.0), MaxValueValidator(1.0)])
    confidence_score = models.FloatField(validators=[MinValueValidator(0.0), MaxValueValidator(1.0)])
    reasoning = models.TextField()
    automated = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = "Dispute Arbitrations"

    def __str__(self):
        return f"Dispute {self.dispute.id} - {self.decision} ({self.confidence_score:.2f})"
