"""Run the study generation queue without repeating uncertain dispatches."""
from time import sleep

from django.core.management.base import BaseCommand
from django.db import close_old_connections

from ...study_jobs import work_once, worker_lock


class Command(BaseCommand):
    help = 'Run the durable private study generation queue.'

    def add_arguments(self, parser):
        parser.add_argument('--once', action='store_true', help='Process one queue iteration and exit.')

    def handle(self, *args, **options):
        with worker_lock() as acquired:
            if not acquired:
                self.stderr.write('Study dispatcher already running.')
                return
            while True:
                close_old_connections()
                try:
                    did_work = work_once()
                except Exception:
                    # Avoid exception strings containing file paths, student text or secrets.
                    self.stderr.write('Study queue iteration failed. A claimed job will recover by receipt.')
                    if options['once']:
                        raise
                    did_work = False
                if options['once']:
                    return
                if not did_work:
                    sleep(1)
