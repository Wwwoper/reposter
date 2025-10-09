#!/bin/bash

# Отчет для Docker контейнера
# Использование: ./weekly_report_docker.sh [имя_контейнера]

CONTAINER_NAME=${1:-"reposter-bot"}

echo "=== Отчет за неделю (Docker) ==="
echo ""

# Проверка, что контейнер запущен
if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "❌ Контейнер ${CONTAINER_NAME} не запущен"
    exit 1
fi

echo "📊 Статистика публикаций:"
total_success=$(docker exec ${CONTAINER_NAME} sh -c "grep 'Успешная публикация' logs/bot.log* 2>/dev/null | wc -l" || echo "0")
total_errors=$(docker exec ${CONTAINER_NAME} sh -c "grep 'ERROR' logs/bot.log* 2>/dev/null | wc -l" || echo "0")

# Защита от деления на ноль
total=$((total_success + total_errors))
if [ $total -eq 0 ]; then
    success_rate="N/A (нет данных)"
    echo "  ℹ️  Логи пока пустые. Отправьте хотя бы один пост."
else
    # Используем awk вместо bc для надежности
    success_rate=$(awk "BEGIN {printf \"%.1f\", ($total_success * 100) / $total}")
    echo "  ✅ Успешных: $total_success"
    echo "  ❌ Ошибок: $total_errors"
    echo "  📈 Success rate: ${success_rate}%"
fi
echo ""

echo "🕐 Rate limiting:"
rate_limits=$(docker exec ${CONTAINER_NAME} sh -c "grep 'Rate limit' logs/bot.log* 2>/dev/null | wc -l" || echo "0")
echo "  Срабатываний: $rate_limits"
echo ""

echo "🧹 Автоочистка:"
cleanups=$(docker exec ${CONTAINER_NAME} sh -c "grep 'Очищено.*файлов' logs/bot.log* 2>/dev/null | wc -l" || echo "0")
echo "  Выполнено очисток: $cleanups"
echo ""

echo "💾 Использование диска:"
logs_size=$(docker exec ${CONTAINER_NAME} sh -c "du -sh logs/ 2>/dev/null | cut -f1" || echo "N/A")
temp_size=$(docker exec ${CONTAINER_NAME} sh -c "du -sh temp_photos/ 2>/dev/null | cut -f1" || echo "N/A")
echo "  Логи: $logs_size"
echo "  Temp: $temp_size"
echo ""

echo "🔝 Топ пользователей:"
top_users=$(docker exec ${CONTAINER_NAME} sh -c "
    grep 'Успешная публикация' logs/bot.log* 2>/dev/null | \
    grep -oP 'от \K\d+' | \
    sort | uniq -c | sort -rn | head -5
")

if [ -z "$top_users" ]; then
    echo "  Нет данных"
else
    echo "$top_users" | while read count user_id; do
        echo "  ${count} постов - пользователь ${user_id}"
    done
fi

echo ""
echo "⏱ Время работы контейнера:"
docker ps --filter "name=${CONTAINER_NAME}" --format "{{.Status}}"

echo ""
echo "💡 Подсказка: Для просмотра логов в реальном времени:"
echo "   docker logs -f ${CONTAINER_NAME}"
echo "   или"
echo "   docker exec ${CONTAINER_NAME} tail -f logs/bot.log"
