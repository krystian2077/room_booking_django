#!/usr/bin/env bash
set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --no-input
python manage.py migrate

# Automatyczne załadowanie danych z backup (tylko przy pierwszym wdrożeniu)
if [ -f "db_backup.json" ]; then
    echo "📦 Ładowanie danych z db_backup.json..."
    python manage.py loaddata db_backup.json || echo "⚠️ Dane już załadowane lub błąd (to normalne przy ponownym wdrożeniu)"
fi

echo "✅ Build zakończony pomyślnie!"

