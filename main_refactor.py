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
from sqlalchemy import select, func, String
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
from aiogram.fsm.storage.redis import RedisStorage

import logging


#//TODO АСИНХРОННЫЙ ОБРАБОТЧИК НАПОМИНАНИЙ
#//TODO РАСПИСАНИЕ ИТОГОВЫХ
#//TODO АДМИН-ЧАСТЬ
#//TODO AI АССИСТЕНТ
#//TODO СОСТОЯНИЕ В ОБРАБОТЧИКЕ(ВКЛ/ВЫКЛ УВЕДОМЛЕНИЯ)
#//TODO ОТКЛЮЧЕНИЕ НАПОМИНАНИЙ + ТЕКУЩИЙ СТАТУС НАПОМИНАНИЙ(ВКЛЮЧЕНЫ ИЛИ НЕТ)
#//TODO РАСПИСАНИЕ ДЛЯ 4-6 КУРСОВ





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

class AdminFilter(Filter):
    def __init__(self, text: str) -> None:
        self.text = text

    async def __call__(self, message: Message) -> bool:
        return message.text == self.text

async def to_dict(obj):
    return {c.key: getattr(obj, c.key) for c in obj.__table__.columns if c.key != 'groups' and c.key != 'id' and getattr(obj, c.key) is not None}

# async def sender(user_id, state):
#     current_weekday = datetime.today().weekday()
#
#     weekdays_dict = {'ПОНЕДЕЛЬНИК': 0,
#                      'ВТОРНИК': 1,
#                      'СРЕДА': 2,
#                      'ЧЕТВЕРГ': 3,
#                      'ПЯТНИЦА': 4}
#
#     while True:
#
#         data = await state.get_data()
#         username = data.get('name')
#         group_number = data.get('group')
#         async with SessionLocal() as db:
#             stmt = select(Discipline).where(Discipline.groups.any(group_number))
#             result = await db.execute(stmt)
#             disciplines = result.scalars().all()
#             disciplines_list = [await to_dict(d) for d in disciplines]
#             await state.update_data(disciplines=disciplines_list)
#             disciplines = await DateToDateTime().pretty(state, command='weekly')
#
#         for discipline in disciplines:
#             time_str = discipline['time'].split(' – ')[0]
#
#             lesson_time = datetime.strptime(time_str, '%H.%M').time()
#             discipline['lesson_start_time'] = datetime.combine(datetime.today(), lesson_time)
#
#
#         todays_disciplines = [discipline for discipline in disciplines if weekdays_dict[discipline['weekday']] == current_weekday]
#
#         for index, discipline in enumerate(todays_disciplines):
#             current_datetime = datetime.now()
#
#             diff = discipline['lesson_start_time'] - current_datetime
#             if index == len(todays_disciplines) - 1:
#                 if diff.total_seconds() <= 3600:
#                     logger.info(f'{username} - обрабатываем предмет, до которого осталось менее часа, {diff.total_seconds()}, {discipline}')
#                     await bot.send_message(user_id, f'Остался час до {discipline}')
#
#                     try:
#                         await asyncio.sleep(diff.total_seconds())
#                         await bot.send_message(user_id, f'Занятие {discipline} началось!')
#                         diff = disciplines[index + 1]['lesson_start_time'] - current_datetime - timedelta(hours=1)
#                         await asyncio.sleep(diff.total_seconds())
#                     except IndexError:
#                         break
#                 else:
#                     logger.info(f'{username} - ждём следующий предмет, {diff.total_seconds()}, {discipline}')
#                     await asyncio.sleep(diff.total_seconds() - 3600)
#                     await bot.send_message(user_id, f'Остался час до {discipline}')
#                     await asyncio.sleep(3600)
#                     await bot.send_message(user_id, f'Занятие {discipline} началось!')
#                 target_datetime = (current_datetime + timedelta(days=1)).replace(hour=0, minute=0, second=0,
#                                                                                  microsecond=0)
#                 diff = target_datetime - current_datetime
#                 logger.info(f'{username} - ждём следующего дня, {diff.total_seconds()}')
#                 await asyncio.sleep(diff.total_seconds())
#
#             elif diff.total_seconds() < 0:
#                 logger.info(f'{username} - пропускаем сегодняшний прошедший предмет, {diff.total_seconds()}, {discipline}')
#                 pass
#
#             elif diff.total_seconds() <= 3600:
#                 logger.info(f'{username} - обрабатываем предмет, до которого осталось менее часа, {diff.total_seconds()}, {discipline}')
#                 await bot.send_message(user_id, f'Остался час до {discipline}')
#                 if index == 0:
#                     await asyncio.sleep(diff.total_seconds())
#                     await bot.send_message(user_id, f'Занятие {discipline} началось!')
#                 else:
#                     try:
#                         await asyncio.sleep(diff.total_seconds())
#                         await bot.send_message(user_id, f'Занятие {discipline} началось!')
#                         diff = disciplines[index + 1]['lesson_start_time'] - current_datetime - timedelta(hours=1)
#                         await asyncio.sleep(diff.total_seconds())
#                     except IndexError:
#                         break
#
#             else:
#                 logger.info(f'{username} - ждём следующий предмет, {diff.total_seconds()}, {discipline}')
#                 await asyncio.sleep(diff.total_seconds() - 3600)
#                 await bot.send_message(user_id, f'Остался час до {discipline}')
#                 await asyncio.sleep(3600)
#                 await bot.send_message(user_id, f'Занятие {discipline} началось!')
#
#         if current_weekday <= 4:
#             current_weekday += 1
#         elif current_weekday == 5 or current_weekday == 6:
#             current_datetime = datetime.now()
#             target_datetime = (current_datetime + timedelta(days=7 - current_weekday)).replace(hour=0, minute=0, second=0)
#             diff = target_datetime - current_datetime
#             await asyncio.sleep(diff.total_seconds())
#             current_weekday = 0


async def start_logic(state: FSMContext):
    data = await state.get_data()
    name = data.get('name')
    id = data.get('id')

    await bot.send_message(chat_id=id, text=f'Привет, {html.bold(name)}!'
                         f' Я бот, который поможет тебе с расписанием занятий.'
                         f' На данный момент я нахожусь в разработке и готов работать только со студентами ВГМУ 3 курса факультета "Лечебное дело".'
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

        await callback.message.answer(answer, reply_markup=keyboard)

    elif callback.data == 'return_back':
        await start_logic(state)

    elif callback.data == 'notifications':
        disciplines = await DateToDateTime().pretty(state, command='weekly')

        for discipline in disciplines:
            time_str = discipline['time'].split(' – ')[0]

            lesson_time = datetime.strptime(time_str, '%H.%M').time()
            discipline['lesson_start_time'] = datetime.combine(datetime.today(), lesson_time)

        user_id = callback.from_user.id
        await sender(user_id, state)
        answer = MessageText().pretty(disciplines_list=disciplines, ignorable_keys=['current_week', 'weekday', 'lesson_start_time'])
        await callback.message.answer(answer, reply_markup=keyboard)


@dp.message()
async def warn_text(message: Message):
    await message.answer("Пожалуйста, используйте кнопки для взаимодействия.")


@dp.message(AdminFilter('admin'))
async def admin(message: Message) -> None:
    disciplines = await parse()
    async with SessionLocal() as db:
        for weekday in disciplines:
            for discipline in disciplines[weekday]:
                discipline['weekday'] = weekday
                data = Discipline(**discipline)
                db.add(data)
                await db.commit()
    return disciplines


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