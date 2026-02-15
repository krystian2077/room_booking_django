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

echo "✅ Build zakończony pomyślnie!"



