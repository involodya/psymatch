#!/bin/bash

# Скрипт для запуска PsyMatch бота и админки

echo "🚀 Запуск PsyMatch..."

# Проверяем, что .env существует
if [ ! -f .env ]; then
    echo "❌ Файл .env не найден!"
    echo "Скопируйте env.example в .env и настройте его:"
    echo "  cp env.example .env"
    echo "  nano .env"
    exit 1
fi

# Проверяем, установлены ли зависимости
if ! python -c "import telegram" 2>/dev/null; then
    echo "⚠️  Зависимости не установлены. Устанавливаем..."
    pip install -r requirements.txt
fi

# Останавливаем старые процессы
echo "🛑 Остановка старых процессов..."
pkill -f "python.*bot.py" 2>/dev/null
pkill -f "python.*admin_app.py" 2>/dev/null
sleep 2

# Запускаем бота
echo "🤖 Запуск Telegram бота..."
nohup python bot.py > bot_output.log 2>&1 &
BOT_PID=$!
echo "✅ Бот запущен (PID: $BOT_PID)"

# Ждем немного
sleep 2

# Запускаем админку
echo "🌐 Запуск веб-админки..."
nohup python admin_app.py > admin_output.log 2>&1 &
ADMIN_PID=$!
echo "✅ Админка запущена (PID: $ADMIN_PID)"

echo ""
echo "✨ PsyMatch успешно запущен!"
echo ""
echo "📊 Статус:"
echo "  - Telegram бот: запущен (PID: $BOT_PID)"
echo "  - Веб-админка: http://localhost:5000 (PID: $ADMIN_PID)"
echo ""
echo "📝 Логи:"
echo "  - Бот: tail -f bot.log"
echo "  - Админка: tail -f admin_output.log"
echo ""
echo "🛑 Остановить: ./stop.sh"

