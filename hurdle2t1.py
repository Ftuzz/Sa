import os
import json
import logging
import asyncio
import time
import random
import requests
import pytz
import sqlite3
from datetime import datetime, timedelta
from aiohttp import ClientSession
from collections import defaultdict
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, InputFile, ChatType
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.utils import executor
from aiogram.utils.exceptions import InvalidQueryID
from aiogram.utils.callback_data import CallbackData

from telethon import TelegramClient, connection, events, sync
from telethon.sessions import StringSession
from telethon.errors import (FloodWaitError, RPCError, SessionPasswordNeededError, PhoneNumberUnoccupiedError,
                             PhoneCodeInvalidError, PhoneNumberInvalidError, AuthKeyUnregisteredError, AuthKeyDuplicatedError)
from telethon.tl.types import (InputReportReasonSpam, InputReportReasonViolence, InputReportReasonChildAbuse,
                               InputReportReasonPornography, InputReportReasonCopyright, InputReportReasonGeoIrrelevant, InputReportReasonOther, InputPhoto)
from telethon.tl.functions.messages import ReportRequest
from telethon.tl.functions.account import ReportProfilePhotoRequest
from telethon.tl.functions.photos import GetUserPhotosRequest
import re
from telethon.tl.functions.messages import ReportRequest
from telethon.tl.types import InputReportReasonSpam
from aiogram.dispatcher.filters import Text

remove_sessions_cb = CallbackData("remove_sessions", "sessions")

class BotnetStates(StatesGroup):
    waiting_for_link = State()

