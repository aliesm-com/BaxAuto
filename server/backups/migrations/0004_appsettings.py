from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('backups', '0003_backuprecord_scheduled_job'),
    ]

    operations = [
        migrations.CreateModel(
            name='AppSettings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                (
                    'keep_local_backups',
                    models.BooleanField(
                        default=True,
                        help_text=(
                            'If disabled, drop the local copy after a successful upload to remote storage '
                            '(S3/SFTP/FTP). Download and restore then pick a remote (or local if still present).'
                        ),
                    ),
                ),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'App settings',
                'verbose_name_plural': 'App settings',
            },
        ),
    ]
