#!/usr/bin/env bash
set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --no-input

# Automatyczne tworzenie migracji jeśli są potrzebne
echo "🔄 Sprawdzanie i tworzenie nowych migracji..."
python manage.py makemigrations --noinput

# Aplikowanie migracji
echo "🔄 Aplikowanie migracji..."
python manage.py migrate

# Automatyczne załadowanie danych z backup (tylko przy pierwszym wdrożeniu)
if [ -f "db_backup.json" ]; then
    echo "📦 Ładowanie danych z db_backup.json..."
    python manage.py loaddata db_backup.json --ignorenonexistent || echo "⚠️ Dane już załadowane lub błąd (to normalne przy ponownym wdrożeniu)"
    echo "✅ Próba załadowania danych zakończona"
fi

# Tworzenie superusera jeśli nie istnieje
echo "👤 Sprawdzanie/tworzenie superusera..."
python manage.py shell << EOF
from django.contrib.auth.models import User
if not User.objects.filter(username='krystian').exists():
    User.objects.create_superuser('krystian', 'krystian@example.com', 'admin')
    print('✅ Utworzono superusera: krystian')
else:
    # Aktualizacja hasła dla istniejącego użytkownika
    user = User.objects.get(username='krystian')
    user.set_password('admin')
    user.is_superuser = True
    user.is_staff = True
    user.save()
    print('✅ Zaktualizowano hasło dla użytkownika: krystian')
EOF

echo "✅ Build zakończony pomyślnie!"



