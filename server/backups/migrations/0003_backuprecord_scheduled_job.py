# Generated manually for retention + scheduled_job link.

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('backups', '0002_backuprecord_compressed_storage'),
        ('scheduler', '0002_scheduledjob_retention_days'),
    ]

    operations = [
        migrations.AddField(
            model_name='backuprecord',
            name='scheduled_job',
            field=models.ForeignKey(
                blank=True,
                help_text='Set when this backup was produced by a schedule (used for retention).',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='backup_records',
                to='scheduler.scheduledjob',
            ),
        ),
        migrations.AddIndex(
            model_name='backuprecord',
            index=models.Index(fields=['scheduled_job', '-created_at'], name='backups_bac_schedul_6f2a1c_idx'),
        ),
    ]
