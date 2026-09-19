from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('scheduler', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='scheduledjob',
            name='retention_days',
            field=models.PositiveIntegerField(
                blank=True,
                default=30,
                help_text=(
                    'For backup jobs: delete successful backups from this schedule older than N days. '
                    'Leave empty to keep forever.'
                ),
                null=True,
            ),
        ),
    ]
