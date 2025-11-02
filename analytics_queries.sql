-- Примеры SQL-запросов для аналитики бота PsyMatch

-- =====================================================
-- ОСНОВНАЯ СТАТИСТИКА
-- =====================================================

-- Общее количество пользователей по типам
SELECT 
    user_type,
    COUNT(*) as count
FROM users
GROUP BY user_type;

-- Количество завершивших регистрацию (прошли тест)
SELECT 
    user_type,
    COUNT(*) as total,
    SUM(CASE WHEN test_completed = 1 THEN 1 ELSE 0 END) as completed_test,
    ROUND(SUM(CASE WHEN test_completed = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as completion_rate
FROM users
GROUP BY user_type;

-- =====================================================
-- АКТИВНОСТЬ ПОЛЬЗОВАТЕЛЕЙ
-- =====================================================

-- Пользователи, активные за последние N дней
SELECT 
    user_type,
    COUNT(*) as active_users
FROM users
WHERE datetime(last_active) >= datetime('now', '-7 days')
GROUP BY user_type;

-- Распределение активности по дням недели
SELECT 
    strftime('%w', last_active) as day_of_week,
    COUNT(*) as activity_count
FROM users
GROUP BY day_of_week
ORDER BY day_of_week;

-- Среднее время между регистрацией и последней активностью
SELECT 
    user_type,
    AVG(julianday(last_active) - julianday(registration_date)) as avg_days_active
FROM users
GROUP BY user_type;

-- =====================================================
-- МАТЧИНГ И ЛАЙКИ
-- =====================================================

-- Общее количество лайков и матчей
SELECT 
    COUNT(*) as total_likes,
    SUM(CASE WHEN is_mutual = 1 THEN 1 ELSE 0 END) as mutual_matches,
    ROUND(SUM(CASE WHEN is_mutual = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as match_rate
FROM likes;

-- Топ-10 психологов по количеству полученных лайков
SELECT 
    pp.name,
    COUNT(*) as likes_received,
    SUM(CASE WHEN l.is_mutual = 1 THEN 1 ELSE 0 END) as mutual_matches
FROM likes l
JOIN psychologist_profiles pp ON l.to_user_id = pp.user_id
GROUP BY l.to_user_id, pp.name
ORDER BY likes_received DESC
LIMIT 10;

-- Распределение процентов совместимости при лайках
SELECT 
    CASE 
        WHEN m.match_percentage >= 90 THEN '90-100%'
        WHEN m.match_percentage >= 80 THEN '80-89%'
        WHEN m.match_percentage >= 70 THEN '70-79%'
        WHEN m.match_percentage >= 60 THEN '60-69%'
        ELSE '< 60%'
    END as match_range,
    COUNT(*) as likes_count
FROM likes l
JOIN matches m ON l.from_user_id = m.patient_id AND l.to_user_id = m.psychologist_id
GROUP BY match_range
ORDER BY match_range DESC;

-- Средний процент совместимости при взаимных лайках vs обычных
SELECT 
    CASE WHEN l.is_mutual = 1 THEN 'Mutual' ELSE 'One-way' END as like_type,
    AVG(m.match_percentage) as avg_match,
    MIN(m.match_percentage) as min_match,
    MAX(m.match_percentage) as max_match
FROM likes l
JOIN matches m ON l.from_user_id = m.patient_id AND l.to_user_id = m.psychologist_id
GROUP BY like_type;

-- =====================================================
-- ПОВЕДЕНИЕ ПОЛЬЗОВАТЕЛЕЙ (из логов)
-- =====================================================

-- На какой по счету карточке пользователи ставят первый лайк
WITH first_like AS (
    SELECT user_id, MIN(timestamp) as first_like_time
    FROM user_actions
    WHERE action_type = 'like_sent'
    GROUP BY user_id
),
cards_before_like AS (
    SELECT 
        ua.user_id,
        COUNT(*) as cards_viewed
    FROM user_actions ua
    JOIN first_like fl ON ua.user_id = fl.user_id
    WHERE ua.action_type = 'card_viewed'
    AND ua.timestamp < fl.first_like_time
    GROUP BY ua.user_id
)
SELECT 
    AVG(cards_viewed) as avg_cards_before_first_like,
    MIN(cards_viewed) as min_cards,
    MAX(cards_viewed) as max_cards
FROM cards_before_like;

-- Конверсия просмотров в лайки
SELECT 
    COUNT(CASE WHEN action_type = 'card_viewed' THEN 1 END) as total_views,
    COUNT(CASE WHEN action_type = 'like_sent' THEN 1 END) as total_likes,
    ROUND(
        COUNT(CASE WHEN action_type = 'like_sent' THEN 1 END) * 100.0 / 
        COUNT(CASE WHEN action_type = 'card_viewed' THEN 1 END), 
        2
    ) as conversion_rate
FROM user_actions;

-- Среднее количество просмотров на пользователя
SELECT 
    user_type,
    AVG(views_per_user) as avg_views
FROM (
    SELECT 
        u.user_type,
        ua.user_id,
        COUNT(*) as views_per_user
    FROM user_actions ua
    JOIN users u ON ua.user_id = u.user_id
    WHERE ua.action_type = 'card_viewed'
    GROUP BY ua.user_id, u.user_type
)
GROUP BY user_type;

-- Распределение ответов на каждый вопрос теста
-- (полезно для понимания, какие ответы наиболее популярны)
WITH parsed_answers AS (
    SELECT 
        user_id,
        action_data
    FROM user_actions
    WHERE action_type = 'test_answer'
)
SELECT 
    SUBSTR(action_data, INSTR(action_data, 'Q') + 1, INSTR(action_data, ':') - INSTR(action_data, 'Q') - 1) as question_num,
    SUBSTR(action_data, INSTR(action_data, 'A') + 1) as answer_num,
    COUNT(*) as count
FROM parsed_answers
GROUP BY question_num, answer_num
ORDER BY question_num, answer_num;

-- =====================================================
-- ВРЕМЕННЫЕ МЕТРИКИ
-- =====================================================

-- Регистрации по дням
SELECT 
    DATE(registration_date) as date,
    user_type,
    COUNT(*) as registrations
FROM users
GROUP BY DATE(registration_date), user_type
ORDER BY date DESC;

-- Лайки по дням
SELECT 
    DATE(liked_date) as date,
    COUNT(*) as total_likes,
    SUM(CASE WHEN is_mutual = 1 THEN 1 ELSE 0 END) as mutual_likes
FROM likes
GROUP BY DATE(liked_date)
ORDER BY date DESC;

-- Пиковые часы активности
SELECT 
    strftime('%H', timestamp) as hour,
    COUNT(*) as actions
FROM user_actions
GROUP BY hour
ORDER BY actions DESC;

-- =====================================================
-- RETENTION И ENGAGEMENT
-- =====================================================

-- Сколько дней прошло с регистрации для активных пользователей
SELECT 
    CASE 
        WHEN days_since_reg <= 1 THEN '0-1 days'
        WHEN days_since_reg <= 7 THEN '2-7 days'
        WHEN days_since_reg <= 30 THEN '8-30 days'
        ELSE '30+ days'
    END as cohort,
    COUNT(*) as users
FROM (
    SELECT 
        user_id,
        julianday(last_active) - julianday(registration_date) as days_since_reg
    FROM users
    WHERE datetime(last_active) >= datetime('now', '-1 day')
)
GROUP BY cohort;

-- Engagement: среднее количество действий на пользователя
SELECT 
    u.user_type,
    COUNT(DISTINCT ua.user_id) as active_users,
    COUNT(*) as total_actions,
    ROUND(COUNT(*) * 1.0 / COUNT(DISTINCT ua.user_id), 2) as avg_actions_per_user
FROM user_actions ua
JOIN users u ON ua.user_id = u.user_id
WHERE datetime(ua.timestamp) >= datetime('now', '-7 days')
GROUP BY u.user_type;

-- =====================================================
-- КАЧЕСТВО МАТЧИНГА
-- =====================================================

-- Средний процент совместимости по всем парам
SELECT 
    AVG(match_percentage) as avg_match,
    MIN(match_percentage) as min_match,
    MAX(match_percentage) as max_match,
    COUNT(*) as total_pairs
FROM matches;

-- Распределение совместимости
SELECT 
    CASE 
        WHEN match_percentage >= 90 THEN '90-100%'
        WHEN match_percentage >= 80 THEN '80-89%'
        WHEN match_percentage >= 70 THEN '70-79%'
        WHEN match_percentage >= 60 THEN '60-69%'
        ELSE '< 60%'
    END as match_range,
    COUNT(*) as pairs_count,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM matches), 2) as percentage
FROM matches
GROUP BY match_range
ORDER BY match_range DESC;

-- =====================================================
-- ЭКСПОРТНЫЕ ЗАПРОСЫ
-- =====================================================

-- Экспорт всех взаимных матчей для дальнейшего анализа
SELECT 
    pat.main_request,
    psy.name as psychologist_name,
    psy.education,
    psy.experience,
    m.match_percentage,
    l1.liked_date as patient_liked_date,
    l2.liked_date as psychologist_liked_date
FROM likes l1
JOIN likes l2 ON l1.from_user_id = l2.to_user_id AND l1.to_user_id = l2.from_user_id
JOIN patient_profiles pat ON l1.from_user_id = pat.user_id
JOIN psychologist_profiles psy ON l1.to_user_id = psy.user_id
JOIN matches m ON l1.from_user_id = m.patient_id AND l1.to_user_id = m.psychologist_id
WHERE l1.is_mutual = 1
ORDER BY m.match_percentage DESC;

