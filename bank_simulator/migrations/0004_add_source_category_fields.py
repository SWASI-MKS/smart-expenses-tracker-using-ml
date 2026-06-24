from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('bank_simulator', '0003_auto_20260226_1422'),
    ]

    operations = [
        # Add source field for credit transactions
        migrations.AddField(
            model_name='banktransaction',
            name='source',
            field=models.CharField(blank=True, default='', max_length=100),
        ),
        # Add category field for debit transactions
        migrations.AddField(
            model_name='banktransaction',
            name='category',
            field=models.CharField(blank=True, default='', max_length=100),
        ),
        # Add linked income ID for sync tracking
        migrations.AddField(
            model_name='banktransaction',
            name='linked_income_id',
            field=models.IntegerField(blank=True, null=True),
        ),
        # Add linked expense ID for sync tracking
        migrations.AddField(
            model_name='banktransaction',
            name='linked_expense_id',
            field=models.IntegerField(blank=True, null=True),
        ),
    ]