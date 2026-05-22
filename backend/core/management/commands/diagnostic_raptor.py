"""
Django Management Command: Diagnostic for RAPTOR + Mineru + DocumentChunk

Usage:
    python manage.py diagnostic_raptor [--document-id=<uuid>]
"""

from django.core.management.base import BaseCommand, CommandError
from services.diagnostic_raptor_mineru import run_diagnostic, print_diagnostic_report


class Command(BaseCommand):
    help = 'Diagnostic for RAPTOR + Mineru + DocumentChunk pipeline'

    def add_arguments(self, parser):
        parser.add_argument(
            '--document-id',
            type=str,
            help='Specific document ID to diagnose',
        )

    def handle(self, *args, **options):
        document_id = options.get('document_id')
        
        self.stdout.write(
            self.style.SUCCESS('🔍 Running RAPTOR + Mineru diagnostic...')
        )
        
        try:
            report = run_diagnostic(document_id)
            print_diagnostic_report(report)
            
            if report['total_issues'] == 0:
                self.stdout.write(
                    self.style.SUCCESS(
                        '\n✅ All diagnostic checks passed!'
                    )
                )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f"\n⚠️  {report['total_issues']} issue(s) found. "
                        f"Please review above."
                    )
                )
        except Exception as e:
            raise CommandError(f'Diagnostic failed: {str(e)}')
