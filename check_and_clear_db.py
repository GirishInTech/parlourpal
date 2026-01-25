import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'parlorpal.settings')
django.setup()

from core.models import CustomUser, BusinessProfile, Festival, SearchHistory, TwoFactorAuth, UserHistory, PosterGeneration

print("Checking Supabase database...")
print(f"Users: {CustomUser.objects.count()}")
print(f"Business Profiles: {BusinessProfile.objects.count()}")
print(f"Festivals: {Festival.objects.count()}")
print(f"Search History: {SearchHistory.objects.count()}")
print(f"Poster Generation: {PosterGeneration.objects.count()}")
print(f"User History: {UserHistory.objects.count()}")

# Clear all data
response = input("\nDo you want to clear all data and reimport from SQLite? (yes/no): ")
if response.lower() == 'yes':
    print("\nClearing data...")
    UserHistory.objects.all().delete()
    PosterGeneration.objects.all().delete()
    SearchHistory.objects.all().delete()
    TwoFactorAuth.objects.all().delete()
    BusinessProfile.objects.all().delete()
    Festival.objects.all().delete()
    CustomUser.objects.all().delete()
    print("✓ All data cleared. Run: python manage.py loaddata sqlite_backup.json")
else:
    print("No changes made.")
