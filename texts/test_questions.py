TEST_QUESTIONS = [
    {
        "question": "Как вы обычно реагируете на стрессовые ситуации?",
        "options": [
            "Ищу поддержку у близких",
            "Анализирую ситуацию логически",
            "Занимаюсь спортом или хобби",
            "Избегаю конфликтов"
        ],
        "weights": {
            "support": [3, 1, 1, 2],  # Вес для шкалы "поддержка"
            "logic": [1, 3, 1, 1],   # Вес для шкалы "логика"
            "action": [1, 1, 3, 1],  # Вес для шкалы "действие"
            "avoidance": [2, 1, 1, 3] # Вес для шкалы "избегание"
        }
    },
    {
        "question": "Что для вас важнее в отношениях с людьми?",
        "options": [
            "Эмоциональная близость",
            "Взаимопонимание и доверие",
            "Совместные интересы",
            "Уважение личных границ"
        ],
        "weights": {
            "emotional": [3, 2, 1, 1],
            "understanding": [2, 3, 1, 2],
            "interests": [1, 1, 3, 1],
            "boundaries": [1, 2, 1, 3]
        }
    },
    {
        "question": "Как вы принимаете важные решения?",
        "options": [
            "Обсуждаю с близкими",
            "Взвешиваю все за и против",
            "Доверяюсь интуиции",
            "Консультируюсь со специалистами"
        ],
        "weights": {
            "discussion": [3, 1, 1, 2],
            "analysis": [1, 3, 1, 2],
            "intuition": [1, 1, 3, 1],
            "expertise": [2, 2, 1, 3]
        }
    },
    {
        "question": "Что вас больше мотивирует в жизни?",
        "options": [
            "Достижение целей",
            "Помощь другим",
            "Личностный рост",
            "Стабильность и комфорт"
        ],
        "weights": {
            "achievement": [3, 1, 2, 1],
            "help": [1, 3, 2, 1],
            "growth": [2, 2, 3, 1],
            "stability": [1, 1, 1, 3]
        }
    },
    {
        "question": "Как вы относитесь к изменениям?",
        "options": [
            "Люблю новые возможности",
            "Предпочитаю планировать заранее",
            "Адаптируюсь постепенно",
            "Избегаю резких перемен"
        ],
        "weights": {
            "openness": [3, 1, 2, 1],
            "planning": [1, 3, 1, 2],
            "adaptation": [2, 1, 3, 1],
            "conservatism": [1, 2, 1, 3]
        }
    },
    {
        "question": "Что для вас значит успех?",
        "options": [
            "Финансовая независимость",
            "Гармония в отношениях",
            "Признание достижений",
            "Внутреннее удовлетворение"
        ],
        "weights": {
            "financial": [3, 1, 1, 2],
            "relationships": [1, 3, 1, 2],
            "recognition": [2, 1, 3, 1],
            "satisfaction": [1, 2, 2, 3]
        }
    },
    {
        "question": "Как вы справляетесь с конфликтами?",
        "options": [
            "Обсуждаю открыто",
            "Ищу компромисс",
            "Избегаю эскалации",
            "Защищаю свою позицию"
        ],
        "weights": {
            "openness": [3, 2, 1, 1],
            "compromise": [2, 3, 1, 2],
            "avoidance": [1, 1, 3, 1],
            "defense": [1, 2, 1, 3]
        }
    },
    {
        "question": "Что вас вдохновляет в других людях?",
        "options": [
            "Их достижения",
            "Их доброта и empathy",
            "Их креативность",
            "Их надежность"
        ],
        "weights": {
            "achievement": [3, 1, 1, 2],
            "kindness": [1, 3, 1, 2],
            "creativity": [1, 1, 3, 1],
            "reliability": [2, 2, 1, 3]
        }
    },
    {
        "question": "Как вы проводите свободное время?",
        "options": [
            "В компании друзей",
            "За чтением или обучением",
            "Активно (спорт, путешествия)",
            "В спокойствии дома"
        ],
        "weights": {
            "social": [3, 1, 2, 1],
            "intellectual": [1, 3, 1, 2],
            "active": [2, 1, 3, 1],
            "relaxed": [1, 2, 1, 3]
        }
    },
    {
        "question": "Что для вас важнее в профессиональной деятельности?",
        "options": [
            "Высокая зарплата",
            "Интересная работа",
            "Полезность для общества",
            "Работа в команде"
        ],
        "weights": {
            "salary": [3, 1, 1, 1],
            "interest": [1, 3, 2, 1],
            "usefulness": [1, 2, 3, 1],
            "teamwork": [1, 1, 1, 3]
        }
    }
]

# Шкалы для расчета совместимости
COMPATIBILITY_SCALES = {
    "emotional_support": ["emotional", "support", "kindness"],
    "logical_analysis": ["logic", "analysis", "intellectual"],
    "action_orientation": ["action", "active", "achievement"],
    "relationship_focus": ["understanding", "relationships", "teamwork"],
    "stability_preference": ["boundaries", "stability", "reliability"]
}

# Функция расчета процента совместимости
def calculate_match_percentage(user1_answers, user2_answers):
    """
    Рассчитывает процент совместимости между двумя пользователями
    на основе их ответов на тест
    """
    if not user1_answers or not user2_answers:
        return 50  # Базовый процент если кто-то не прошел тест

    total_score = 0
    max_score = 0

    for scale_name, scale_factors in COMPATIBILITY_SCALES.items():
        user1_scale_score = sum(user1_answers.get(factor, 0) for factor in scale_factors)
        user2_scale_score = sum(user2_answers.get(factor, 0) for factor in scale_factors)

        # Совместимость по шкале - чем ближе значения, тем лучше
        scale_compatibility = 100 - abs(user1_scale_score - user2_scale_score) * 10
        scale_compatibility = max(0, min(100, scale_compatibility))

        total_score += scale_compatibility
        max_score += 100

    return round((total_score / max_score) * 100)