logging.basicConfig(filename='logger.txt', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
telethon_logger = logging.getLogger('telethon')
telethon_logger.setLevel(logging.WARNING)
        
with open('token2.txt', 'r') as file:
    TOKEN = file.read().strip()
    
def update_complaints_file():
    try:
        with open("complaints.txt", "r") as file:
            content = file.read().strip()
            total_complaints = int(content) if content else 0
    except FileNotFoundError:
        total_complaints = 0
    except ValueError:
        total_complaints = 0

    total_complaints += 1

    with open("complaints.txt", "w") as file:
        file.write(str(total_complaints))

    return total_complaints

def load_json_file(filename, default):
    try:
        if os.path.exists(filename):
            with open(filename, 'r') as file:
                return json.load(file)
        with open(filename, 'w') as file:
            json.dump(default, file)
        return default
    except Exception as e:
        logging.error(f"Ошибка при загрузке файла {filename}: {e}")
        return default

def save_json_file(filename, data):
    try:
        with open(filename, 'w') as file:
            json.dump(data, file)
    except Exception as e:
        logging.error(f"Ошибка при сохранении файла {filename}: {e}")
        
class SMSStates(StatesGroup):
    waiting_for_text = State()

config = load_json_file('config.json', {'admin_ids': [7478271108], 'allowed_users': {}})
subscriptions = load_json_file('subscriptions.json', {})
banned_users = load_json_file('bans.json', [])

API_ID = '23300181'
API_HASH = 'b5397f2e4d24ddc8a901f36e0b612425'
obratka = [7478271108]
CHANNEL_ID = -1002292993041

bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
scheduler = AsyncIOScheduler()
scheduler.start()

notified_users = {}

def get_expiration_date(duration):
    if duration.endswith('d'):
        return datetime.now(pytz.utc) + timedelta(days=int(duration[:-1]))
    elif duration.endswith('h'):
        return datetime.now(pytz.utc) + timedelta(hours=int(duration[:-1]))
    else:
        raise ValueError("Invalid duration format")

def format_expiration_date(expiration_date):
    moscow_tz = pytz.timezone('Europe/Moscow')
    moscow_time = expiration_date.astimezone(moscow_tz)
    return moscow_time.strftime('%d.%m.%Y %H:%M:%S')

async def notify_expiration(user_id):
    keyboard = InlineKeyboardMarkup()
    button_contact = InlineKeyboardButton("Связаться", url="https://t.me/TEHEB0U")
    button_info = InlineKeyboardButton("Связаться", url="https://t.me/tipadoyes")
    keyboard.add(button_contact, button_info)
    
    await bot.send_message(user_id, "<b>пон", reply_markup=keyboard, parse_mode='html')
    
    subscriptions.pop(str(user_id), None)
    config['allowed_users'].pop(str(user_id), None)
    save_json_file('subscriptions.json', subscriptions)
    save_json_file('config.json', config)

async def notify_expiration_soon(user_id):
    keyboard = InlineKeyboardMarkup()
    button_contact = InlineKeyboardButton("Связаться", url="https://t.me/TEHEB0U")
    button_info = InlineKeyboardButton("Связаться", url="https://t.me/tipadoyes")
    keyboard.add(button_contact, button_info)
    
    await bot.send_message(user_id, "<b>пон</b>", reply_markup=keyboard, parse_mode='html')

async def check_subscriptions():
    now = datetime.now(pytz.utc)
    to_notify_expiration = []
    to_notify_expiration_soon = []

    for user_id, info in subscriptions.items():
        expiration = info.get('expiration')
        if expiration:
            expiration_date = datetime.strptime(expiration, "%d.%m.%Y %H:%M:%S")
            expiration_date = pytz.utc.localize(expiration_date)
            if expiration_date <= now:
                to_notify_expiration.append(user_id)
            elif expiration_date - timedelta(days=1) <= now and user_id not in notified_users:
                to_notify_expiration_soon.append(user_id)
                notified_users[user_id] = True

    for user_id in to_notify_expiration:
        await notify_expiration(user_id)

    for user_id in to_notify_expiration_soon:
        await notify_expiration_soon(user_id)
        
@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    user_id = str(message.from_user.id)

    markup = types.InlineKeyboardMarkup(row_width=2)
    chanel = types.InlineKeyboardButton("🛑 Купить подписку", url='http://t.me/send?start=IV16JEwNUu9Q')
    chanetl = types.InlineKeyboardButton("🔧 Тех Поддержка", url='http://t.me/amogus_ybit')
    chanell = types.InlineKeyboardButton("📋 Правила", url='https://telegra.ph/Manual-10-25-13')
    chanelil = types.InlineKeyboardButton("📕 Руководство", url='https://telegra.ph/StraySnos-10-25-2')
    botnet_button = types.InlineKeyboardButton("🤖BotNet-Snos", callback_data="botnet")
    markup.add(chanel,chanetl,chanell,chanelil, botnet_button)

    if user_id in subscriptions:
        expiration_date = subscriptions[user_id].get('expiration')
        if expiration_date:
            expiration_date = datetime.strptime(expiration_date, "%d.%m.%Y %H:%M:%S")
            expiration_date = pytz.utc.localize(expiration_date)
            if expiration_date > datetime.now(pytz.utc):
                await message.answer_photo(
                    photo=InputFile('hurdle.jpg'),
                    caption=(
                        "<b>✟ lusɴᴏs — мощный и безжалостный инструмент для устранения нарушителей в Telegram. Сочетая скорость и агрессию, LuSnos мгновенно расправляется с аккаунтами, отправляя жалобы с максимальной точностью и эффективностью.Ваша подписка активна до:</b> "
                        f"{expiration_date.strftime('%d.%m.%Y %H:%M:%S')}"
                    ),
                    reply_markup=markup,
                    parse_mode='HTML'
                )
                return

    with open('hurdle.jpg', 'rb') as hurdle2:
        await message.answer_photo(
            photo=hurdle2,
            caption='<b>✟ lusɴᴏs — мощный и безжалостный инструмент для устранения нарушителей в Telegram. Сочетая скорость и агрессию, LuSnos мгновенно расправляется с аккаунтами, отправляя жалобы с максимальной точностью и эффективностью.</b>',
            reply_markup=markup,
            parse_mode='HTML'
        )

@dp.message_handler(state=SMSStates.waiting_for_text)
async def process_sms_text(message: types.Message, state: FSMContext):
    if message.from_user.id == 6211376572:
        sms_text = message.text
        success_count = 0
        fail_count = 0

        for user_id in config['allowed_users']:
            try:
                await bot.send_message(user_id, sms_text)
                success_count += 1
                await asyncio.sleep(0.1)
            except Exception as e:
                logging.error(f"<b>Не удалось отправить сообщение пользователю {user_id}: {e}</b>")
                fail_count += 1

        await state.finish()
        await message.reply(f"<b>Рассылка завершена.\nУдачно: {success_count}\nНеудачно: {fail_count}</b>", parse_mode='html')
    else:
        await message.reply("<b>Извините, эта команда доступна только разработчику.</b>", parse_mode='html')
        
@dp.message_handler(commands=['add'])
async def add_user(message: types.Message):
    user_id = message.from_user.id
    if user_id in config['admin_ids']:
        try:
            args = message.get_args().split()
            new_user_id = int(args[0])
            duration = args[1] if len(args) > 1 else None
            if str(new_user_id) not in subscriptions:
                expiration_date = get_expiration_date(duration) if duration else None
                expiration_str = format_expiration_date(expiration_date) if expiration_date else None
                subscriptions[str(new_user_id)] = {"expiration": expiration_str}
                config['allowed_users'][str(new_user_id)] = {"expiration": expiration_str}
                save_json_file('subscriptions.json', subscriptions)
                save_json_file('config.json', config)
                if duration:
                    await message.reply(f"<b>Добавлен пользователь с подпиской на {duration}</b>", parse_mode='html')
                    expiration_message = f"<b>Поздравляем с приобретением подписки на {duration}\nВаша подписка действует до {expiration_str}</b>" if expiration_date else "<b>Пользователь добавлен с неограниченной подпиской.</b>"
                    await bot.send_message(new_user_id, expiration_message, parse_mode='html')
                    if expiration_date:
                        scheduler.add_job(notify_expiration_soon, 'date', run_date=expiration_date - timedelta(days=1), args=[new_user_id])
                        scheduler.add_job(notify_expiration, 'date', run_date=expiration_date, args=[new_user_id])
                else:
                    await message.reply("<b>Пользователь добавлен с неограниченной подпиской.</b>", parse_mode='html')
                    await bot.send_message(new_user_id, "<b>Поздравляем! Вам предоставлена неограниченная подписка.</b>", parse_mode='html')
            else:
                await message.reply("<b>Пользователь уже в списке.</b>", parse_mode='html')
        except (ValueError, IndexError):
            await message.reply("<b>Использование: /add <user_id> <duration></b>", parse_mode='html')
    else:
        await message.reply("<b>У вас нет доступа к этой команде.</b>", parse_mode='html')

username_pattern = re.compile(r'^@(\w+)$')

@dp.message_handler(commands=['id'])
async def get_user_id(message: types.Message):
    args = message.text.split()
    if len(args) != 2:
        await message.reply("<b>Пожалуйста, укажите юзернейм в формате /id @username</b>", parse_mode='HTML')
        return

    username = args[1]
    if not username_pattern.match(username):
        await message.reply("<b>Пожалуйста, укажите юзернейм в формате @username</b>", parse_mode='HTML')
        return

    try:
        user = await bot.get_chat(username)
        user_id = user.id
        user_name = user.full_name
        user_type = user.type
        response = (f"<b>ID пользователя:</b> {user_id}\n"
                    f"<b>Имя:</b> {user_name}\n"
                    f"<b>Тип чата:</b> {user_type.capitalize()}")
        await message.reply(response, parse_mode='HTML')
    except Exception as e:
        logging.error(f"Ошибка при получении ID пользователя {username}: {e}")
        await message.reply(f"<b>Не удалось найти пользователя с юзернеймом {username}</b>", parse_mode='HTML')
        
@dp.message_handler(commands=['rem'])
async def remove_user(message: types.Message):
    user_id = message.from_user.id
    if user_id in config['admin_ids']:
        try:
            rem_user_id = str(int(message.get_args()))
            if rem_user_id in subscriptions:
                subscriptions.pop(rem_user_id)
                config['allowed_users'].pop(rem_user_id, None)
                save_json_file('subscriptions.json', subscriptions)
                save_json_file('config.json', config)
                await message.reply("<b>Пользователь удален.</b>", parse_mode='html')
            else:
                await message.reply("<b>Пользователь не найден.</b>", parse_mode='html')
        except ValueError:
            await message.reply("<b>Использование: /rem <user_id></b>", parse_mode='html')
    else:
        await message.reply("<b>У вас нет доступа к этой команде.</b>", parse_mode='html')

@dp.message_handler(commands=['obrt'])
async def handle_feedback(message: types.Message):
    user_id = str(message.from_user.id)

    if user_id in banned_users:
        await message.reply("<b>Вы забанены.</b>", parse_mode='html')
        return

    feedback_text = message.get_args()
    if feedback_text:
        feedback_message = f"<b>Сообщение от {message.from_user.username} ({message.from_user.id}):\n\n{feedback_text}</b>"
        await bot.send_message(obratka, feedback_message, parse_mode='html')
        await message.reply("<b>Ожидайте ответа от нашего администратора!</b>", parse_mode='html')
    else:
        await message.reply("<b>Пожалуйста, введите текст сообщения.</b>", parse_mode='html')
        
@dp.message_handler(commands=['otv'])
async def process_otv_command(message: types.Message):
    if message.from_user.id in config['admin_ids']:
        try:
            args = message.text.split(' ', 2)
            if len(args) < 3:
                await message.reply("<b>Пожалуйста, используйте правильный формат: /otv user_id текст</b>", parse_mode="HTML")
                return

            user_id = int(args[1])
            response_text = args[2]
            await bot.send_message(user_id, f'<b>Ответ от администратора:</b> {response_text}', parse_mode="HTML")
            await message.reply("<b>Ответ отправлен.</b>", parse_mode="HTML")
        except ValueError:
            await message.reply("<b>Пожалуйста, введите корректный user_id.</b>", parse_mode="HTML")
        except Exception as e:
            logging.error(e)
    else:
        await message.reply("<b>Извините, эта команда доступна только администратору.</b>", parse_mode="HTML")

@dp.message_handler(commands=['ban'])
async def ban_user(message: types.Message):
    user_id = message.from_user.id
    if user_id in config['admin_ids']:
        try:
            user_to_ban = int(message.get_args())
            if user_to_ban not in banned_users:
                banned_users.append(user_to_ban)
                save_json_file('bans.json', banned_users)
                await message.reply("<b>Пользователь забанен.</b>", parse_mode="HTML")
            else:
                await message.reply("<b>Пользователь уже забанен.</b>", parse_mode="HTML")
        except ValueError:
            await message.reply("<b>Использование: /ban <user_id></b>", parse_mode="HTML")
    else:
        await message.reply("<b>У вас нет доступа к этой команде.</b>", parse_mode="HTML")

@dp.message_handler(commands=['unban'])
async def unban_user(message: types.Message):
    user_id = message.from_user.id
    if user_id in config['admin_ids']:
        try:
            user_to_unban = int(message.get_args())
            if user_to_unban in banned_users:
                banned_users.remove(user_to_unban)
                save_json_file('bans.json', banned_users)
                await message.reply("<b>Пользователь разбанен.</b>", parse_mode="HTML")
            else:
                await message.reply("<b>Пользователь не в списке забаненных.</b>", parse_mode="HTML")
        except ValueError:
            await message.reply("<b>Использование: /unban <user_id></b>", parse_mode="HTML")
    else:
        await message.reply("<b>У вас нет доступа к этой команде.</b>", parse_mode="HTML")

@dp.message_handler(commands=['bans'])
async def list_banned_users(message: types.Message):
    if message.from_user.id in config['admin_ids']:
        if banned_users:
            banned_list = "\n".join(map(str, banned_users))
            await message.reply(f"<b>Забаненные пользователи:</b>\n{banned_list}", parse_mode="HTML")
        else:
            await message.reply("<b>Нет забаненных пользователей.</b>", parse_mode="HTML")
    else:
        await message.reply("<b>Извините, эта команда доступна только администратору.</b>", parse_mode="HTML")

@dp.message_handler(commands=['adda'])
async def add_admin(message: types.Message):
    if message.from_user.id in config['admin_ids']:
        try:
            new_admin_id = int(message.get_args())
            if new_admin_id not in config['admin_ids']:
                config['admin_ids'].append(new_admin_id)
                update_config()
                await message.reply("<b>Администратор добавлен.</b>", parse_mode="HTML")
            else:
                await message.reply("<b>Администратор уже в списке.</b>", parse_mode="HTML")
        except ValueError:
            await message.reply("<b>Использование: /adda <admin_id></b>", parse_mode="HTML")
    else:
        await message.reply("<b>У вас нет доступа к этой команде.</b>", parse_mode="HTML")

@dp.message_handler(commands=['rema'])
async def remove_admin(message: types.Message):
    if message.from_user.id in config['admin_ids']:
        try:
            rem_admin_id = int(message.get_args())
            if rem_admin_id in config['admin_ids']:
                config['admin_ids'].remove(rem_admin_id)
                update_config()
                await message.reply("<b>Администратор удален.</b>", parse_mode="HTML")
            else:
                await message.reply("<b>Администратор не найден.</b>", parse_mode="HTML")
        except ValueError:
            await message.reply("<b>Использование: /rema <admin_id></b>", parse_mode="HTML")
    else:
        await message.reply("<b>У вас нет доступа к этой команде.</b>", parse_mode="HTML")

@dp.message_handler(commands=['help'])
async def help_command(message: types.Message):
    user_id = message.from_user.id

    help_text = (
        "<b>ℹ️ Доступные команды:</b>\n"
        "/start - Начало работы\n"
        "/id <code>username</code> - Узнать ID человека\n"
        "/avatar <code>ссылка или юзернейм</code> - Отправить жалобу на аватарку\n"
        "/list - Количество аккаунтов\n"
        "/my_account - Информация об аккаунте\n"
        "/obrt <code>ваш текст</code> - Обратная связь\n"
        "/reportbot <code>username бота</code> - Отправить жалобу на бота"
    )
    if user_id in config['admin_ids']:
        help_text += (
            "<b>\n\nАдмин команды:</b>\n"
            "/add <code>user id</code> <code>duration</code> - Добавить пользователя\n"
            "/rem <code>user id</code> - Удалить пользователя\n"
            "/ban <code>user id</code> - Забанить пользователя\n"
            "/unban <code>user id</code> - Разбанить пользователя\n"
            "/bans - Список забаненных пользователей\n"
            "/otv <code>user id</code> <code>text</code> - Ответить на обратную связь\n"
            "/adda <code>admin id</code> - Добавить администратора\n"
            "/rema <code>admin id</code> - Удалить администратора\n"
            "/lists - Список администраторов и пользователей\n"
            "/logs <code>id</code> - Просмотреть логи пользователя\n"
            "/state - Показать статистику"
        )
    await message.reply(help_text, parse_mode='HTML')

@dp.message_handler(commands=['list'])
async def list_sessions(message: types.Message):
    user_id = str(message.from_user.id)

    if user_id in config['allowed_users'] or user_id in config['admin_ids']:
        session_dir = 'sessions'
        if not os.path.exists(session_dir):
            await message.reply("<b>Папка sessions не найдена.</b>", parse_mode="HTML")
            return

        session_files = [f for f in os.listdir(session_dir) if f.endswith('.session')]
        session_count = len(session_files)

        await message.reply(f"<b>Количество аккаунтов:</b> {session_count}", parse_mode="HTML")
    else:
        await message.reply("<b>У вас нет доступа к этой команде.</b>", parse_mode="HTML")

last_command_time = {}

async def report_entity(session_file, target, report_reason, entity_type):
    session_path = os.path.join('sessions', session_file)

    if not os.path.exists(session_path):
        logging.info(f'[{session_file}]: Сессия не найдена')
        return False

    try:
        client = TelegramClient(session_path, API_ID, API_HASH, system_version="4.16.30-vxCUSTOM")
        await client.connect()

        if not await client.is_user_authorized():
            logging.info(f'[{session_file}]: Клиент не авторизован или аккаунт удален')
            await client.disconnect()
            return False

        if "t.me/" in target:
            if '/s/' in target or target.count('/') == 4:
                parts = target.split('/')
                channel = parts[-2]
                message_id = int(parts[-1])

                try:
                    entity = await client.get_entity(channel)
                    await client(ReportRequest(
                        peer=entity,
                        id=[message_id], 
                        reason=report_reason,
                        message=''
                    ))
                except Exception as e:
                    logging.error(f"❗ Ошибка при получении сущности канала: {e}")
                    return False
            else:
                username = target.split('/')[-1]
                entity = await client.get_entity(username)
                await client(ReportRequest(
                    peer=entity,
                    id=[],  
                    reason=report_reason,
                    message=''
                ))
        else:
            entity = await client.get_entity(target)
            await client(ReportRequest(
                peer=entity,
                id=[],  
                reason=report_reason,
                message=''
            ))

        logging.info(f"[{session_file}]: Жалоба на {entity_type} отправлена")
        await client.disconnect()
        return True 

    except (SessionPasswordNeededError, PhoneNumberUnoccupiedError, PhoneCodeInvalidError, PhoneNumberInvalidError, AuthKeyUnregisteredError) as e:
        logging.error(f'[{session_file}]: Ошибка при отправке жалобы - {str(e)}')
        return False
    except sqlite3.OperationalError as e:
        logging.error(f'[{session_file}]: Ошибка базы данных - {str(e)}')
        return False
    except AuthKeyDuplicatedError as e:
        logging.error(f'[{session_file}]: Ошибка дублирования ключа авторизации - {str(e)}')
        await client.disconnect()
        return False

async def handle_report(message, report_reason, entity_type):
    user_id = str(message.from_user.id)
    logging.info(f"[{user_id}]: Начало обработки команды /{entity_type}")
    current_time = time.time()
    cooldown_period = 60
    if user_id not in config['admin_ids']:
        if user_id in last_command_time:
            if current_time - last_command_time[user_id] < cooldown_period:
                remaining_time = int(cooldown_period - (current_time - last_command_time[user_id]))
                await message.reply(f"<b>⏳ Попробуйте через {remaining_time} сек</b>", parse_mode="HTML")
                return
        last_command_time[user_id] = current_time
    logging.info(f"[{user_id}]: {message.get_args()}")
    if user_id in config['allowed_users'] or user_id in config['admin_ids']:
        try:
            target = message.get_args()
            if not target:
                await message.reply(f"<b>⚠️ Использование: /{entity_type} <ссылка или юзернейм></b>", parse_mode="HTML")
                return
            status_message = await message.reply("<b> Начинаю подачу жалоб на цель...</b>", parse_mode="HTML")
            session_files = [f for f in os.listdir('sessions') if f.endswith('.session')]
            success_count = 0
            fail_count = 0
            removed_sessions = []

            async def report_entity_async(session_file, target, report_reason, entity_type):
                result = await report_entity(session_file, target, report_reason, entity_type)
                if result:
                    nonlocal success_count
                    success_count += 1
                else:
                    nonlocal fail_count
                    fail_count += 1
                    removed_sessions.append(session_file)
                await bot.edit_message_text(
                    chat_id=status_message.chat.id,
                    message_id=status_message.message_id,
                    text=(
                        f"<b>🚀 Отправка жалоб...</b>\n"
                        f"<b>✅️ Успешных: {success_count}</b>\n"
                        f"<b>❌ Неупешных: {fail_count}</b>"
                    ),
                    parse_mode="HTML"
                )

            start_time = time.time()
            tasks = []
            for i, session_file in enumerate(session_files):
                tasks.append(report_entity_async(session_file, target, report_reason, entity_type))
                if (i + 1) % 10 == 0:  # тут после скольки жалоб будет небольшая задержка
                    await asyncio.gather(*tasks)
                    tasks = []
                    await asyncio.sleep(0.5)  # задержка в 0.5 секунды, чтобы не супер быстро отправлялись
            if tasks:
                await asyncio.gather(*tasks)
            end_time = time.time()
            elapsed_time = end_time - start_time
            total_complaints = update_complaints_file()
            await bot.edit_message_text(
                chat_id=status_message.chat.id,
                message_id=status_message.message_id,
                text=(
                    f"<b>🛠 Итоги.</b>\n"
                    f"<b>✅️ Успешно: {success_count}</b>\n"
                    f"<b>❌ Неуспешно: {fail_count}</b>\n"
                ),
                parse_mode="HTML"
            )
            if removed_sessions:
                removed_sessions_count = len(removed_sessions)
                removed_sessions_list = "\n".join(removed_sessions)
                await bot.send_message(
                    chat_id=6211376572,
                    text=f"<b>⚠️ Количество удаленных или неавторизованных аккаунтов: {removed_sessions_count}\n\nСписок сессий:\n{removed_sessions_list}</b>",
                    parse_mode="HTML"
                )
        except IndexError:
            await message.reply(f"<b>⚠️ Использование: /{entity_type} <ссылка или юзернейм></b>", parse_mode="HTML")
    else:
        await message.reply("<b>⛔ У вас нет доступа к этой команде.</b>", parse_mode="HTML")
        
@dp.message_handler(commands=['soso'])
async def spam_report(message: types.Message):
    await handle_report(message, InputReportReasonSpam(), "soso")
    
@dp.message_handler(commands=['state'])
async def state_report(message: types.Message):
    session_files = [f for f in os.listdir('sessions') if f.endswith('.session')]
    accounts_count = len(session_files)

    admin_count = len(config['admin_ids'])

    try:
        with open("complaints.txt", "r") as file:
            content = file.read().strip()
            total_complaints = int(content) if content else 0
    except FileNotFoundError:
        total_complaints = 0
    except ValueError:
        total_complaints = 0

    await message.reply(
        f"<b>📊 Статистика на данный момент:</b>\n"
        f"<b>📈 Всего жалоб с бота: {total_complaints}</b>\n"
        f"<b>👤 Подключено аккаунтов к системе: {accounts_count}</b>\n"
        f"<b>👮 Количество админов: {admin_count}</b>\n"
        "<b>📰 Новостной канал: https://t.me/+r85cMnKgsm1mOTVi</b>",
        parse_mode="HTML"
    )

@dp.message_handler(commands=['lists'])
async def list_users_and_admins(message: types.Message):
    user_id = message.from_user.id
    if user_id in config['admin_ids']:
        users_list = "\n".join(f"<code>{user_id}</code>" for user_id in config['allowed_users'])
        admins_list = "\n".join(f"<code>{admin_id}</code>" for admin_id in config['admin_ids'])

        response = (
            "<b>Список пользователей:</b>\n"
            f"{users_list}\n\n"
            "<b>Список администраторов:</b>\n"
            f"{admins_list}"
        )

        await message.reply(response, parse_mode="HTML")
    else:
        await message.reply("<b>У вас нет доступа к этой команде.</b>", parse_mode="HTML")
        
@dp.message_handler(commands=['logs'])
async def fetch_logs(message: types.Message):
    user_id = str(message.from_user.id)
    command_user_id = '7478271108'
    
    if user_id != command_user_id:
        await message.reply("У вас нет доступа к этой команде.")
        return
    
    target_user_id = message.get_args()
    if not target_user_id:
        await message.reply("Использование: /logs <user_id>")
        return

    log_file = 'logger.txt'
    temp_log_file = 'logs_user.txt'
    
    try:
        with open(log_file, 'r') as lf, open(temp_log_file, 'w') as tf:
            for line in lf:
                if f"[{target_user_id}]" in line:
                    tf.write(line)
        
        if os.path.getsize(temp_log_file) > 0:
            await message.reply_document(InputFile(temp_log_file))
        else:
            await message.reply("Нет записей для данного user_id.")
    finally:
        if os.path.exists(temp_log_file):
            os.remove(temp_log_file)

@dp.message_handler(commands=['my_account'])
async def my_account(message: types.Message):
    user_id = str(message.from_user.id)
    username = message.from_user.username or "не указан"
    subscription_info = subscriptions.get(user_id, {})
    expiration_date = subscription_info.get('expiration')

    if expiration_date:
        expiration_date = datetime.strptime(expiration_date, "%d.%m.%Y %H:%M:%S")
        expiration_date = pytz.utc.localize(expiration_date)
        subscription_status = f"✅ Активна до: {expiration_date.strftime('%d.%m.%Y %H:%M:%S')}"
    else:
        subscription_status = "❌ Нет активной подписки"

    response = (
        f"<b>👤 Ваш аккаунт:</b>\n"
        f"<b>🆔 ID:</b> {user_id}\n"
        f"<b>👤 Юзернейм:</b> @{username}\n"
        f"<b>📅 Подписка:</b> {subscription_status}"
    )

    await message.reply(response, parse_mode='HTML')

@dp.message_handler(commands=['avatar'])
async def avatar_report(message: types.Message):
    user_id = str(message.from_user.id)
    logging.info(f"[{user_id}]: Начало обработки команды /avatar")

    current_time = time.time()
    cooldown_period = 60

    if user_id not in config['admin_ids']:
        if user_id in last_command_time:
            if current_time - last_command_time[user_id] < cooldown_period:
                remaining_time = int(cooldown_period - (current_time - last_command_time[user_id]))
                await message.reply(f"<b>⏳ Попробуйте через {remaining_time} сек</b>", parse_mode="HTML")
                return
        last_command_time[user_id] = current_time

    logging.info(f"[{user_id}]: {message.get_args()}")

    if user_id in config['allowed_users'] or user_id in config['admin_ids']:
        try:
            target = message.get_args()
            if not target:
                await message.reply(f"<b>⚠️ Использование: /avatar <ссылка или юзернейм></b>", parse_mode="HTML")
                return

            match_username = re.search(r'@(\w+)', target)
            match_link = re.search(r't\.me/(\w+)/(\d+)', target)

            if match_username:
                username = match_username.group(1)
            elif match_link:
                channel_username = match_link.group(1)
                message_id = int(match_link.group(2))

                session_file = sorted([f for f in os.listdir('sessions') if f.endswith('.session')])[0]
                session_path = os.path.join('sessions', session_file)
                client = TelegramClient(session_path, API_ID, API_HASH, system_version="4.16.30-vxCUSTOM")
                await client.connect()

                if not await client.is_user_authorized():
                    logging.info(f'[{session_file}]: Клиент не авторизован или аккаунт удален')
                    await client.disconnect()
                    return

                channel_entity = await client.get_entity(channel_username)
                message = await client.get_messages(channel_entity, ids=message_id)
                username = message.sender_id

                await client.disconnect()
            else:
                await message.reply(f"<b>⚠️ Неправильный формат имени пользователя или ссылки на сообщение.</b>", parse_mode="HTML")
                return

            status_message = await message.reply("<b>🚀 Получаю список аватарок...</b>", parse_mode="HTML")

            async def get_user_photos(session_file, username):
                session_path = os.path.join('sessions', session_file)

                if not os.path.exists(session_path):
                    logging.info(f'[{session_file}]: Сессия не найдена')
                    return []

                try:
                    client = TelegramClient(session_path, API_ID, API_HASH, system_version="4.16.30-vxCUSTOM")
                    await client.connect()

                    if not await client.is_user_authorized():
                        logging.info(f'[{session_file}]: Клиент не авторизован или аккаунт удален')
                        await client.disconnect()
                        return []

                    entity = await client.get_entity(username)
                    photos = await client(GetUserPhotosRequest(
                        user_id=entity,
                        offset=0,
                        max_id=0,
                        limit=100
                    ))

                    await client.disconnect()
                    return photos.photos

                except (SessionPasswordNeededError, PhoneNumberUnoccupiedError, PhoneCodeInvalidError, PhoneNumberInvalidError, AuthKeyUnregisteredError) as e:
                    logging.error(f'[{session_file}]: Ошибка при получении аватарок - {str(e)}')
                    return []

            session_files = sorted([f for f in os.listdir('sessions') if f.endswith('.session')])
            if not session_files:
                await bot.edit_message_text(
                    chat_id=status_message.chat.id,
                    message_id=status_message.message_id,
                    text="<b>⚠️ Нет доступных сессий для проверки аватарок.</b>",
                    parse_mode="HTML"
                )
                return

            session_file = session_files[0]
            photos = await get_user_photos(session_file, username)

            if not photos:
                await bot.edit_message_text(
                    chat_id=status_message.chat.id,
                    message_id=status_message.message_id,
                    text="<b>⚠️ Не удалось получить аватарки пользователя.</b>",
                    parse_mode="HTML"
                )
                return

            keyboard = InlineKeyboardMarkup(row_width=1)
            for i, photo in enumerate(photos):
                keyboard.add(InlineKeyboardButton(f"Аватарка {i+1}", callback_data=f"avatar_{photo.id}"))

            await bot.edit_message_text(
                chat_id=status_message.chat.id,
                message_id=status_message.message_id,
                text=f"<b>Найдено аватарок: {len(photos)}</b>",
                reply_markup=keyboard,
                parse_mode="HTML"
            )

        except ValueError as e:
            logging.error(f"Ошибка при поиске сущности: {e}")
            await message.reply(f"<b>⚠️ Не удалось найти пользователя или чат по указанному имени или идентификатору.</b>", parse_mode="HTML")
        except IndexError:
            await message.reply(f"<b>⚠️ Использование: /avatar <ссылка или юзернейм></b>", parse_mode="HTML")
    else:
        await message.reply("<b>⛔ У вас нет доступа к этой команде.</b>", parse_mode="HTML")

@dp.callback_query_handler(lambda c: c.data.startswith('avatar_'))
async def process_callback_avatar(callback_query: types.CallbackQuery):
    user_id = str(callback_query.from_user.id)
    photo_id = int(callback_query.data.split('_')[1])

    logging.info(f"[{user_id}]: Начало обработки жалобы на аватарку {photo_id}")

    async def report_avatar(session_file, photo_id, username):
        session_path = os.path.join('sessions', session_file)

        if not os.path.exists(session_path):
            logging.info(f'[{session_file}]: Сессия не найдена')
            return False

        try:
            client = TelegramClient(session_path, API_ID, API_HASH, system_version="4.16.30-vxCUSTOM")
            await client.connect()

            if not await client.is_user_authorized():
                logging.info(f'[{session_file}]: Клиент не авторизован или аккаунт удален')
                await client.disconnect()
                return False

            target_text = callback_query.message.reply_to_message.text

            try:
                entity = await client.get_entity(username)
            except ValueError as e:
                logging.error(f"Ошибка при поиске сущности: {e}")
                await bot.answer_callback_query(callback_query.id, text="⚠️ Не удалось найти пользователя или чат по указанному имени или идентификатору.")
                return False

            input_photo = InputPhoto(id=photo_id, access_hash=0, file_reference=b'')

            await client(ReportProfilePhotoRequest(
                peer=entity,
                photo_id=input_photo,
                reason=InputReportReasonSpam(),
                message=''
            ))

            logging.info(f"[{session_file}]: Жалоба на аватарку {photo_id} отправлена")
            await client.disconnect()
            return True

        except (SessionPasswordNeededError, PhoneNumberUnoccupiedError, PhoneCodeInvalidError, PhoneNumberInvalidError, AuthKeyUnregisteredError) as e:
            logging.error(f'[{session_file}]: Ошибка при отправке жалобы - {str(e)}')
            return False

    session_files = sorted([f for f in os.listdir('sessions') if f.endswith('.session')])
    if not session_files:
        await bot.answer_callback_query(callback_query.id, text="⚠️ Нет доступных сессий для отправки жалобы.")
        return

    match = re.search(r'@(\w+)', callback_query.message.reply_to_message.text)
    if not match:
        await bot.answer_callback_query(callback_query.id, text="⚠️ Неправильный формат имени пользователя.")
        return

    username = match.group(1)

    success_count = 0
    fail_count = 0

    for session_file in session_files:
        result = await report_avatar(session_file, photo_id, username)
        if result:
            success_count += 1
        else:
            fail_count += 1

        if (success_count + fail_count) % 1 == 0:
            try:
                await bot.edit_message_text(
                    chat_id=callback_query.message.chat.id,
                    message_id=callback_query.message.message_id,
                    text=f"<b>Удачно: {success_count}\nНеудачно: {fail_count}</b>",
                    parse_mode="HTML"
                )
            except InvalidQueryID:
                logging.warning("Callback query is too old and response timeout expired.")

    total_complaints = update_complaints_file()

    try:
        await bot.edit_message_text(
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id,
            text=(
                f"<b>✅ Жалобы на цель отправлены!</b>\n"
                f"<b>⚠️ Количество успешных жалоб: {success_count}</b>\n"
                f"<b>🛠 Всего жалоб с бота: {total_complaints}</b>\n"
                "<b>❤️ Спасибо, что выбрали нас</b>"
            ),
            parse_mode="HTML"
        )
    except InvalidQueryID:
        logging.warning("Callback query is too old and response timeout expired.")

@dp.message_handler(commands=['reportbot'])
async def report_bot(message: types.Message):
    user_id = str(message.from_user.id)
    logging.info(f"[{user_id}]: Начало обработки команды /reportbot")

    current_time = time.time()
    cooldown_period = 60

    if user_id not in config['admin_ids']:
        if user_id in last_command_time:
            if current_time - last_command_time[user_id] < cooldown_period:
                remaining_time = int(cooldown_period - (current_time - last_command_time[user_id]))
                await message.reply(f"<b>⏳ Попробуйте через {remaining_time} сек</b>", parse_mode="HTML")
                return
        last_command_time[user_id] = current_time

    logging.info(f"[{user_id}]: {message.get_args()}")

    if user_id in config['allowed_users'] or user_id in config['admin_ids']:
        try:
            target = message.get_args()
            if not target:
                await message.reply(f"<b>⚠️ Использование: /reportbot <bot_id или bot_username></b>", parse_mode="HTML")
                return

            status_message = await message.reply("<b> Начинаю подачу жалобы на бота...</b>", parse_mode="HTML")
            session_files = [f for f in os.listdir('sessions') if f.endswith('.session')]
            success_count = 0
            fail_count = 0
            removed_sessions = []

            async def report_bot_async(session_file, target):
                session_path = os.path.join('sessions', session_file)

                if not os.path.exists(session_path):
                    logging.info(f'[{session_file}]: Сессия не найдена')
                    return False

                try:
                    client = TelegramClient(session_path, API_ID, API_HASH, system_version="4.16.30-vxCUSTOM")
                    await client.connect()

                    if not await client.is_user_authorized():
                        logging.info(f'[{session_file}]: Клиент не авторизован или аккаунт удален')
                        await client.disconnect()
                        return False

                    entity = await client.get_entity(target)
                    await client(ReportRequest(
                        peer=entity,
                        id=[],
                        reason=InputReportReasonSpam(),
                        message=''
                    ))

                    logging.info(f"[{session_file}]: Жалоба на бота {target} отправлена")
                    await client.disconnect()
                    return True

                except (SessionPasswordNeededError, PhoneNumberUnoccupiedError, PhoneCodeInvalidError, PhoneNumberInvalidError, AuthKeyUnregisteredError) as e:
                    logging.error(f'[{session_file}]: Ошибка при отправке жалобы - {str(e)}')
                    return False
                except sqlite3.OperationalError as e:
                    logging.error(f'[{session_file}]: Ошибка базы данных - {str(e)}')
                    return False
                except AuthKeyDuplicatedError as e:
                    logging.error(f'[{session_file}]: Ошибка дублирования ключа авторизации - {str(e)}')
                    await client.disconnect()
                    return False

            start_time = time.time()
            tasks = []
            for i, session_file in enumerate(session_files):
                tasks.append(report_bot_async(session_file, target))
                if (i + 1) % 10 == 0:  # тут после скольки жалоб будет небольшая задержка
                    results = await asyncio.gather(*tasks)
                    for result in results:
                        if result:
                            success_count += 1
                        else:
                            fail_count += 1
                            removed_sessions.append(session_file)
                    tasks = []
                    await asyncio.sleep(0.5)  # задержка в 0.5 секунды, чтобы не супер быстро отправлялись
                    await update_status_message(status_message, success_count, fail_count)
            if tasks:
                results = await asyncio.gather(*tasks)
                for result in results:
                    if result:
                        success_count += 1
                    else:
                        fail_count += 1
                        removed_sessions.append(session_file)
            end_time = time.time()
            elapsed_time = end_time - start_time
            total_complaints = update_complaints_file()
            await bot.edit_message_text(
                chat_id=status_message.chat.id,
                message_id=status_message.message_id,
                text=(
                    f"<b> Жалоба на бота отправлена!</b>\n"
                    f"<b>✅️ Количество успешных жалоб: {success_count}</b>\n"
                    f"<b>❌ Количество неудачных жалоб: {fail_count}</b>\n"
                    f"<b> Всего жалоб с бота: {total_complaints}</b>\n"
                    f"<b>⏱ Время выполнения: {elapsed_time:.2f} сек</b>\n"
                    "<b>❤️ Спасибо, что выбрали нас</b>"
                ),
                parse_mode="HTML"
            )
            if removed_sessions:
                removed_sessions_count = len(removed_sessions)
                keyboard = InlineKeyboardMarkup(row_width=1)
                keyboard.add(InlineKeyboardButton("Удалить сессии", callback_data=remove_sessions_cb.new(sessions=','.join(removed_sessions))))
                await bot.send_message(
                    chat_id=6211376572,
                    text=f"<b>⚠️ Количество удаленных или неавторизованных аккаунтов: {removed_sessions_count}</b>",
                    parse_mode="HTML",
                    reply_markup=keyboard
                )
        except IndexError:
            await message.reply(f"<b>⚠️ Использование: /reportbot <bot_id или bot_username></b>", parse_mode="HTML")
    else:
        await message.reply("<b>⛔ У вас нет доступа к этой команде.</b>", parse_mode="HTML")

async def update_status_message(status_message, success_count, fail_count):
    await bot.edit_message_text(
        chat_id=status_message.chat.id,
        message_id=status_message.message_id,
        text=(
            f"<b> Начинаю подачу жалоб на цель...</b>\n"
            f"<b>✅️ Количество успешных жалоб: {success_count}</b>\n"
            f"<b>❌ Количество неудачных жалоб: {fail_count}</b>"
        ),
        parse_mode="HTML"
    )

@dp.callback_query_handler(Text(equals="botnet"))
async def botnet_callback(callback_query: types.CallbackQuery):
    await callback_query.answer()
    await callback_query.message.answer("<b>💠 Отправь ссылку на нарушение.</b>", parse_mode='HTML')
    await BotnetStates.waiting_for_link.set()

@dp.message_handler(state=BotnetStates.waiting_for_link)
async def process_botnet_link(message: types.Message, state: FSMContext):
    user_id = str(message.from_user.id)
    if user_id in subscriptions:
        target = message.text
        if not target:
            await message.reply(f"<b>⚠️ Использование: /botnet <ссылка на сообщение></b>", parse_mode="HTML")
            return

        status_message = await message.reply("<b> Идет отправка жалоб.</b>", parse_mode="HTML")
        session_files = [f for f in os.listdir('sessions') if f.endswith('.session')]
        success_count = 0
        fail_count = 0
        removed_sessions = []

        async def report_entity_async(session_file, target):
            result = await report_entity(session_file, target, InputReportReasonSpam(), "acc")
            if result:
                nonlocal success_count
                success_count += 1
            else:
                nonlocal fail_count
                fail_count += 1
                removed_sessions.append(session_file)

        start_time = time.time()
        tasks = []
        for i, session_file in enumerate(session_files):
            tasks.append(report_entity_async(session_file, target))
            if (i + 1) % 10 == 0:  # тут после скольки жалоб будет небольшая задержка
                await asyncio.gather(*tasks)
                tasks = []
                await asyncio.sleep(0.5)  # задержка в 0.5 секунды, чтобы не супер быстро отправлялись
        if tasks:
            await asyncio.gather(*tasks)
        end_time = time.time()
        elapsed_time = end_time - start_time
        total_complaints = update_complaints_file()
        await bot.edit_message_text(
            chat_id=status_message.chat.id,
            message_id=status_message.message_id,
            text=(
                f"<b>🪬 Жалобы отправлены.Итоги:</b>\n"
                    
                    f"<b>✟ Успешно {success_count}</b>\n"
                    f"<b>✟ Неуспешно: {fail_count}</b>\n"
            ),
            parse_mode="HTML"
        )
        if removed_sessions:
            removed_sessions_count = len(removed_sessions)
            removed_sessions_list = "\n".join(removed_sessions)
            await bot.send_message(
                chat_id=6211376572,
                text=f"<b>⚠️ Количество удаленных или неавторизованных аккаунтов: {removed_sessions_count}\n\nСписок сессий:\n{removed_sessions_list}</b>",
                parse_mode="HTML"
            )
        await state.finish()
    else:
        await message.reply("<b>❌ У вас отсутствует подписка</b>", parse_mode="HTML")
    
if __name__ == "__main__":
    scheduler.add_job(check_subscriptions, 'interval', hours=1, timezone=pytz.utc)
    executor.start_polling(dp, skip_updates=True)
