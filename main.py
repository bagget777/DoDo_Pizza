
import logging
import sqlite3
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Command
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from datetime import datetime
from config import token

bot = Bot(token)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

conn = sqlite3.connect('dodo_pizza_bot.db')
cursor = conn.cursor()

cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        first_name TEXT,
        last_name TEXT,
        username TEXT,
        id_user INTEGER,
        phone_number TEXT
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS address (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        id_user INTEGER,
        address_longitude REAL,
        address_latitude REAL
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        address_destination TEXT,
        date_time_order TEXT
    )
''')

logging.basicConfig(level=logging.INFO)


class Form(StatesGroup):
    phone_number = State()
    location = State()
    order = State()


@dp.message_handler(Command('start'))
async def start_command(message: types.Message):

    cursor.execute('SELECT * FROM users WHERE id_user = ?', (message.from_user.id,))
    user = cursor.fetchone()

    if user:
        await message.answer(f"Здравствуйте, {message.from_user.full_name}!")
    else:
        cursor.execute('''
            INSERT INTO users (first_name, last_name, username, id_user)
            VALUES (?, ?, ?, ?)
        ''', (message.from_user.first_name, message.from_user.last_name, message.from_user.username, message.from_user.id))
        conn.commit()

        await message.answer(f"Здравствуйте, {message.from_user.full_name}! Вы были добавлены в базу данных.")
    

    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton('Отправить номер', callback_data='phone_number'),
        InlineKeyboardButton('Отправить локацию', callback_data='location'),
        InlineKeyboardButton('Заказать еду', callback_data='order')
    )

    await message.answer("Выберите действие:", reply_markup=keyboard)


@dp.callback_query_handler(lambda c: c.data == 'phone_number', state='*')
async def process_phone_number(callback_query: types.CallbackQuery, state: FSMContext):
    await bot.answer_callback_query(callback_query.id)

    await Form.phone_number.set()
    await bot.send_message(callback_query.from_user.id, "Отправьте свой номер телефона",
                           reply_markup=types.ReplyKeyboardRemove())

import re



@dp.message_handler(state=Form.phone_number)
async def process_phone_number_input(message: types.Message, state: FSMContext):
    phone_number = re.sub(r'\D', '', message.text) 
    if not phone_number:
        await message.answer("Вы ввели некорректный номер телефона. Попробуйте еще раз.")
        return

    async with state.proxy() as data:
        data['phone_number'] = phone_number

    cursor.execute('UPDATE users SET phone_number = ? WHERE id_user = ?', (phone_number, message.from_user.id))
    conn.commit()

    await message.answer("Спасибо, ваш номер телефона был сохранен.")
    await state.finish()



@dp.callback_query_handler(lambda c: c.data == 'location', state='*')
async def process_location(callback_query: types.CallbackQuery, state: FSMContext):
    await bot.answer_callback_query(callback_query.id)

    await Form.location.set()
    await bot.send_message(callback_query.from_user.id, "Отправьте свою локацию", reply_markup=types.ReplyKeyboardRemove())


@dp.message_handler(content_types=types.ContentTypes.LOCATION, state=Form.location)
async def process_location_input(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['latitude'] = message.location.latitude
        data['longitude'] = message.location.longitude

        cursor.execute('INSERT INTO address (id_user, address_longitude, address_latitude) VALUES (?, ?, ?)',
                   (message.from_user.id, message.location.longitude, message.location.latitude))
    conn.commit()

    await message.answer("Спасибо, ваша локация была сохранена.")
    await state.finish()

@dp.callback_query_handler(lambda c: c.data == 'order', state='*')
async def process_order(callback_query: types.CallbackQuery, state: FSMContext):
    await bot.answer_callback_query(callback_query.id)

    await Form.order.set()
    await bot.send_message(callback_query.from_user.id, "Введите ваш заказ")


@dp.message_handler(state=Form.order)
async def process_order_input(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['order'] = message.text

    cursor.execute('INSERT INTO orders (title, address_destination, date_time_order) VALUES (?, ?, ?)',
                   (message.text, 'ADJUST_DESTINATION_ADDRESS', datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()

    await message.answer("Ваш заказ был принят.")
    await state.finish()


async def on_startup(dp):
    await bot.send_message(chat_id=5016205223, text="Бот запущен")


@dp.message_handler(commands=['start'])
async def not_found(message: types.Message):
    await message.reply("Я вас не понял, введите /help")


if __name__ == '__main__':
    import asyncio

    loop = asyncio.get_event_loop()
    loop.create_task(on_startup(dp))

    try:
        loop.run_until_complete(dp.start_polling())
    except KeyboardInterrupt:
        pass
    finally:
        loop.run_until_complete(dp.storage.close())
        loop.run_until_complete(dp.storage.wait_closed())
        loop.run_until_complete(bot.session.close())
        loop.close()
        conn.close()

