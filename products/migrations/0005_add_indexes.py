from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0004_remove_vacation_field'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='product',
            index=models.Index(fields=['vendor', 'is_active'], name='prod_vendor_active_idx'),
        ),
        migrations.AddIndex(
            model_name='product',
            index=models.Index(fields=['category', 'is_active'], name='prod_cat_active_idx'),
        ),
        migrations.AddIndex(
            model_name='product',
            index=models.Index(fields=['stock_quantity'], name='products_stock_idx'),
        ),
        migrations.AddIndex(
            model_name='product',
            index=models.Index(fields=['price_btc'], name='products_price_btc_idx'),
        ),
        migrations.AddIndex(
            model_name='product',
            index=models.Index(fields=['price_xmr'], name='products_price_xmr_idx'),
        ),
        migrations.AddIndex(
            model_name='product',
            index=models.Index(fields=['-created_at'], name='products_created_desc_idx'),
        ),
    ]