import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv
from database import Database
from texts.messages import *
from texts.test_questions import TEST_QUESTIONS, calculate_match_percentage
import json

# Загрузка переменных окружения
load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_USER_IDS = [int(id.strip()) for id in os.getenv('ADMIN_USER_IDS', '').split(',') if id.strip()]
DB_PATH = os.getenv('DB_PATH', 'psymatch.db')
LOG_FILE = os.getenv('LOG_FILE', 'bot.log')

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class PsyMatchBot:
    def __init__(self):
        self.db = Database(DB_PATH)
        self.user_states = {}  # Хранение состояний пользователей
        self.user_test_data = {}  # Данные теста пользователей

    def get_main_keyboard(self, user_id):
        """Получение основной клавиатуры в зависимости от роли пользователя"""
        user = self.db.get_user(user_id)
        if not user:
            return None

        keyboard = []

        if user['role'] == 'psychologist':
            keyboard = [
                [InlineKeyboardButton("👀 Посмотреть лайки", callback_data="view_likes")],
                [InlineKeyboardButton("📊 Моя статистика", callback_data="my_stats")],
            ]
        else:  # patient
            keyboard = [
                [InlineKeyboardButton("🔍 Искать психологов", callback_data="start_swiping")],
                [InlineKeyboardButton("📊 Моя статистика", callback_data="my_stats")],
            ]

        if user_id in ADMIN_USER_IDS:
            keyboard.append([InlineKeyboardButton("⚙️ Админ панель", callback_data="admin_panel")])

        return InlineKeyboardMarkup(keyboard)

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        user = update.effective_user
        user_id = user.id

        logger.info(f"User {user_id} started the bot")

        # Обновляем активность пользователя
        self.db.update_last_active(user_id)

        # Проверяем, зарегистрирован ли пользователь
        existing_user = self.db.get_user(user_id)

        if existing_user:
            # Пользователь уже зарегистрирован
            role_emoji = "👨‍⚕️" if existing_user['role'] == 'psychologist' else "👤"
            welcome_text = f"С возвращением, {existing_user['name'] or 'пользователь'}! {role_emoji}"
            reply_markup = self.get_main_keyboard(user_id)
            await update.message.reply_text(welcome_text, reply_markup=reply_markup)
        else:
            # Новый пользователь - показываем выбор роли
            keyboard = [
                [InlineKeyboardButton("👨‍⚕️ Я психолог", callback_data="role_psychologist")],
                [InlineKeyboardButton("👤 Я пациент", callback_data="role_patient")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(START_MESSAGE, reply_markup=reply_markup)

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик callback запросов"""
        query = update.callback_query
        user_id = query.from_user.id
        data = query.data

        logger.info(f"Callback from user {user_id}: {data}")

        # Обновляем активность
        self.db.update_last_active(user_id)

        await query.answer()

        if data.startswith("role_"):
            await self.handle_role_selection(query, data)
        elif data == "start_profile_setup":
            await self.start_profile_setup(query)
        elif data == "start_test":
            await self.start_psychological_test(query)
        elif data.startswith("test_answer_"):
            await self.handle_test_answer(query, data)
        elif data == "start_swiping":
            await self.start_swiping(query)
        elif data.startswith("swipe_"):
            await self.handle_swipe(query, data)
        elif data == "view_likes":
            await self.view_likes(query)
        elif data == "my_stats":
            await self.show_user_stats(query)
        elif data == "admin_panel":
            await self.show_admin_panel(query)

    async def handle_role_selection(self, query, data):
        """Обработка выбора роли"""
        user_id = query.from_user.id
        role = data.replace("role_", "")

        # Регистрируем пользователя
        self.db.register_user(user_id, role)

        # Сохраняем состояние для настройки профиля
        self.user_states[user_id] = {
            'state': 'profile_setup',
            'step': 'photo',
            'role': role
        }

        if role == 'psychologist':
            text = PSYCHOLOGIST_PROFILE_SETUP
        else:
            text = PATIENT_PROFILE_SETUP

        await query.edit_message_text(text)

    async def start_profile_setup(self, query):
        """Начало настройки профиля"""
        user_id = query.from_user.id
        user = self.db.get_user(user_id)

        self.user_states[user_id] = {
            'state': 'profile_setup',
            'step': 'photo',
            'role': user['role']
        }

        if user['role'] == 'psychologist':
            text = PSYCHOLOGIST_PROFILE_SETUP
        else:
            text = PATIENT_PROFILE_SETUP

        await query.edit_message_text(text)

    async def start_psychological_test(self, query):
        """Начало психологического теста"""
        user_id = query.from_user.id

        self.user_test_data[user_id] = {
            'current_question': 0,
            'answers': {}
        }

        await self.show_test_question(query)

    async def show_test_question(self, query_or_message, is_callback=True):
        """Показ вопроса теста"""
        user_id = query_or_message.from_user.id if hasattr(query_or_message, 'from_user') else query_or_message.chat.id

        test_data = self.user_test_data.get(user_id)
        if not test_data:
            return

        question_index = test_data['current_question']
        if question_index >= len(TEST_QUESTIONS):
            # Тест завершен
            await self.finish_test(query_or_message, is_callback)
            return

        question = TEST_QUESTIONS[question_index]

        text = TEST_QUESTION.format(
            current=question_index + 1,
            total=len(TEST_QUESTIONS),
            question=question['question']
        )

        keyboard = []
        for i, option in enumerate(question['options']):
            keyboard.append([InlineKeyboardButton(option, callback_data=f"test_answer_{i}")])

        reply_markup = InlineKeyboardMarkup(keyboard)

        if is_callback:
            await query_or_message.edit_message_text(text, reply_markup=reply_markup)
        else:
            await query_or_message.reply_text(text, reply_markup=reply_markup)

    async def handle_test_answer(self, query, data):
        """Обработка ответа на вопрос теста"""
        user_id = query.from_user.id
        answer_index = int(data.replace("test_answer_", ""))

        test_data = self.user_test_data.get(user_id)
        if not test_data:
            return

        question_index = test_data['current_question']
        question = TEST_QUESTIONS[question_index]

        # Сохраняем ответ
        test_data['answers'].update(question['weights'])
        for scale, weights in question['weights'].items():
            current_value = test_data['answers'].get(scale, 0)
            test_data['answers'][scale] = current_value + weights[answer_index]

        # Переходим к следующему вопросу
        test_data['current_question'] += 1
        await self.show_test_question(query)

    async def finish_test(self, query_or_message, is_callback=True):
        """Завершение теста"""
        user_id = query_or_message.from_user.id if hasattr(query_or_message, 'from_user') else query_or_message.chat.id

        test_data = self.user_test_data.get(user_id)
        if test_data:
            # Сохраняем результаты теста
            self.db.save_test_answers(user_id, test_data['answers'])

            # Очищаем данные теста
            del self.user_test_data[user_id]

        text = TEST_COMPLETED
        reply_markup = self.get_main_keyboard(user_id)

        if is_callback:
            await query_or_message.edit_message_text(text, reply_markup=reply_markup)
        else:
            await query_or_message.reply_text(text, reply_markup=reply_markup)

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик текстовых сообщений"""
        user_id = update.effective_user.id
        message_text = update.message.text
        user_state = self.user_states.get(user_id)

        if not user_state:
            return

        # Обновляем активность
        self.db.update_last_active(user_id)

        if user_state['state'] == 'profile_setup':
            await self.handle_profile_setup_message(update, user_state)

    async def handle_profile_setup_message(self, update, user_state):
        """Обработка сообщений настройки профиля"""
        user_id = update.effective_user.id
        message = update.message
        step = user_state['step']
        role = user_state['role']

        if step == 'photo':
            if message.photo:
                # Сохраняем фото
                photo_file_id = message.photo[-1].file_id
                self.db.update_user_profile(user_id, photo_file_id=photo_file_id)

                user_state['step'] = 'name'
                if role == 'psychologist':
                    await message.reply_text("Отлично! Теперь введите ваше имя:")
                else:
                    await message.reply_text("Отлично! Теперь введите ваше имя:")
            else:
                await message.reply_text("Пожалуйста, отправьте фото профиля.")

        elif step == 'name':
            self.db.update_user_profile(user_id, name=message.text)

            if role == 'psychologist':
                user_state['step'] = 'education'
                await message.reply_text("Расскажите о вашем образовании:")
            else:
                user_state['step'] = 'request'
                await message.reply_text("Опишите ваш основной запрос к психологу:")

        elif step == 'education':
            self.db.update_user_profile(user_id, education=message.text)
            user_state['step'] = 'experience'
            await message.reply_text("Опишите ваш опыт работы:")

        elif step == 'experience':
            self.db.update_user_profile(user_id, experience=message.text)
            # Завершаем настройку профиля психолога
            user_state['state'] = 'ready'
            user_state['step'] = None

            keyboard = [[InlineKeyboardButton("🚀 Начать тест", callback_data="start_test")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await message.reply_text("Профиль заполнен! Теперь пройдите психологический тест:", reply_markup=reply_markup)

        elif step == 'request':
            self.db.update_user_profile(user_id, request=message.text)
            # Завершаем настройку профиля пациента
            user_state['state'] = 'ready'
            user_state['step'] = None

            keyboard = [[InlineKeyboardButton("🚀 Начать тест", callback_data="start_test")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await message.reply_text("Профиль заполнен! Теперь пройдите психологический тест:", reply_markup=reply_markup)

    async def start_swiping(self, query):
        """Начало листания профилей"""
        user_id = query.from_user.id
        user = self.db.get_user(user_id)

        if not user:
            return

        # Определяем, кого искать
        role_to_find = 'psychologist' if user['role'] == 'patient' else 'patient'

        # Получаем первый профиль
        profiles = self.db.get_profiles_for_swiping(user_id, role_to_find, 0, 1)

        if not profiles:
            await query.edit_message_text(NO_MORE_PROFILES, reply_markup=self.get_main_keyboard(user_id))
            return

        profile = profiles[0]

        # Логируем просмотр профиля
        self.db.log_analytics(user_id, 'view_profile', profile['user_id'], 1)

        await self.show_profile_card(query, profile, 0, role_to_find)

    async def show_profile_card(self, query, profile, position, role_to_find):
        """Показ карточки профиля"""
        user_id = query.from_user.id
        user = self.db.get_user(user_id)

        # Вычисляем процент совместимости
        user_answers = user.get('test_answers', {})
        profile_answers = profile.get('test_answers', {})
        match_percent = calculate_match_percentage(user_answers, profile_answers)

        # Формируем текст профиля
        role_emoji = "👨‍⚕️" if profile['role'] == 'psychologist' else "👤"
        role_text = "Психолог" if profile['role'] == 'psychologist' else "Пациент"

        if profile['role'] == 'psychologist':
            description = f"🎓 Образование: {profile.get('education', 'Не указано')}\n💼 Опыт: {profile.get('experience', 'Не указано')}"
        else:
            description = f"📝 Запрос: {profile.get('request', 'Не указано')}"

        text = PROFILE_TEMPLATE.format(
            name=profile.get('name', 'Имя не указано'),
            role_emoji=role_emoji,
            role=role_text,
            description=description,
            match_percent=match_percent
        )

        # Клавиатура для листания
        keyboard = [
            [InlineKeyboardButton("👎 Пропустить", callback_data=f"swipe_left_{profile['user_id']}_{position}")],
            [InlineKeyboardButton("💖 Лайк", callback_data=f"swipe_right_{profile['user_id']}_{position}")]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        # Отправляем фото и текст
        if profile.get('photo_file_id'):
            await query.message.reply_photo(
                photo=profile['photo_file_id'],
                caption=text,
                reply_markup=reply_markup
            )
            # Удаляем предыдущее сообщение
            await query.message.delete()
        else:
            await query.edit_message_text(text, reply_markup=reply_markup)

    async def handle_swipe(self, query, data):
        """Обработка свайпа (лайк/пропуск)"""
        user_id = query.from_user.id
        parts = data.split('_')
        action = parts[1]  # left или right
        target_user_id = int(parts[2])
        position = int(parts[3])

        user = self.db.get_user(user_id)
        role_to_find = 'psychologist' if user['role'] == 'patient' else 'patient'

        # Логируем действие
        self.db.log_analytics(user_id, f'swipe_{action}', target_user_id, position)

        if action == 'right':
            # Лайк
            is_new_like = self.db.add_like(user_id, target_user_id)

            if is_new_like:
                # Проверяем взаимный лайк
                if self.db.check_mutual_like(user_id, target_user_id):
                    # Это матч!
                    target_user = self.db.get_user(target_user_id)

                    # Уведомляем обоих пользователей
                    match_text = MATCH_FOUND.format(
                        contact_info=self.get_contact_info(target_user)
                    )
                    await query.edit_message_text(match_text, reply_markup=self.get_main_keyboard(user_id))

                    # Логируем матч
                    self.db.log_analytics(user_id, 'match', target_user_id)
                    return
                else:
                    await query.answer(LIKE_SENT)
            else:
                await query.answer("Вы уже лайкнули этого пользователя")

        # Отмечаем профиль как просмотренный
        self.db.mark_profile_viewed(user_id, target_user_id)

        # Показываем следующий профиль
        next_profiles = self.db.get_profiles_for_swiping(user_id, role_to_find, position + 1, 1)

        if next_profiles:
            await self.show_profile_card(query, next_profiles[0], position + 1, role_to_find)
        else:
            await query.edit_message_text(NO_MORE_PROFILES, reply_markup=self.get_main_keyboard(user_id))

    def get_contact_info(self, user):
        """Получение контактной информации пользователя"""
        info_parts = []
        if user.get('name'):
            info_parts.append(f"Имя: {user['name']}")

        # В реальном приложении здесь должна быть контактная информация
        # Пока просто возвращаем имя и ID для демонстрации
        info_parts.append(f"Telegram ID: {user['user_id']}")

        return "\n".join(info_parts)

    async def view_likes(self, query):
        """Просмотр лайков (для психологов)"""
        user_id = query.from_user.id
        likes = self.db.get_likes_for_user(user_id)

        if not likes:
            await query.edit_message_text("Пока никто вас не лайкнул 😔", reply_markup=self.get_main_keyboard(user_id))
            return

        text = "Пользователи, которые вас лайкнули:\n\n"

        for i, liker in enumerate(likes[:10], 1):  # Показываем первые 10
            text += f"{i}. {liker.get('name', 'Без имени')} (ID: {liker['user_id']})\n"
            text += f"   Контакты: {self.get_contact_info(liker)}\n\n"

        reply_markup = self.get_main_keyboard(user_id)
        await query.edit_message_text(text, reply_markup=reply_markup)

    async def show_user_stats(self, query):
        """Показ статистики пользователя"""
        user_id = query.from_user.id

        # Получаем базовую статистику
        user = self.db.get_user(user_id)
        likes_given = self.db.get_connection().execute(
            "SELECT COUNT(*) FROM likes WHERE from_user_id = ?", (user_id,)
        ).fetchone()[0]

        likes_received = len(self.db.get_likes_for_user(user_id))

        text = f"📊 Ваша статистика:\n\n"
        text += f"👤 Роль: {'Психолог' if user['role'] == 'psychologist' else 'Пациент'}\n"
        text += f"💖 Лайков отправлено: {likes_given}\n"
        text += f"👍 Лайков получено: {likes_received}\n"
        text += f"📅 Дата регистрации: {user['registered_at'][:10] if user['registered_at'] else 'Неизвестно'}"

        reply_markup = self.get_main_keyboard(user_id)
        await query.edit_message_text(text, reply_markup=reply_markup)

    async def show_admin_panel(self, query):
        """Показ админ панели"""
        user_id = query.from_user.id

        if user_id not in ADMIN_USER_IDS:
            await query.answer("У вас нет доступа к админ панели")
            return

        stats = self.db.get_statistics()

        text = ADMIN_STATS.format(**stats)

        reply_markup = self.get_main_keyboard(user_id)
        await query.edit_message_text(text, reply_markup=reply_markup)

    def run(self):
        """Запуск бота"""
        application = Application.builder().token(BOT_TOKEN).build()

        # Обработчики команд
        application.add_handler(CommandHandler("start", self.start))

        # Обработчик callback запросов
        application.add_handler(CallbackQueryHandler(self.handle_callback))

        # Обработчик текстовых сообщений
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))

        # Обработчик фото
        application.add_handler(MessageHandler(filters.PHOTO, self.handle_message))

        logger.info("Bot started")
        application.run_polling()

if __name__ == "__main__":
    bot = PsyMatchBot()
    bot.run()
