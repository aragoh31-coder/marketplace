from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('vendors', '0006_vendor_average_rating_vendor_completed_orders_and_more'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='vendor',
            index=models.Index(fields=['is_active', 'is_approved'], name='vendors_active_approved_idx'),
        ),
        migrations.AddIndex(
            model_name='vendor',
            index=models.Index(fields=['-trust_score'], name='vendors_trust_score_idx'),
        ),
        migrations.AddIndex(
            model_name='vendor',
            index=models.Index(fields=['user'], name='vendors_user_idx'),
        ),
        migrations.AddIndex(
            model_name='vendorrating',
            index=models.Index(fields=['vendor', 'user'], name='vendor_rating_idx'),
        ),
        migrations.AddIndex(
            model_name='vendorrating',
            index=models.Index(fields=['vendor', '-created_at'], name='vendor_rating_recent_idx'),
        ),
    ]