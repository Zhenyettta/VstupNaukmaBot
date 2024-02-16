from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import MessageHandler, filters, CommandHandler, CallbackQueryHandler

from bot.utils.utils import *

ADMISSION, FACULTY, SPECIALITY, QUESTION, ANSWER, CALCULATE = range(6)

warehouse = json_to_dict("bot/utils/specialties.json")
additional_subjects = [
    "Іноземна мова",
    "Біологія",
    "Фізика",
    "Хімія",
    "Українська література",
    "Географія"
]
all_subjects = ["Історія України", "Математика", "Українська мова"] + additional_subjects + ["bonus"]
pattern = '^(' + '|'.join(all_subjects) + ')$'


async def go_home(update: Update, context: CallbackContext) -> int:
    from bot.handlers.start import start
    await clear_scores(context)
    await start(update, context)
    return ConversationHandler.END


async def admission(update: Update, context: CallbackContext) -> int:
    buttons = [['Бакалаврат', 'Магістратура']]
    return await generic_reply(update, 'Оберіть категорію:', buttons, ADMISSION, back_button=True)


async def faculty(update: Update, context: CallbackContext) -> int:
    if update.message.text != BACK:
        context.user_data['degree'] = update.message.text
    buttons = list(map(lambda x: [x], warehouse[context.user_data.get('degree')].keys()))
    return await generic_reply(update, 'Оберіть факультет:', buttons, FACULTY, back_button=True, home_button=True)


async def clear_scores(context: CallbackContext):
    keys_to_clear = [f'score_{subj}' for subj in all_subjects]
    for key in keys_to_clear:
        context.user_data.pop(key, None)


async def speciality(update: Update, context: CallbackContext) -> int:
    if update.message.text != BACK:
        context.user_data['faculty'] = update.message.text
    buttons = list(
        map(lambda x: [x], warehouse[context.user_data.get('degree')][context.user_data.get('faculty')].keys()))
    return await generic_reply(update, 'Оберіть спеціальність:', buttons, SPECIALITY, back_button=True,
                               home_button=True)


async def question(update: Update, context: CallbackContext) -> int:
    if update.message.text == BACK:
        await clear_scores(context)
    else:
        context.user_data['speciality'] = update.message.text
    buttons = list(map(lambda x: [x], warehouse[context.user_data.get('degree')][context.user_data.get('faculty')][
        context.user_data.get('speciality')].keys()))
    return await generic_reply(update, 'Оберіть питання:', buttons, QUESTION, back_button=True, home_button=True)


async def answer(update: Update, context: CallbackContext) -> int:
    if update.message.text != BACK:
        context.user_data['question'] = update.message.text
    answer_reply = \
        warehouse[context.user_data.get('degree')][context.user_data.get('faculty')][
            context.user_data.get('speciality')][
            context.user_data.get('question')]
    return await generic_reply(update, f"{answer_reply}", [], ANSWER, back_button=True, home_button=True)


async def calculate(update: Update, context: CallbackContext) -> int:
    context.user_data['selected_additional_subject'] = ''
    if update.message.text != BACK:
        context.user_data['question'] = update.message.text
    answer_reply = \
        warehouse[context.user_data.get('degree')][context.user_data.get('faculty')][
            context.user_data.get('speciality')][
            context.user_data.get('question')]

    keyboard = [
        [InlineKeyboardButton("Українська мова", callback_data="Українська мова")],
        [InlineKeyboardButton("Математика", callback_data="Математика")],
        [InlineKeyboardButton("Історія України", callback_data="Історія України")],
        [InlineKeyboardButton("Додатково", callback_data="bonus")],
    ]

    context.user_data['coefficients'] = answer_reply
    reply_markup = InlineKeyboardMarkup(keyboard)

    await generic_reply(update, "Оберіть бали: ", [], CALCULATE, back_button=True, home_button=True,
                        back_home_row=True)
    await update.message.reply_text("Предмети: ", reply_markup=reply_markup)
    return CALCULATE


