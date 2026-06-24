# Generated manually for Goal Lifecycle Management

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('goals', '0001_initial'),
    ]

    operations = [
        # Add status field
        migrations.AddField(
            model_name='goal',
            name='status',
            field=models.CharField(
                choices=[('ACTIVE', 'Active'), ('COMPLETED', 'Completed'), ('OVERDUE', 'Overdue'), ('ARCHIVED', 'Archived')],
                default='ACTIVE',
                max_length=20
            ),
        ),
        # Add is_achieved field (legacy compatibility)
        migrations.AddField(
            model_name='goal',
            name='is_achieved',
            field=models.BooleanField(default=False),
        ),
        # Add created_at field
        migrations.AddField(
            model_name='goal',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        # Add updated_at field
        migrations.AddField(
            model_name='goal',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        # Add indexes
        migrations.AddIndex(
            model_name='goal',
            index=models.Index(fields=['owner', 'status'], name='goals_goal_owner_s_status_idx'),
        ),
        migrations.AddIndex(
            model_name='goal',
            index=models.Index(fields=['end_date'], name='goals_goal_end_dat_idx'),
        ),
    ]
