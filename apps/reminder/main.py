import asyncio
import logging
import sys
from datetime import datetime

import sqlalchemy as sa
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

from pydantic import BaseModel, ConfigDict

# from .database.models import Discipline
# from .database.database import SessionLocal

from apps.parser.parser import parse


class DisciplineSchema(BaseModel):

    name: str
    groups: list
    time: str
    lecture: bool
    weekday: str
    classroom: str | None
    special_data: list | None

    model_config = ConfigDict(from_attributes=True)

async def get_disciplines(session, discipline_model):
    async with session() as db:
        disciplines_list = []
        result = await db.execute(sa.select(discipline_model))
        disciplines = result.scalars().all()
        for discipline in disciplines:
            discipline_schema = DisciplineSchema.model_validate(discipline).model_dump()

            disciplines_list.append(discipline_schema)
        return disciplines_list

async def convert_to_datetime(disciplines, cur_weekday):
    weekdays_number = {'ПОНЕДЕЛЬНИК': 0,
                       'ВТОРНИК': 1,
                       'СРЕДА': 2,
                       'ЧЕТВЕРГ': 3,
                       'ПЯТНИЦА': 4}

    for discipline in disciplines:
        discipline['weekday'] = weekdays_number[discipline['weekday']]

    return disciplines




