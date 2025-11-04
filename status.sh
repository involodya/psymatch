#!/bin/bash

# Скрипт для проверки статуса PsyMatch

echo "📊 Статус PsyMatch"
echo "=================="
echo ""

# Проверяем бота
BOT_PID=$(pgrep -f "python.*bot.py")
if [ -n "$BOT_PID" ]; then
    echo "🤖 Telegram бот: ✅ Запущен (PID: $BOT_PID)"
    # Проверяем использование памяти
    MEM=$(ps -o rss= -p $BOT_PID | awk '{print $1/1024 " MB"}')
    echo "   Память: $MEM"
else
    echo "🤖 Telegram бот: ❌ Остановлен"
fi

echo ""

# Проверяем админку
ADMIN_PID=$(pgrep -f "python.*admin_app.py")
if [ -n "$ADMIN_PID" ]; then
    echo "🌐 Веб-админка: ✅ Запущена (PID: $ADMIN_PID)"
    MEM=$(ps -o rss= -p $ADMIN_PID | awk '{print $1/1024 " MB"}')
    echo "   Память: $MEM"
    echo "   URL: http://localhost:5000"
else
    echo "🌐 Веб-админка: ❌ Остановлена"
fi

echo ""
echo "📁 Файлы:"

# Проверяем наличие важных файлов
if [ -f .env ]; then
    echo "   .env: ✅"
else
    echo "   .env: ❌ Отсутствует"
fi

if [ -f psymatch.db ]; then
    SIZE=$(du -h psymatch.db | cut -f1)
    echo "   psymatch.db: ✅ ($SIZE)"
else
    echo "   psymatch.db: ❌ Отсутствует"
fi

if [ -f bot.log ]; then
    SIZE=$(du -h bot.log | cut -f1)
    LINES=$(wc -l < bot.log)
    echo "   bot.log: ✅ ($SIZE, $LINES строк)"
else
    echo "   bot.log: ⚠️  Отсутствует"
fi

echo ""
echo "📊 База данных:"

if [ -f psymatch.db ]; then
    # Статистика пользователей
    PSYCHOLOGISTS=$(sqlite3 psymatch.db "SELECT COUNT(*) FROM users WHERE user_type='psychologist';")
    PATIENTS=$(sqlite3 psymatch.db "SELECT COUNT(*) FROM users WHERE user_type='patient';")
    echo "   Психологов: $PSYCHOLOGISTS"
    echo "   Пациентов: $PATIENTS"
    
    # Фича-флаги
    echo ""
    echo "🎛️  Фича-флаги:"
    sqlite3 psymatch.db "SELECT flag_name, CASE WHEN enabled=1 THEN '✅ ON' ELSE '❌ OFF' END FROM feature_flags;" | while read line; do
        echo "   $line"
    done
fi

echo ""
echo "💡 Полезные команды:"
echo "   ./start.sh    - Запустить"
echo "   ./stop.sh     - Остановить"
echo "   ./restart.sh  - Перезапустить"
echo "   tail -f bot.log - Смотреть логи"

