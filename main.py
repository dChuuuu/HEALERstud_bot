import asyncio
import logging
import sys
from os import getenv


from aiogram import Bot, Dispatcher, html
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, StateFilter
from aiogram.filters import Filter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from alembic.command import current
from sqlalchemy import select, func, String, text
from sqlalchemy.ext.asyncio import AsyncSession

from pydantic import BaseModel
from sqlalchemy.orm import Session

from apps.database.models import Discipline
from apps.database.database import SessionLocal
from datetime import datetime, timedelta
from apps.parser.parser import parse, disciplines
from apps.reminder.main import get_disciplines, convert_to_datetime
from forms import Form
from tools.pretty import MessageText, DateToDateTime
from tools.sender import sender
from aiogram.fsm.storage.redis import RedisStorage
import redis.asyncio as redis

import logging

#//TODO ПОЧИНИТЬ NONE
#//TODO СОХРАНЕНИЕ СОСТОЯНИЯ НАПОМИНАНИЙ ПОСЛЕ ПЕРЕЗАГРУЗКИ БОТА
#//TODO АСИНХРОННЫЙ ОБРАБОТЧИК НАПОМИНАНИЙ
#//TODO РАСПИСАНИЕ ДЛЯ 4-6 КУРСОВ
#//TODO РАСПИСАНИЕ ИТОГОВЫХ
#//TODO АДМИН-ЧАСТЬ
#//TODO AI АССИСТЕНТ


logger = logging.getLogger('main')
logger.setLevel(logging.INFO)

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)



keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Получить расписание на неделю", callback_data="week_schedule")],
        [InlineKeyboardButton(text="Получить расписание на сегодня", callback_data="daily_schedule")],
        [InlineKeyboardButton(text="Получить расписание на следующую неделю", callback_data="next_week_schedule")],
        [InlineKeyboardButton(text="Получить общее расписание", callback_data='common_schedule')],
        [InlineKeyboardButton(text="В начало(изменить группу)", callback_data='return_back')],
        [InlineKeyboardButton(text="Включить/выключить напоминания", callback_data='notifications')]
    ])

try:
    from env import TOKEN
except ImportError:
    raise BaseException('Не указан токен в env.py')

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

storage = RedisStorage.from_url("redis://localhost:6379/0")
dp = Dispatcher(storage=storage)

r = redis.Redis.from_url("redis://localhost:6379/0")

class AdminFilter(Filter):
    def __init__(self, text: str) -> None:
        self.text = text

    async def __call__(self, message: Message) -> bool:
        return message.text == self.text

async def to_dict(obj):
    return {c.key: getattr(obj, c.key) for c in obj.__table__.columns if c.key != 'groups' and c.key != 'id' and getattr(obj, c.key) is not None}

async def start_logic(state: FSMContext):
    data = await state.get_data()
    name = data.get('name')
    id = data.get('id')

    await bot.send_message(chat_id=id, text=f'Привет, {html.bold(name)}!'
                         f' Я бот, который поможет тебе с расписанием занятий.'
                         f' На данный момент я нахожусь в разработке и готов работать только со студентами ВГМУ:\n'
                         f' - 3 курс факультета "Лечебное дело".\n'
                         f' Пожалуйста, укажи свою группу, чтобы получить расписание.', parse_mode='HTML')


    await state.set_state(Form.group)


@dp.message(CommandStart())
async def command_start_handler(message: Message, state: FSMContext) -> None:
    await state.update_data(name=message.from_user.full_name, id=message.from_user.id)
    await start_logic(state)


@dp.message(StateFilter(Form.group))
async def group_number_handler(message: Message, state: FSMContext):
    try:
        int(message.text)
    except ValueError:
        await message.answer("Номер группы - должно быть число")
        return None

    async with SessionLocal() as db:
        group_number = message.text
        await state.update_data(group=group_number)
        stmt = select(Discipline).where(Discipline.groups.any(group_number))
        result = await db.execute(stmt)
        disciplines = result.scalars().all()
        if len(disciplines) == 0:
            await message.answer('Неверно указана группа или занятий не найдено')
        disciplines_list = [await to_dict(d) for d in disciplines]
        answer = MessageText().pretty(disciplines_list=disciplines_list, ignorable_keys=['weekday'])
        print(answer)
        await message.answer(answer, reply_markup=keyboard)
        await state.update_data(disciplines=disciplines_list)
        await state.set_state(Form.disciplines)


@dp.callback_query(StateFilter(Form.disciplines))
async def callback_handler(callback: CallbackQuery, state: FSMContext):


    if callback.data == 'week_schedule':

        disciplines = await DateToDateTime().pretty(state, command='weekly')

        answer = MessageText().pretty(disciplines_list=disciplines, ignorable_keys=['current_week', 'weekday'])

        await callback.message.answer(answer, reply_markup=keyboard)

    elif callback.data == 'daily_schedule':

        disciplines = await DateToDateTime().pretty(state, command='daily')
        answer = MessageText().pretty(disciplines_list=disciplines, ignorable_keys=['current_week', 'weekday'])

        await callback.message.answer(answer, reply_markup=keyboard)

    elif callback.data == 'next_week_schedule':

        disciplines = await DateToDateTime().pretty(state, command='next_week')
        answer = MessageText().pretty(disciplines_list=disciplines, ignorable_keys=['current_week', 'weekday'])
        await callback.message.answer(answer, reply_markup=keyboard)

    elif callback.data == 'common_schedule':
        data = await state.get_data()
        disciplines_list = data.get('disciplines')
        answer = MessageText().pretty(disciplines_list=disciplines_list, ignorable_keys=['current_week', 'weekday'])
        print(answer)
        await callback.message.answer(answer, reply_markup=keyboard)

    elif callback.data == 'return_back':
        await start_logic(state)

    elif callback.data == 'notifications':
        data = await state.get_data()
        user_id = data.get('id')
        tasks = asyncio.all_tasks()
        outdated_task = None

        for task in tasks:
            if task.get_name() == 'Sender':
                outdated_task = task
                break

        if outdated_task:
            outdated_task.cancel()

            await bot.send_message(chat_id=user_id, text='Уведомления выключены!', reply_markup=keyboard)
            tasks = asyncio.all_tasks()
            print(tasks)
            return None

        disciplines = await DateToDateTime().pretty(state, command='weekly')

        for discipline in disciplines:
            time_str = discipline['time'].split(' – ')[0]

            lesson_time = datetime.strptime(time_str, '%H.%M').time()
            discipline['lesson_start_time'] = datetime.combine(datetime.today(), lesson_time)

        user_id = callback.from_user.id
        await bot.send_message(chat_id=user_id, text='Уведомления включены!', reply_markup=keyboard)
        await asyncio.create_task(sender(user_id, state, bot, logger), name='Sender')


@dp.message(AdminFilter('admin'))
async def admin() -> None:
    disciplines = await parse()
    async with SessionLocal() as db:

        await r.flushdb()
        stmt = "TRUNCATE TABLE disciplines RESTART IDENTITY;"
        await db.execute(text(stmt))

        for weekday in disciplines:
            for discipline in disciplines[weekday]:
                discipline['weekday'] = weekday
                data = Discipline(**discipline)
                db.add(data)
                await db.commit()

    return disciplines



@dp.message()
async def warn_text(message: Message):
    await message.answer("Пожалуйста, используйте кнопки для взаимодействия.")





@dp.message()
async def root(message: Message) -> None:
    """
    Handler will forward receive a message back to the sender

    By default, message handler will handle all message types (like a text, photo, sticker etc.)
    """
    await message.answer('Неверная команда!')


async def main() -> None:
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())