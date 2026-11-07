import telebot
from telebot import types
import time

TOKEN = "9046707529:AAEfeWamhzao6kIo-B3MIyueSyRy8FTSWVM"  # Токен от @BotFather
ADMIN_PRIVATE_ID = -5509983337  # Ваш личный ID админа
GROUP_CHAT_ID = -5509983337# ID группы (обязательно с минусом!)
CHANNEL_CHAT_ID = -1004368391517 # ID вашего канала для цитат (обязательно с минусом!)

bot = telebot.TeleBot(TOKEN)
USER_DATA = {}

TOTAL_USERS = set()
TOTAL_MESSAGES = 0

@bot.message_handler(commands=['start'])
def start_command(message):
    global TOTAL_USERS
    TOTAL_USERS.add(message.from_user.id)
    text = "💬 <b>Отправь мне свое сообщение или вопрос!</b>\n\n🔒 Всё конфиденциально. Перед отправкой ты сможешь выбрать режим публикации."
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(types.KeyboardButton("/start"))
    bot.send_message(message.chat.id, text, parse_mode="HTML", reply_markup=keyboard)

@bot.message_handler(commands=['stats'])
def stats_command(message):
    if message.from_user.id != ADMIN_PRIVATE_ID:
        return
    text = f"📊 <b>Статистика:</b>\n\n👥 Пользователей: <b>{len(TOTAL_USERS)}</b>\n📩 Сообщений: <b>{TOTAL_MESSAGES}</b>"
    bot.send_message(message.chat.id, text, parse_mode="HTML")

@bot.message_handler(func=lambda m: m.chat.type == 'private' and m.text not in ['/start', '/stats'], 
                     content_types=['text', 'photo', 'video', 'voice', 'video_note', 'document'])
def handle_incoming_media(message):
    global TOTAL_USERS
    user_id = message.from_user.id
    TOTAL_USERS.add(user_id)
    
    media_data = {}
    if message.text:
        media_data = {'type': 'text', 'content': message.text}
    elif message.photo:
        media_data = {'type': 'photo', 'content': message.photo[-1].file_id, 'caption': message.caption or ""}
    elif message.video:
        media_data = {'type': 'video', 'content': message.video.file_id, 'caption': message.caption or ""}
    elif message.voice:
        media_data = {'type': 'voice', 'content': message.voice.file_id}
    elif message.video_note:
        media_data = {'type': 'video_note', 'content': message.video_note.file_id}
    else:
        bot.reply_to(message, "⚠️ Этот тип контента не поддерживается.")
        return

    msg_id = message.message_id
    USER_DATA[f"{user_id}_{msg_id}"] = media_data

    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        types.InlineKeyboardButton("🎭 Анонимно", callback_data=f"anon_{msg_id}"),
        types.InlineKeyboardButton("👁️ Не анонимно", callback_data=f"pub_{msg_id}")
    )
    bot.reply_to(message, "Выбери, как показать сообщение:", reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: call.data.startswith('anon_') or call.data.startswith('pub_'))
