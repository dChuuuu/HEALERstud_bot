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
from aiogram.types import Message
from sqlalchemy import select, func, String
from sqlalchemy.ext.asyncio import AsyncSession

from pydantic import BaseModel

from apps.database.models import Discipline
from apps.database.database import SessionLocal

from apps.parser.parser import parse

try:
    from env import TOKEN
except ImportError:
    raise BaseException('Не указан токен в env.py')

# All handlers should be attached to the Router (or Dispatcher)
#//TODO ГДЕ ФЛАГ ЛЕКЦИЙ?
dp = Dispatcher()


class Form(StatesGroup):
    group = State()


class AdminFilter(Filter):
    def __init__(self, text: str) -> None:
        self.text = text

    async def __call__(self, message: Message) -> bool:
        return message.text == self.text


async def to_dict(obj):
    return {c.key: getattr(obj, c.key) for c in obj.__table__.columns if c.key != 'groups' and c.key != 'id' and getattr(obj, c.key) is not None}


# class Discipline(Base):
#     __tablename__ = 'disciplines'
#
#     id = Column(Integernullable=False, primary_key=True, autoincrement=True)
#     name = Column(String, nullable=False, primary_key=True)
#     groups = Column(ARRAY(String), nullable=False)
#     time = Column(String, nullable=False)
#     lecture = Column(Boolean, nullable=False, default='False'),
#     classroom = Column(String, nullable=True)
#     special_data = Column(ARRAY(String), nullable=True)


@dp.message(CommandStart())
async def command_start_handler(message: Message, state: FSMContext) -> None:
    """
    This handler receives messages with `/start` command
    """
    # Most event objects have aliases for API methods that can be called in events' context
    # For example if you want to answer to incoming message you can use `message.answer(...)` alias
    # and the target chat will be passed to :ref:`aiogram.methods.send_message.SendMessage`
    # method automatically or call API method directly via
    # Bot instance: `bot.send_message(chat_id=message.chat.id, ...)`
    await message.answer(f'Привет, {html.bold(message.from_user.full_name)}!'
                         f' Я бот, который поможет тебе с расписанием занятий.'
                         f' На данный момент я нахожусь в разработке и готов работать только со студентами ВГМУ факультета "Лечебное дело".'
                         f' Пожалуйста, укажи свою группу, чтобы получить расписание.')

    await state.set_state(Form.group)


@dp.message(StateFilter(Form.group))
async def group_number_handler(message: Message, state: FSMContext) -> None:
    try:
        int(message.text)
    except ValueError:
        await message.answer("Номер группы - должно быть число")
    # finally:
    #     await state.clear()
    async with SessionLocal() as db:
        group_number = message.text
        stmt = select(Discipline).where(Discipline.groups.any(group_number))
        result = await db.execute(stmt)
        disciplines = result.scalars().all()
        if len(disciplines) == 0:
            await message.answer('Неверно указана группа или занятий не найдено')
        disciplines_list = [await to_dict(d) for d in disciplines]

        texts = {}
        answer = ''
        for d in disciplines_list:
            texts.setdefault(d['weekday'], []).append({key: value for key, value in d.items() if key != 'weekday'})

        for weekday in texts:
            answer += weekday + '\n\n'
            for discipline in texts[weekday]:
                try:
                    discipline['special_data'] = ', '.join(discipline['special_data'])
                except KeyError:
                    pass
                if discipline['lecture'] is True:
                    answer += 'ЛЕКЦИЯ\n'
                del discipline['lecture']
                answer += str(' '.join([value for value in discipline.values()])) + '\n\n'


        await message.answer(answer)


# @dp.message(AdminFilter('admin'))
# async def admin(message: Message) -> None:
#     disciplines = await parse()
#     async with SessionLocal() as db:
#         for weekday in disciplines:
#             for discipline in disciplines[weekday]:
#                 discipline['weekday'] = weekday
#                 data = Discipline(**discipline)
#                 db.add(data)
#                 await db.commit()
#     return disciplines


@dp.message()
async def root(message: Message) -> None:
    """
    Handler will forward receive a message back to the sender

    By default, message handler will handle all message types (like a text, photo, sticker etc.)
    """
    await message.answer('Неверная команда!')

async def main() -> None:
    # Initialize Bot instance with default bot properties which will be passed to all API calls
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

    # And the run events dispatching
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())