from django.core.management.base import BaseCommand

from scheduler.services import run_due_scheduled_jobs


class Command(BaseCommand):
    help = (
        'Run scheduled jobs that are due (see scheduler.ScheduledJob). '
        'Run this command every minute (or faster) via cron, systemd timer, or a worker.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=50,
            help='Maximum jobs to process in one invocation (default: 50).',
        )

    def handle(self, *args, **options):
        n = run_due_scheduled_jobs(limit=int(options['limit']))
        self.stdout.write(self.style.SUCCESS(f'Scheduler processed {n} job(s).'))