def callback_media_handling(call):
    global TOTAL_MESSAGES
    user = call.from_user
    user_id = user.id
    
    try:
        action, msg_id = call.data.split('_')
    except:
        return

    data_key = f"{user_id}_{msg_id}"
    data = USER_DATA.get(data_key)
    if not data:
        try:
            bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
        except:
            pass
        bot.answer_callback_query(call.id, "❌ Данные устарели.")
        return

    TOTAL_MESSAGES += 1
    username = f"@{user.username}" if user.username else "нет"
    is_anon = (action == 'anon')

    # Заголовок для админа
    admin_header = f"📩 <b>От:</b> {user.first_name} ({username})\n🆔 <code>{user.id}</code>\n🔒 <b>Режим:</b> {'🎭 Анонимно' if is_anon else '👁️ Открыто'}\n\n"
    
    # Текст для группы (кто написал)
    group_author = f"👤 <b>Автор:</b> {user.first_name}" if not is_anon else "👤 <b>Автор:</b> Анонимно"
    
    m_type, content = data['type'], data['content']

    # 1. Отправка админу в ЛС
    try:
        if m_type == 'text':
            bot.send_message(ADMIN_PRIVATE_ID, admin_header + f"💬 {content}", parse_mode="HTML")
        elif m_type == 'photo':
            bot.send_photo(ADMIN_PRIVATE_ID, content, caption=admin_header + (f"💬 {data['caption']}" if data['caption'] else ""), parse_mode="HTML")
        elif m_type == 'video':
            bot.send_video(ADMIN_PRIVATE_ID, content, caption=admin_header + (f"💬 {data['caption']}" if data['caption'] else ""), parse_mode="HTML")
        elif m_type == 'voice':
            bot.send_message(ADMIN_PRIVATE_ID, admin_header + "🎙 <b>Голосовое:</b>", parse_mode="HTML")
            bot.send_voice(ADMIN_PRIVATE_ID, content)
        elif m_type == 'video_note':
            bot.send_message(ADMIN_PRIVATE_ID, admin_header + "📹 <b>Видеосообщение:</b>", parse_mode="HTML")
            bot.send_video_note(ADMIN_PRIVATE_ID, content)
    except Exception as e:
        print(f"Ошибка админу: {e}")

    # 2. Отправка в ГРУППУ (с призывом свайпнуть внизу)
    try:
        if m_type == 'text':
            bot.send_message(GROUP_CHAT_ID, f"🔔 <b>Новое сообщение в боте!</b>\n{group_author}\n\n┃ {content}\n\n<i>💬 Свайпните для ответа</i>", parse_mode="HTML")
        elif m_type == 'photo':
            cap = f"🔔 <b>Новое сообщение в боте!</b>\n{group_author}" + (f"\n\n┃ {data['caption']}" if data['caption'] else "") + "\n\n<i>💬 Свайпните для ответа</i>"
            bot.send_photo(GROUP_CHAT_ID, content, caption=cap, parse_mode="HTML")
        elif m_type == 'video':
            cap = f"🔔 <b>Новое сообщение в боте!</b>\n{group_author}" + (f"\n\n┃ {data['caption']}" if data['caption'] else "") + "\n\n<i>💬 Свайпните для ответа</i>"
            bot.send_video(GROUP_CHAT_ID, content, caption=cap, parse_mode="HTML")
        elif m_type == 'voice':
            bot.send_message(GROUP_CHAT_ID, f"🔔 <b>Новое сообщение в боте!</b>\n{group_author}\n\n🎙 <b>Голосовое:</b>\n\n<i>💬 Свайпните для ответа</i>", parse_mode="HTML")
            bot.send_voice(GROUP_CHAT_ID, content)
        elif m_type == 'video_note':
            bot.send_message(GROUP_CHAT_ID, f"🔔 <b>Новое сообщение в боте!</b>\n{group_author}\n\n📹 <b>Видеосообщение:</b>\n\n<i>💬 Свайпните для ответа</i>", parse_mode="HTML")
            bot.send_video_note(GROUP_CHAT_ID, content)
    except Exception as e:
        print(f"⚠️ Ошибка группы: {e}")

    # 3. Отправка в КАНАЛ (цитата + свайп внизу)
    try:
        if m_type == 'text':
            bot.send_message(CHANNEL_CHAT_ID, f"🔔 <b>У вас новое анонимное сообщение!</b>\n\n<blockquote>{content}</blockquote>\n\n<i>💬 Свайпните для ответа</i>", parse_mode="HTML")
        elif m_type == 'photo':
            cap = "🔔 <b>У вас новое анонимное сообщение!</b>" + (f"\n\n<blockquote>{data['caption']}</blockquote>" if data['caption'] else "") + "\n\n<i>💬 Свайпните для ответа</i>"
            bot.send_photo(CHANNEL_CHAT_ID, content, caption=cap, parse_mode="HTML")
        elif m_type == 'video':
            cap = "🔔 <b>У вас новое анонимное сообщение!</b>" + (f"\n\n<blockquote>{data['caption']}</blockquote>" if data['caption'] else "") + "\n\n<i>💬 Свайпните для ответа</i>"
            bot.send_video(CHANNEL_CHAT_ID, content, caption=cap, parse_mode="HTML")
        elif m_type == 'voice':
            bot.send_voice(CHANNEL_CHAT_ID, content, caption="🔔 <b>У вас новое анонимное сообщение!</b>\n\n<blockquote>🎙 Голосовое сообщение</blockquote>\n\n<i>💬 Свайпните для ответа</i>", parse_mode="HTML")
        elif m_type == 'video_note':
            bot.send_video_note(CHANNEL_CHAT_ID, content)
    except Exception as e:
        print(f"⚠️ Ошибка канала: {e}")

    USER_DATA.pop(data_key, None)

    try:
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="✅ Отправлено!", reply_markup=None)
    except:
        pass

if __name__ == "__main__":
    print("Бот запущен...")
    while True:
        try:
            bot.remove_webhook()
            bot.infinity_polling(timeout=60, long_polling_timeout=60)
        except Exception as e:
            print(f"⚠️ Ошибка: {e}. Переподключение...")
            time.sleep(3)
