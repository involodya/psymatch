#!/bin/bash

# Скрипт для остановки PsyMatch бота и админки

echo "🛑 Остановка PsyMatch..."

# Останавливаем бота
BOT_PIDS=$(pgrep -f "python.*bot.py")
if [ -n "$BOT_PIDS" ]; then
    echo "Остановка Telegram бота (PID: $BOT_PIDS)..."
    pkill -f "python.*bot.py"
    echo "✅ Бот остановлен"
else
    echo "⚠️  Бот не запущен"
fi

# Останавливаем админку
ADMIN_PIDS=$(pgrep -f "python.*admin_app.py")
if [ -n "$ADMIN_PIDS" ]; then
    echo "Остановка веб-админки (PID: $ADMIN_PIDS)..."
    pkill -f "python.*admin_app.py"
    echo "✅ Админка остановлена"
else
    echo "⚠️  Админка не запущена"
fi

echo ""
echo "✨ PsyMatch остановлен"

