import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'parlorpal.settings')
django.setup()

from django.core import serializers
from core.models import CustomUser, BusinessProfile, Festival, SearchHistory, TwoFactorAuth, UserHistory, PosterGeneration

# Load the backup
with open('sqlite_backup.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Track imported user IDs to avoid duplicates (use dict to track which profiles we've seen)
imported_profiles = {}

print("Starting import...")
successful = 0
skipped = 0
errors = 0

for item in data:
    model_name = item['model']
    
    # Skip sessions - they're temporary anyway
    if model_name == 'sessions.session':
        skipped += 1
        continue
    
    try:
        # Special handling for BusinessProfile to avoid duplicate user_id
        if model_name == 'core.businessprofile':
            user_id = item['fields'].get('user')
            if not isinstance(user_id, (int, str)):
                print(f"Skipping BusinessProfile pk={item.get('pk')}: invalid user_id type")
                skipped += 1
                continue
            if user_id in imported_profiles:
                print(f"Skipping duplicate BusinessProfile for user_id={user_id}")
                skipped += 1
                continue
            imported_profiles[user_id] = item.get('pk')
        
        # Fix PosterGeneration cloudinary_url field if too long
        if model_name == 'core.postergeneration':
            url = item['fields'].get('cloudinary_url', '')
            if len(url) > 200:
                # Truncate or skip
                print(f"Skipping PosterGeneration pk={item.get('pk')}: URL too long ({len(url)} chars)")
                skipped += 1
                continue
        
        # Deserialize and save
        for obj in serializers.deserialize('json', json.dumps([item])):
            obj.save()
        successful += 1
        
    except Exception as e:
        print(f"Error importing {model_name} pk={item.get('pk')}: {e}")
        errors += 1

print(f"\n✓ Import complete!")
print(f"  Successful: {successful}")
print(f"  Skipped: {skipped}")
print(f"  Errors: {errors}")
