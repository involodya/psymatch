# Руководство по обновлению PsyMatch

## Обновление с v1.0 до v2.0

### Шаг 1: Резервная копия

```bash
cp psymatch.db psymatch.db.backup
```

### Шаг 2: Обновление кода

```bash
git pull
```

### Шаг 3: Установка зависимостей

```bash
pip install -r requirements.txt
```

### Шаг 4: Настройка .env

Добавьте новые переменные в `.env`:

```bash
ADMIN_SECRET_KEY=your_random_secret_key_here
ADMIN_USERNAME=admin
ADMIN_PASSWORD=your_secure_password
```

Для генерации случайного ключа:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### Шаг 5: Применение миграций

```bash
python migrate_db.py
```

Система автоматически определит, какие миграции нужно применить.

### Шаг 6: Перезапуск

```bash
# Остановите бота
kill $(pgrep -f bot.py)

# Запустите заново
python bot.py &
```

### Шаг 7: Запуск веб-админки (опционально)

```bash
python admin_app.py &
# Откройте http://localhost:5001
```

## Что нового в v2.0

### Расширенный профиль психолога
- Пол (Мужской/Женский)
- Возраст (18-100)
- О себе
- Подход (8 вариантов)
- Специализации
- Цена (5 вариантов)

### Фича-флаги
- `psychological_test_and_matching` - управление тестом и подбором
- По умолчанию **выключен**

### Веб-админка
- Статистика в реальном времени
- Управление фича-флагами
- http://localhost:5001

### Новые команды
- `/restart` - удалить свой профиль и начать заново

### Взаимные лайки
- Психолог может лайкнуть пациента в ответ прямо из уведомления

## Создание новой миграции

Для добавления новых изменений в БД:

1. Создайте файл `migrations/004_your_migration.sql`
2. Напишите SQL для изменений
3. Запустите `python migrate_db.py`

Система автоматически применит только новые миграции.

## Проверка статуса миграций

```bash
sqlite3 psymatch.db "SELECT * FROM schema_migrations;"
```

## Откат (если что-то пошло не так)

```bash
# Восстановите из резервной копии
cp psymatch.db.backup psymatch.db

# Или удалите последнюю миграцию из таблицы
sqlite3 psymatch.db "DELETE FROM schema_migrations WHERE version = X;"
```

## Troubleshooting

### Миграция не работает
```bash
# Проверьте структуру БД
sqlite3 psymatch.db ".schema"

# Проверьте примененные миграции
sqlite3 psymatch.db "SELECT * FROM schema_migrations;"
```

### Бот не запускается
```bash
# Проверьте логи
tail -f bot.log

# Проверьте зависимости
pip install -r requirements.txt --upgrade
```

### Админка не открывается
```bash
# Проверьте порт
netstat -tuln | grep 5001

# Запустите в консоли для отладки
python admin_app.py
```

