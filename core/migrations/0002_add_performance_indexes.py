# Generated migration for performance optimization
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        # Add indexes for frequently queried fields
        migrations.AddIndex(
            model_name='product',
            index=models.Index(fields=['is_active', 'created_at'], name='core_product_active_idx'),
        ),
        migrations.AddIndex(
            model_name='product',
            index=models.Index(fields=['vendor', 'is_active'], name='core_product_vendor_idx'),
        ),
        migrations.AddIndex(
            model_name='product',
            index=models.Index(fields=['category', 'is_active'], name='core_product_category_idx'),
        ),
        migrations.AddIndex(
            model_name='order',
            index=models.Index(fields=['user', 'status', 'created_at'], name='core_order_user_status_idx'),
        ),
        migrations.AddIndex(
            model_name='order',
            index=models.Index(fields=['vendor', 'status'], name='core_order_vendor_idx'),
        ),
        migrations.AddIndex(
            model_name='transaction',
            index=models.Index(fields=['user', 'created_at'], name='core_transaction_user_idx'),
        ),
        migrations.AddIndex(
            model_name='transaction',
            index=models.Index(fields=['status', 'created_at'], name='core_transaction_status_idx'),
        ),
    ]