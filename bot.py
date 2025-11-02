import os
import json
import logging
from datetime import datetime
from typing import Dict, Optional
from dotenv import load_dotenv

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ConversationHandler, ContextTypes, filters
)

from database import Database
from matching import MatchingSystem, PsychologicalTest

load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler(os.getenv('LOG_FILE', 'bot.log'), encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_IDS = [int(x) for x in os.getenv('ADMIN_IDS', '').split(',') if x.strip()]
DB_PATH = os.getenv('DATABASE_PATH', 'psymatch.db')

with open('messages.json', 'r', encoding='utf-8') as f:
    MESSAGES = json.load(f)

with open('test_questions.json', 'r', encoding='utf-8') as f:
    TEST_QUESTIONS = json.load(f)

db = Database(DB_PATH)
matching_system = MatchingSystem(db)
psychological_test = PsychologicalTest(TEST_QUESTIONS)

CHOOSING_ROLE, PATIENT_REQUEST, PATIENT_CONTACT = range(3)
PSYCH_PHOTO, PSYCH_NAME, PSYCH_EDUCATION, PSYCH_EXPERIENCE, PSYCH_CONTACT = range(3, 8)
TEST_IN_PROGRESS = 8


def log_user_action(user_id: int, action_type: str, action_data: Optional[str] = None):
    db.log_action(user_id, action_type, action_data)
    logger.info(f"User {user_id} - {action_type}: {action_data}")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.update_last_active(user.id)
    log_user_action(user.id, "command_start")
    
    existing_user = db.get_user(user.id)
    if existing_user:
        if existing_user['test_completed']:
            await show_main_menu(update, context)
            return ConversationHandler.END
    
    keyboard = [
        [InlineKeyboardButton(MESSAGES['role_patient'], callback_data='role_patient')],
        [InlineKeyboardButton(MESSAGES['role_psychologist'], callback_data='role_psychologist')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(MESSAGES['welcome'], reply_markup=reply_markup)
    return CHOOSING_ROLE


async def role_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    role = query.data.split('_')[1]
    
    db.create_user(user.id, user.username, role)
    log_user_action(user.id, "role_selected", role)
    
    context.user_data['role'] = role
    context.user_data['profile_data'] = {}
    
    if role == 'patient':
        await query.edit_message_text(MESSAGES['registration_patient_start'])
        return PATIENT_REQUEST
    else:
        await query.edit_message_text(MESSAGES['registration_psychologist_start'])
        return PSYCH_PHOTO


async def patient_request_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    db.update_last_active(user_id)
    
    context.user_data['profile_data']['request'] = update.message.text
    log_user_action(user_id, "patient_request_entered", update.message.text[:50])
    
    await update.message.reply_text(MESSAGES['registration_patient_contact'])
    return PATIENT_CONTACT


async def patient_contact_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    db.update_last_active(user_id)
    
    contact = update.message.text
    request = context.user_data['profile_data']['request']
    
    db.save_patient_profile(user_id, request, contact)
    log_user_action(user_id, "patient_profile_completed")
    
    await start_psychological_test(update, context)
    return TEST_IN_PROGRESS


async def psychologist_photo_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    db.update_last_active(user_id)
    
    if not update.message.photo:
        await update.message.reply_text(MESSAGES['error_photo_required'])
        return PSYCH_PHOTO
    
    photo = update.message.photo[-1]
    context.user_data['profile_data']['photo_file_id'] = photo.file_id
    log_user_action(user_id, "psychologist_photo_uploaded")
    
    await update.message.reply_text(MESSAGES['registration_psychologist_name'])
    return PSYCH_NAME


async def psychologist_name_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    db.update_last_active(user_id)
    
    context.user_data['profile_data']['name'] = update.message.text
    log_user_action(user_id, "psychologist_name_entered")
    
    await update.message.reply_text(MESSAGES['registration_psychologist_education'])
    return PSYCH_EDUCATION


async def psychologist_education_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    db.update_last_active(user_id)
    
    context.user_data['profile_data']['education'] = update.message.text
    log_user_action(user_id, "psychologist_education_entered")
    
    await update.message.reply_text(MESSAGES['registration_psychologist_experience'])
    return PSYCH_EXPERIENCE


async def psychologist_experience_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    db.update_last_active(user_id)
    
    context.user_data['profile_data']['experience'] = update.message.text
    log_user_action(user_id, "psychologist_experience_entered")
    
    await update.message.reply_text(MESSAGES['registration_psychologist_contact'])
    return PSYCH_CONTACT


async def psychologist_contact_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    db.update_last_active(user_id)
    
    profile_data = context.user_data['profile_data']
    
    db.save_psychologist_profile(
        user_id,
        profile_data['name'],
        profile_data['photo_file_id'],
        profile_data['education'],
        profile_data['experience'],
        update.message.text
    )
    log_user_action(user_id, "psychologist_profile_completed")
    
    await start_psychological_test(update, context)
    return TEST_IN_PROGRESS


async def start_psychological_test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    context.user_data['test_answers'] = {}
    context.user_data['test_current_question'] = 0
    
    total = psychological_test.get_total_questions()
    intro_text = MESSAGES['test_intro'].format(total=total)
    
    await update.message.reply_text(intro_text)
    await send_test_question(update, context, 0)


async def send_test_question(update: Update, context: ContextTypes.DEFAULT_TYPE, question_index: int):
    question_data = psychological_test.get_question(question_index)
    
    if not question_data:
        await complete_test(update, context)
        return
    
    total = psychological_test.get_total_questions()
    question_text = MESSAGES['test_question_template'].format(
        current=question_index + 1,
        total=total,
        question=question_data['question']
    )
    
    keyboard = []
    for i, option in enumerate(question_data['options']):
        keyboard.append([InlineKeyboardButton(option, callback_data=f'test_answer_{question_index}_{i}')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(question_text, reply_markup=reply_markup)
    else:
        await update.message.reply_text(question_text, reply_markup=reply_markup)


async def test_answer_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    db.update_last_active(user_id)
    
    _, _, question_idx, answer_idx = query.data.split('_')
    question_idx = int(question_idx)
    answer_idx = int(answer_idx)
    
    context.user_data['test_answers'][question_idx] = answer_idx
    log_user_action(user_id, "test_answer", f"Q{question_idx}:A{answer_idx}")
    
    next_question = question_idx + 1
    context.user_data['test_current_question'] = next_question
    
    if next_question < psychological_test.get_total_questions():
        await send_test_question(update, context, next_question)
    else:
        await complete_test(update, context)


async def complete_test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id if update.effective_user else context.user_data.get('user_id')
    
    answers = context.user_data.get('test_answers', {})
    values_vector = psychological_test.calculate_values_vector(answers)
    
    db.save_test_result(user_id, values_vector)
    log_user_action(user_id, "test_completed")
    
    user = db.get_user(user_id)
    user_type = user['user_type']
    
    if user_type == 'patient':
        matching_system.calculate_all_matches_for_patient(user_id)
        message = MESSAGES['test_completed'] + '\n\n' + MESSAGES['test_completed_patient']
    else:
        matching_system.calculate_all_matches_for_psychologist(user_id)
        message = MESSAGES['test_completed'] + '\n\n' + MESSAGES['test_completed_psychologist']
    
    if update.callback_query:
        await update.callback_query.edit_message_text(message)
        await show_main_menu_callback(update, context)
    else:
        await update.message.reply_text(message)
        await show_main_menu_message(update, context)
    
    return ConversationHandler.END


async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await show_main_menu_callback(update, context)
    else:
        await show_main_menu_message(update, context)


async def show_main_menu_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = db.get_user(user_id)
    
    if not user:
        await update.message.reply_text(MESSAGES['error_not_registered'])
        return
    
    if user['user_type'] == 'patient':
        keyboard = [[KeyboardButton(MESSAGES['button_browse'])]]
        message = MESSAGES['main_menu_patient']
    else:
        keyboard = [[KeyboardButton(MESSAGES['button_my_likes'])]]
        message = MESSAGES['main_menu_psychologist']
    
    if user_id in ADMIN_IDS:
        keyboard.append([KeyboardButton(MESSAGES['button_stats'])])
    
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(message, reply_markup=reply_markup)


async def show_main_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.callback_query.from_user.id
    user = db.get_user(user_id)
    
    if not user:
        await update.callback_query.message.reply_text(MESSAGES['error_not_registered'])
        return
    
    if user['user_type'] == 'patient':
        keyboard = [[KeyboardButton(MESSAGES['button_browse'])]]
        message = MESSAGES['main_menu_patient']
    else:
        keyboard = [[KeyboardButton(MESSAGES['button_my_likes'])]]
        message = MESSAGES['main_menu_psychologist']
    
    if user_id in ADMIN_IDS:
        keyboard.append([KeyboardButton(MESSAGES['button_stats'])])
    
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.callback_query.message.reply_text(message, reply_markup=reply_markup)


async def browse_psychologists(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    db.update_last_active(user_id)
    log_user_action(user_id, "browse_start")
    
    psychologists = db.get_psychologists_for_patient(user_id)
    
    if not psychologists:
        await update.message.reply_text(MESSAGES['no_more_psychologists'])
        return
    
    context.user_data['psychologists'] = psychologists
    db.update_card_index(user_id, 0)
    
    await show_psychologist_card(update, context, 0)


async def show_psychologist_card(update: Update, context: ContextTypes.DEFAULT_TYPE, index: int):
    user_id = update.effective_user.id
    psychologists = context.user_data.get('psychologists', [])
    
    if not psychologists or index >= len(psychologists):
        await update.message.reply_text(MESSAGES['no_more_psychologists'])
        return
    
    if index < 0:
        index = 0
    
    psychologist = psychologists[index]
    db.update_card_index(user_id, index)
    log_user_action(user_id, "card_viewed", f"Index:{index},Psychologist:{psychologist['user_id']},Match:{psychologist['match_percentage']}")
    
    card_text = MESSAGES['card_psychologist_template'].format(
        name=psychologist['name'],
        education=psychologist['education'],
        experience=psychologist['experience'],
        match=psychologist['match_percentage']
    )
    
    keyboard = []
    nav_buttons = []
    
    if index > 0:
        nav_buttons.append(InlineKeyboardButton(MESSAGES['button_prev'], callback_data=f'card_prev_{index}'))
    
    if index < len(psychologists) - 1:
        nav_buttons.append(InlineKeyboardButton(MESSAGES['button_next'], callback_data=f'card_next_{index}'))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    if not psychologist['already_liked']:
        keyboard.append([InlineKeyboardButton(MESSAGES['button_like'], callback_data=f'like_{psychologist["user_id"]}')])
    else:
        keyboard.append([InlineKeyboardButton('✅ Уже лайкнут', callback_data='already_liked')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.message.delete()
    
    await update.effective_message.reply_photo(
        photo=psychologist['photo_file_id'],
        caption=card_text,
        reply_markup=reply_markup
    )


async def card_navigation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    db.update_last_active(user_id)
    
    data_parts = query.data.split('_')
    direction = data_parts[1]
    current_index = int(data_parts[2])
    
    if direction == 'next':
        new_index = current_index + 1
    else:
        new_index = current_index - 1
    
    await show_psychologist_card(update, context, new_index)


async def like_psychologist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    db.update_last_active(user_id)
    
    psychologist_id = int(query.data.split('_')[1])
    
    created, is_mutual = db.create_like(user_id, psychologist_id)
    
    if not created:
        return
    
    patient_info = db.get_patient_info(user_id)
    psychologist_info = db.get_psychologist_info(psychologist_id)
    
    psychologists = context.user_data.get('psychologists', [])
    match_percentage = next((p['match_percentage'] for p in psychologists if p['user_id'] == psychologist_id), 0)
    
    log_user_action(user_id, "like_sent", f"To:{psychologist_id},Mutual:{is_mutual},Match:{match_percentage}")
    
    await query.message.delete()
    await query.message.reply_text(MESSAGES['like_sent'])
    
    if is_mutual:
        match_text_patient = MESSAGES['match_notification_patient'].format(
            name=psychologist_info['name'],
            contact=psychologist_info['contact']
        )
        await context.bot.send_message(chat_id=user_id, text=match_text_patient)
        
        match_text_psych = MESSAGES['match_notification_psychologist'].format(
            contact=patient_info['contact']
        )
        await context.bot.send_message(chat_id=psychologist_id, text=match_text_psych)
        
        log_user_action(user_id, "match_created", f"With:{psychologist_id}")
    else:
        notification_text = MESSAGES['like_notification_psychologist'].format(
            request=patient_info['main_request'],
            match=match_percentage,
            contact=patient_info['contact']
        )
        await context.bot.send_message(chat_id=psychologist_id, text=notification_text)


async def show_my_likes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    db.update_last_active(user_id)
    log_user_action(user_id, "view_likes")
    
    likes = db.get_likes_for_psychologist(user_id)
    
    if not likes:
        await update.message.reply_text(MESSAGES['likes_list_empty'])
        return
    
    message = MESSAGES['likes_list_header']
    
    for like in likes:
        mutual_text = MESSAGES['mutual_badge'] if like['is_mutual'] else ''
        date_str = like['liked_date'].split('.')[0] if '.' in like['liked_date'] else like['liked_date']
        
        message += MESSAGES['likes_list_item'].format(
            request=like['main_request'][:100],
            match=like['match_percentage'] if like['match_percentage'] else 'N/A',
            contact=like['contact'],
            date=date_str,
            mutual=mutual_text
        )
    
    await update.message.reply_text(message)


async def show_statistics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    db.update_last_active(user_id)
    
    if user_id not in ADMIN_IDS:
        return
    
    log_user_action(user_id, "view_stats")
    
    stats = db.get_statistics()
    
    message = MESSAGES['stats_template'].format(
        psychologists=stats['psychologists_count'],
        patients=stats['patients_count'],
        active_total=stats['active_users_24h'],
        active_psychologists=stats['active_psychologists_24h'],
        active_patients=stats['active_patients_24h'],
        matches_total=stats['mutual_matches'],
        matches_24h=stats['matches_24h']
    )
    
    await update.message.reply_text(message)


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    
    if text == MESSAGES['button_browse']:
        await browse_psychologists(update, context)
    elif text == MESSAGES['button_my_likes']:
        await show_my_likes(update, context)
    elif text == MESSAGES['button_stats']:
        await show_statistics(update, context)


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Регистрация отменена. Используйте /start для начала.')
    return ConversationHandler.END


async def already_liked_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("Вы уже лайкнули этого психолога!")


def main():
    application = Application.builder().token(BOT_TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            CHOOSING_ROLE: [CallbackQueryHandler(role_selected, pattern='^role_')],
            PATIENT_REQUEST: [MessageHandler(filters.TEXT & ~filters.COMMAND, patient_request_received)],
            PATIENT_CONTACT: [MessageHandler(filters.TEXT & ~filters.COMMAND, patient_contact_received)],
            PSYCH_PHOTO: [MessageHandler(filters.PHOTO, psychologist_photo_received)],
            PSYCH_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, psychologist_name_received)],
            PSYCH_EDUCATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, psychologist_education_received)],
            PSYCH_EXPERIENCE: [MessageHandler(filters.TEXT & ~filters.COMMAND, psychologist_experience_received)],
            PSYCH_CONTACT: [MessageHandler(filters.TEXT & ~filters.COMMAND, psychologist_contact_received)],
            TEST_IN_PROGRESS: [CallbackQueryHandler(test_answer_received, pattern='^test_answer_')],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    
    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(card_navigation, pattern='^card_(prev|next)_'))
    application.add_handler(CallbackQueryHandler(like_psychologist, pattern='^like_'))
    application.add_handler(CallbackQueryHandler(already_liked_callback, pattern='^already_liked$'))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    logger.info("Bot started")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()

