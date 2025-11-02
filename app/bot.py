from __future__ import annotations

import logging
from enum import Enum, auto
from typing import List, Optional

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    Update,
)
from telegram.error import BadRequest
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from .config import Settings
from .db import Database, User
from . import matching
from .resources import load_questions, load_texts


logger = logging.getLogger("psymatch")


class RegistrationState(Enum):
    CHOOSING_ROLE = auto()
    PATIENT_CONTACT = auto()
    PATIENT_REQUEST = auto()
    PATIENT_TEST = auto()
    PSY_CONTACT = auto()
    PSY_EDUCATION = auto()
    PSY_EXPERIENCE = auto()
    PSY_BIO = auto()
    PSY_PHOTO = auto()
    PSY_TEST = auto()


class PsymatchBot:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.db = Database(settings.database_path)
        self.texts = load_texts()
        self.questions = load_questions()
        self.application = self._build_application()

    def _build_application(self) -> Application:
        application = ApplicationBuilder().token(self.settings.telegram_token).build()

        registration_handler = ConversationHandler(
            entry_points=[CommandHandler("start", self.start)],
            states={
                RegistrationState.CHOOSING_ROLE: [CallbackQueryHandler(self.choose_role, pattern=r"^role:")],
                RegistrationState.PATIENT_CONTACT: [MessageHandler(filters.TEXT & (~filters.COMMAND), self.patient_contact)],
                RegistrationState.PATIENT_REQUEST: [MessageHandler(filters.TEXT & (~filters.COMMAND), self.patient_request)],
                RegistrationState.PATIENT_TEST: [MessageHandler(filters.TEXT & (~filters.COMMAND), self.test_answer)],
                RegistrationState.PSY_CONTACT: [MessageHandler(filters.TEXT & (~filters.COMMAND), self.psychologist_contact)],
                RegistrationState.PSY_EDUCATION: [MessageHandler(filters.TEXT & (~filters.COMMAND), self.psychologist_education)],
                RegistrationState.PSY_EXPERIENCE: [MessageHandler(filters.TEXT & (~filters.COMMAND), self.psychologist_experience)],
                RegistrationState.PSY_BIO: [MessageHandler(filters.TEXT & (~filters.COMMAND), self.psychologist_bio)],
                RegistrationState.PSY_PHOTO: [
                    MessageHandler(filters.PHOTO, self.psychologist_photo),
                    MessageHandler(filters.Regex("^(Пропустить|skip)$"), self.psychologist_photo_skip),
                ],
                RegistrationState.PSY_TEST: [MessageHandler(filters.TEXT & (~filters.COMMAND), self.test_answer)],
            },
            fallbacks=[CommandHandler("cancel", self.cancel)],
            name="registration",
        )

        application.add_handler(registration_handler)
        application.add_handler(CommandHandler("browse", self.browse))
        application.add_handler(CommandHandler("likes", self.likes))
        application.add_handler(CommandHandler("admin", self.admin_stats))
        application.add_handler(CallbackQueryHandler(self.browse_action, pattern=r"^browse:"))
        application.add_handler(CallbackQueryHandler(self.like_back, pattern=r"^likeback:"))

        return application

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> Optional[RegistrationState]:
        telegram_user = update.effective_user
        if not telegram_user:
            return ConversationHandler.END

        db_user = self.db.get_user_by_telegram(telegram_user.id)
        if db_user:
            self.db.update_last_active(db_user.id)
            await self._send_welcome_back(update, db_user)
            return ConversationHandler.END

        keyboard = InlineKeyboardMarkup(
            [[
                InlineKeyboardButton("Пациент", callback_data="role:patient"),
                InlineKeyboardButton("Психолог", callback_data="role:psychologist"),
            ]]
        )

        text = (
            "Привет! Давайте определимся, кто вы: пациент или психолог. "
            "Это поможет настроить профиль и подобрать тест."
        )
        if update.message:
            await update.message.reply_text(text, reply_markup=keyboard)
        elif update.callback_query:
            await update.callback_query.edit_message_text(text=text, reply_markup=keyboard)
        return RegistrationState.CHOOSING_ROLE

    async def choose_role(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> RegistrationState:
        query = update.callback_query
        if not query:
            return RegistrationState.CHOOSING_ROLE
        await query.answer()
        role = query.data.split(":", maxsplit=1)[1]
        telegram_user = update.effective_user
        if not telegram_user:
            return RegistrationState.CHOOSING_ROLE

        username = telegram_user.username
        contact = f"@{username}" if username else None
        user_id = self.db.upsert_user(
            telegram_user.id,
            role,
            username,
            telegram_user.full_name,
            contact,
        )
        self.db.update_last_active(user_id)
        context.user_data.clear()
        context.user_data["role"] = role
        context.user_data["user_id"] = user_id

        logger.info("event=registration_role_chosen role=%s telegram_id=%s", role, telegram_user.id)

        if role == "patient":
            await query.edit_message_text(
                "Как с вами удобнее связаться? Оставьте телефон, @username или email.",
                reply_markup=ReplyKeyboardRemove(),
            )
            return RegistrationState.PATIENT_CONTACT

        await query.edit_message_text(
            "Укажите, как с вами связаться (телефон, @username, email).",
            reply_markup=ReplyKeyboardRemove(),
        )
        return RegistrationState.PSY_CONTACT

    async def patient_contact(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> RegistrationState:
        contact = update.message.text.strip()
        await self._update_user_contact(update, context, contact)
        await update.message.reply_text(
            "Опишите свой основной запрос к психологу.",
            reply_markup=ReplyKeyboardRemove(),
        )
        return RegistrationState.PATIENT_REQUEST

    async def patient_request(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> RegistrationState:
        request = update.message.text.strip()
        user_id = context.user_data["user_id"]
        self.db.save_patient_profile(user_id, request)
        logger.info("event=patient_profile_saved user_id=%s", user_id)
        await self._start_test(update, context, audience="patient")
        return RegistrationState.PATIENT_TEST

    async def psychologist_contact(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> RegistrationState:
        contact = update.message.text.strip()
        await self._update_user_contact(update, context, contact)
        await update.message.reply_text(
            "Расскажите о вашем образовании (институт, программа).",
            reply_markup=ReplyKeyboardRemove(),
        )
        return RegistrationState.PSY_EDUCATION

    async def psychologist_education(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> RegistrationState:
        education = update.message.text.strip()
        context.user_data.setdefault("psych_profile", {})["education"] = education
        await update.message.reply_text("Опишите опыт работы (количество лет, сферы).")
        return RegistrationState.PSY_EXPERIENCE

    async def psychologist_experience(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> RegistrationState:
        experience = update.message.text.strip()
        context.user_data.setdefault("psych_profile", {})["experience"] = experience
        await update.message.reply_text("Добавьте пару предложений о подходе или специализации.")
        return RegistrationState.PSY_BIO

    async def psychologist_bio(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> RegistrationState:
        bio = update.message.text.strip()
        context.user_data.setdefault("psych_profile", {})["bio"] = bio
        keyboard = ReplyKeyboardMarkup([["Пропустить"]], one_time_keyboard=True, resize_keyboard=True)
        await update.message.reply_text(
            "Пришлите фото для карточки профиля или нажмите 'Пропустить'.",
            reply_markup=keyboard,
        )
        return RegistrationState.PSY_PHOTO

    async def psychologist_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> RegistrationState:
        photo = update.message.photo[-1]
        photo_id = photo.file_id
        context.user_data.setdefault("psych_profile", {})["photo_file_id"] = photo_id
        await update.message.reply_text("Фото сохранено.", reply_markup=ReplyKeyboardRemove())
        await self._persist_psychologist_profile(context)
        await self._start_test(update, context, audience="psychologist")
        return RegistrationState.PSY_TEST

    async def psychologist_photo_skip(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> RegistrationState:
        await update.message.reply_text("Переходим дальше.", reply_markup=ReplyKeyboardRemove())
        await self._persist_psychologist_profile(context)
        await self._start_test(update, context, audience="psychologist")
        return RegistrationState.PSY_TEST

    async def _persist_psychologist_profile(self, context: ContextTypes.DEFAULT_TYPE) -> None:
        user_id = context.user_data["user_id"]
        profile = context.user_data.get("psych_profile", {})
        self.db.save_psychologist_profile(
            user_id,
            profile.get("photo_file_id"),
            profile.get("education"),
            profile.get("experience"),
            profile.get("bio"),
        )
        logger.info("event=psychologist_profile_saved user_id=%s", user_id)

    async def _start_test(self, update: Update, context: ContextTypes.DEFAULT_TYPE, audience: str) -> None:
        user_id = context.user_data["user_id"]
        context.user_data["test"] = {
            "audience": audience,
            "questions": list(self.questions[matching.ROLE_TO_SECTION[audience]]),
            "index": 0,
            "answers": {},
        }
        intro = self.texts.get(f"{audience}_intro", "Ответьте на вопросы, используя шкалу 1-5.")
        if update.message:
            await update.message.reply_text(intro, reply_markup=ReplyKeyboardRemove())
        logger.info("event=test_started user_id=%s audience=%s", user_id, audience)
        await self._ask_next_question(update, context)

    async def _ask_next_question(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        test_state = context.user_data.get("test")
        if not test_state:
            return
        index = test_state["index"]
        questions = test_state["questions"]
        if index >= len(questions):
            return
        question = questions[index]
        text = question["text"]
        keyboard = ReplyKeyboardMarkup([["1", "2", "3", "4", "5"]], resize_keyboard=True, one_time_keyboard=True)
        if update.message:
            await update.message.reply_text(text, reply_markup=keyboard)
        elif update.callback_query:
            await update.callback_query.message.reply_text(text, reply_markup=keyboard)

    async def test_answer(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> RegistrationState:
        test_state = context.user_data.get("test")
        if not test_state:
            return ConversationHandler.END

        value_text = update.message.text.strip()
        if value_text not in {"1", "2", "3", "4", "5"}:
            await update.message.reply_text("Пожалуйста, введите число от 1 до 5.")
            return RegistrationState.PATIENT_TEST if test_state["audience"] == "patient" else RegistrationState.PSY_TEST

        value = int(value_text)
        index = test_state["index"]
        questions = test_state["questions"]
        question = questions[index]
        test_state["answers"][question["id"]] = value
        test_state["index"] += 1

        user_id = context.user_data["user_id"]
        logger.info(
            "event=test_answer user_id=%s question=%s value=%s position=%s",
            user_id,
            question["id"],
            value,
            index,
        )

        if test_state["index"] >= len(questions):
            await self._finalize_test(update, context)
            return ConversationHandler.END

        await self._ask_next_question(update, context)
        return RegistrationState.PATIENT_TEST if test_state["audience"] == "patient" else RegistrationState.PSY_TEST

    async def _finalize_test(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        test_state = context.user_data.get("test")
        audience = test_state["audience"]
        answers = test_state["answers"]
        user_id = context.user_data["user_id"]
        traits, ordered_answers = matching.aggregate_traits(audience, answers)
        self.db.save_test_results(user_id, audience, traits, ordered_answers)
        if audience == "patient":
            matching.recalc_for_patient(self.db, user_id)
        else:
            matching.recalc_for_psychologist(self.db, user_id)
        context.user_data.pop("test", None)
        completion = self.texts.get("completion_message", "Спасибо за ответы!")
        await update.message.reply_text(
            completion + "\nДальше можно использовать /browse для просмотра или /likes.",
            reply_markup=ReplyKeyboardRemove(),
        )
        logger.info(
            "event=test_completed user_id=%s audience=%s traits=%s",
            user_id,
            audience,
            traits,
        )

    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        await update.message.reply_text("Диалог отменён.", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END

    async def browse(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        db_user = self._require_role(update, context, "patient")
        if not db_user:
            return

        rows = [dict(row) for row in self.db.get_ranked_psychologists(db_user.id)]
        if not rows:
            await update.message.reply_text("Пока нет психологов для отображения. Попробуйте позже.")
            return

        index = self.db.get_patient_swipe_index(db_user.id)
        if index >= len(rows):
            index = 0
        context.user_data["browse"] = {
            "rows": rows,
            "index": index,
        }
        await self._show_card(update, context, db_user.id, index, rows[index])

    async def browse_action(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        if not query:
            return
        patient = self._require_role(update, context, "patient", query=query)
        if not patient:
            await query.answer("Доступно только для пациентов", show_alert=True)
            return

        data = context.user_data.get("browse")
        if not data:
            await query.answer("Используйте /browse сначала")
            return

        action = query.data.split(":", 1)[1]
        rows: List = data["rows"]
        index = data["index"]
        if action == "next":
            await query.answer()
            index = (index + 1) % len(rows)
        elif action == "prev":
            await query.answer()
            index = (index - 1) % len(rows)
        elif action == "like":
            await self._handle_like(patient, rows[index], query, context)
            return

        data["index"] = index
        await self._show_card(update, context, patient.id, index, rows[index], query=query)

    async def _handle_like(self, patient: User, row, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        psychologist_id = row["id"]
        new_like = self.db.record_like(patient.id, psychologist_id)
        logger.info(
            "event=like_sent from_user=%s to_user=%s new=%s position=%s",
            patient.id,
            psychologist_id,
            new_like,
            context.user_data.get("browse", {}).get("index"),
        )
        if not new_like:
            await query.answer("Вы уже лайкали этого специалиста")
            return
        await query.answer("Лайк отправлен")
        self.db.update_last_active(patient.id)

        psych_profile = self.db.get_psychologist_profile(psychologist_id)
        patient_profile = self.db.get_patient_profile(patient.id)

        if psych_profile:
            contact = patient.contact or patient.username or "Нет контакта"
            patient_name = patient.full_name or patient.username or str(patient.telegram_id)
            message = (
                self.texts.get("like_notification_template", "Пациент {patient_name} оставил лайк.")
                .format(patient_name=patient_name, patient_contact=contact)
            )
            if patient_profile and patient_profile["main_request"]:
                message += f"\nЗапрос: {patient_profile['main_request']}"
            markup = InlineKeyboardMarkup(
                [[InlineKeyboardButton("Ответить взаимно", callback_data=f"likeback:{patient.id}")]]
            )
            await context.bot.send_message(chat_id=psych_profile["telegram_id"], text=message, reply_markup=markup)
            logger.info(
                "event=like_forwarded psychologist_id=%s patient_id=%s",
                psychologist_id,
                patient.id,
            )

        if self.db.has_like(psychologist_id, patient.id):
            self.db.ensure_match(patient.id, psychologist_id)
            await self._notify_match(patient, psych_profile, context)

    async def _notify_match(self, patient: Optional[User], psych_profile, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not patient or not psych_profile:
            return
        contact = psych_profile["contact"] or psych_profile["username"] or "Нет контакта"
        patient_contact = patient.contact or patient.username or "Нет контакта"
        message = (
            self.texts.get("match_notification_template", "У вас взаимный интерес.")
            .format(
                psychologist_name=psych_profile["full_name"] or psych_profile["username"] or "Специалист",
                psychologist_contact=contact,
            )
        )
        await context.bot.send_message(chat_id=patient.telegram_id, text=message)
        await context.bot.send_message(
            chat_id=psych_profile["telegram_id"],
            text=(
                "Взаимный лайк с "
                f"{patient.full_name or patient.username or patient.telegram_id}. "
                f"Контакт: {patient_contact}"
            ),
        )
        logger.info(
            "event=match_confirmed patient_id=%s psychologist_id=%s",
            patient.id,
            psych_profile["id"],
        )

    async def _show_card(self, update: Update, context: ContextTypes.DEFAULT_TYPE, patient_id: int, index: int, row, query=None) -> None:
        text_lines = [
            f"{row['full_name'] or 'Без имени'}",
            f"Процент совпадения: {row['score']:.1f}%",
        ]
        if row["education"]:
            text_lines.append(f"Образование: {row['education']}")
        if row["experience"]:
            text_lines.append(f"Опыт: {row['experience']}")
        if row["bio"]:
            text_lines.append(f"Подход: {row['bio']}")

        text_lines.append(self.texts.get("swipe_hint", ""))
        text = "\n".join(line for line in text_lines if line)
        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("⬅️ Назад", callback_data="browse:prev"),
                    InlineKeyboardButton("❤️ Лайк", callback_data="browse:like"),
                    InlineKeyboardButton("Вперёд ➡️", callback_data="browse:next"),
                ]
            ]
        )

        if query:
            try:
                await query.edit_message_text(text=text, reply_markup=keyboard)
            except BadRequest:
                await query.message.reply_text(text, reply_markup=keyboard)
        else:
            await update.message.reply_text(text, reply_markup=keyboard)

        self.db.set_patient_swipe_index(patient_id, index)
        logger.info(
            "event=card_viewed patient_id=%s psychologist_id=%s position=%s score=%.2f",
            patient_id,
            row["id"],
            index,
            row["score"],
        )

    async def like_back(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        if not query:
            return
        psychologist = self._require_role(update, context, "psychologist", query=query)
        if not psychologist:
            await query.answer("Недоступно", show_alert=True)
            return

        patient_id = int(query.data.split(":", 1)[1])
        new_like = self.db.record_like(psychologist.id, patient_id)
        self.db.update_last_active(psychologist.id)
        if not new_like:
            await query.answer("Уже лайкнули")
            return
        if not self.db.has_like(patient_id, psychologist.id):
            await query.answer("Лайк отправлен")
            return

        self.db.ensure_match(patient_id, psychologist.id)
        patient = self.db.get_user(patient_id)
        psych_profile = self.db.get_psychologist_profile(psychologist.id)
        await self._notify_match(patient, psych_profile, context)
        await query.answer("Есть взаимное совпадение!")

    async def likes(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        db_user = self._require_role(update, context, "psychologist")
        if not db_user:
            return
        rows = self.db.list_patients_who_liked(db_user.id)
        if not rows:
            await update.message.reply_text("Пока никто не поставил лайк.")
            return
        for row in rows:
            lines = [
                row["full_name"] or row["username"] or "Пациент",
                f"Контакт: {row['contact'] or row['username'] or 'не указан'}",
            ]
            if row["main_request"]:
                lines.append(f"Запрос: {row['main_request']}")
            lines.append(f"Лайк от {row['created_at']}")
            text = "\n".join(lines)
            markup = InlineKeyboardMarkup(
                [[InlineKeyboardButton("Ответить взаимно", callback_data=f"likeback:{row['id']}")]]
            )
            await update.message.reply_text(text, reply_markup=markup)

    async def admin_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        telegram_user = update.effective_user
        if not telegram_user or telegram_user.id not in self.settings.admin_whitelist:
            if update.message:
                await update.message.reply_text("Нет доступа.")
            elif update.callback_query:
                await update.callback_query.answer("Нет доступа", show_alert=True)
            return
        stats = self.db.fetch_stats()
        text = self.texts.get("admin_stats_template", "")
        formatted = text.format(**stats)
        heading = self.texts.get("admin_stats_heading", "Статистика")
        await update.message.reply_text(f"{heading}\n{formatted}")
        logger.info("event=admin_stats_viewed telegram_id=%s", telegram_user.id)

    def _require_role(self, update: Update, context: ContextTypes.DEFAULT_TYPE, role: str, query=None) -> Optional[User]:
        telegram_user = update.effective_user
        if not telegram_user:
            return None
        db_user = self.db.get_user_by_telegram(telegram_user.id)
        if not db_user:
            message = "Сначала пройдите регистрацию через /start"
            if query:
                context.application.create_task(query.answer(message, show_alert=True))
            elif update.message:
                context.application.create_task(update.message.reply_text(message))
            return None
        self.db.update_last_active(db_user.id)
        if db_user.role != role:
            message = "Эта команда недоступна для вашей роли"
            if query:
                context.application.create_task(query.answer(message, show_alert=True))
            elif update.message:
                context.application.create_task(update.message.reply_text(message))
            return None
        return db_user

    async def _send_welcome_back(self, update: Update, db_user: User) -> None:
        if update.message:
            await update.message.reply_text(
                "С возвращением! Используйте /browse для просмотра или /likes, чтобы посмотреть отклики."
            )

    async def _update_user_contact(self, update: Update, context: ContextTypes.DEFAULT_TYPE, contact: str) -> None:
        telegram_user = update.effective_user
        user_id = context.user_data["user_id"]
        db_user = self.db.get_user(user_id)
        if not db_user:
            return
        username = telegram_user.username if telegram_user else db_user.username
        full_name = telegram_user.full_name if telegram_user else db_user.full_name
        self.db.upsert_user(
            db_user.telegram_id,
            db_user.role,
            username,
            full_name,
            contact,
        )
        logger.info("event=contact_updated user_id=%s", user_id)

    def run(self) -> None:
        self.application.run_polling()

