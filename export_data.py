import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'parlorpal.settings')
django.setup()

from django.core.management import call_command

# Export data with UTF-8 encoding
print("Exporting data from SQLite...")
with open('sqlite_backup.json', 'w', encoding='utf-8') as f:
    call_command(
        'dumpdata',
        '--natural-foreign',
        '--natural-primary',
        '-e', 'contenttypes',
        '-e', 'auth.Permission',
        '--indent', '2',
        stdout=f
    )

print("✓ Data exported successfully to sqlite_backup.json")