async def enter_score(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    await query.answer()
    selected_subject = query.data

    if selected_subject == 'bonus':
        additional_subjects_buttons = [[InlineKeyboardButton(subj, callback_data=subj)] for subj in additional_subjects]
        reply_markup = InlineKeyboardMarkup(additional_subjects_buttons)
        await query.edit_message_text(text="Оберіть додатковий предмет:", reply_markup=reply_markup)
    else:
        context.user_data['selected_subject'] = selected_subject
        if selected_subject in additional_subjects:
            context.user_data['selected_additional_subject'] = selected_subject
        await query.edit_message_text(text=f"Введіть ваш бал за предмет {selected_subject}:")
    return CALCULATE


async def calculate_final_score(update: Update, context: CallbackContext):
    coefficients_list = context.user_data['coefficients'].split()

    total_weighted_score = 0
    total_coefficients = 0

    for subject, index in {"Українська мова": 0, "Математика": 1, "Історія України": 2, "Іноземна мова": 3,
                           "Біологія": 4,
                           "Фізика": 5, "Хімія": 6, "Українська література": 7, "Географія": 8}.items():
        score_entry = context.user_data.get(f'score_{subject}', None)
        if score_entry:
            score = float(score_entry.split('=')[-1].strip())
            coefficient = float(coefficients_list[index])
            total_weighted_score += score
            total_coefficients += coefficient

    final_score = round(total_weighted_score / total_coefficients, 2) if total_coefficients > 0 else 0
    await update.callback_query.edit_message_text(text=f"Ваш конкурсний бал: {final_score}")


async def score_received(update: Update, context: CallbackContext) -> int:
    user_input = update.message.text.strip()
    try:
        user_score = float(user_input)
        if 100 <= user_score <= 200:
            selected_subject = context.user_data['selected_subject']

            coefficients_list = context.user_data['coefficients'].split()

            subject_index = {"Українська мова": 0, "Математика": 1, "Історія України": 2, "Іноземна мова": 3,
                             "Біологія": 4,
                             "Фізика": 5, "Хімія": 6, "Українська література": 7, "Географія": 8}
            coefficient = float(coefficients_list[subject_index[selected_subject]])

            final_score = round(user_score * coefficient, 2)

            context.user_data[f'score_{selected_subject}'] = str(user_score) + "*" + str(coefficient) + " = " + str(
                final_score)
            selected_additional_subject = context.user_data.get('selected_additional_subject', '')
            additional_subject_label = selected_additional_subject if selected_additional_subject else "Додатковий"
            keyboard = [
                [InlineKeyboardButton(f"Українська мова: {context.user_data.get('score_Українська мова', '')}",
                                      callback_data="Українська мова")],
                [InlineKeyboardButton(f"Математика: {context.user_data.get('score_Математика', '')}",
                                      callback_data="Математика")],
                [InlineKeyboardButton(f"Історія України: {context.user_data.get('score_Історія України', '')}",
                                      callback_data="Історія України")],
                [InlineKeyboardButton(
                    f"{additional_subject_label}: {context.user_data.get(f'score_{selected_additional_subject}', '')}",
                    callback_data="bonus")]
            ]

            mandatory_subjects = ['score_Українська мова', 'score_Математика', 'score_Історія України']
            mandatory_scores_entered = all(
                context.user_data.get(subject, None) is not None for subject in mandatory_subjects)

            additional_score_entered = any(
                context.user_data.get(f'score_{subject}', None) is not None for subject in additional_subjects)

            all_scores_entered = mandatory_scores_entered and additional_score_entered

            if all_scores_entered:
                keyboard.append(
                    [InlineKeyboardButton("Розрахувати конкурсний бал", callback_data="calculate_final_score")])

            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(
                text="Виберіть наступний предмет або завершіть введення балів.",
                reply_markup=reply_markup
            )

            return CALCULATE
        else:
            await update.message.reply_text("Бал повинен бути в межах від 100 до 200. Спробуйте ще раз.")
            return CALCULATE
    except ValueError:
        await update.message.reply_text("Введено некоректний бал. Бал повинен бути числом. Спробуйте ще раз.")
        return CALCULATE


admission_handler = ConversationHandler(
    entry_points=[MessageHandler(filters.Regex('Вступ на навчання'), admission)],
    states={
        ADMISSION: [MessageHandler(filters.Regex('Бакалаврат|Магістратура'), faculty),
                    MessageHandler(filters.Regex(BACK), go_home)],
        FACULTY: [MessageHandler(filters.Regex(BACK), admission),
                  MessageHandler(filters.Regex(HOME), go_home), MessageHandler(filters.Regex('.*'), speciality)],
        SPECIALITY: [MessageHandler(filters.Regex(BACK), faculty),
                     MessageHandler(filters.Regex(HOME), go_home), MessageHandler(filters.Regex('.*'), question)],
        QUESTION: [MessageHandler(filters.Regex('Розрахувати бали'), calculate),
                   MessageHandler(filters.Regex(BACK), speciality),
                   MessageHandler(filters.Regex(HOME), go_home), MessageHandler(filters.Regex('.*'), answer)],
        CALCULATE: [
            CallbackQueryHandler(enter_score, pattern=pattern),
            CallbackQueryHandler(calculate_final_score, pattern='^calculate_final_score$'),
            MessageHandler(filters.Regex(BACK), question),
            MessageHandler(filters.Regex(HOME), go_home),
            MessageHandler(filters.TEXT & ~filters.COMMAND, score_received)
        ],
        ANSWER: [
            MessageHandler(filters.Regex(BACK), question), MessageHandler(filters.Regex(HOME), go_home)]
    },
    fallbacks=[CommandHandler('start', admission)],
    name="admission-handler",
    persistent=True,
    per_chat=True
)