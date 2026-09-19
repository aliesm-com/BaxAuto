from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('backups', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='backuprecord',
            name='compressed',
            field=models.BooleanField(
                default=False,
                help_text='True when the stored artifact is gzip (.gz).',
            ),
        ),
        migrations.AddField(
            model_name='backuprecord',
            name='storage_uploads',
            field=models.JSONField(
                blank=True,
                default=list,
                help_text='Per-destination upload results (id, name, kind, ok, remote/error).',
            ),
        ),
    ]
