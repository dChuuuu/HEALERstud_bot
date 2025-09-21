import asyncio

from datetime import timedelta
from apps.parser.parser import disciplines


class UntilTomorrow:
    async def wait(self, current_datetime, username, diff, logger):
        logger.info(f'{username} - ждём следующего дня, {diff.total_seconds()}')
        target_datetime = (current_datetime + timedelta(days=1)).replace(hour=0, minute=0, second=0,
                                                                         microsecond=0)
        diff = target_datetime - current_datetime
        await asyncio.sleep(diff.total_seconds())


class MoreThanHour:
    async def wait(self, username, diff, discipline, user_id, bot, logger):
        logger.info(f'{username} - ждём следующий предмет, более часа {diff.total_seconds()}, {discipline}')
        await asyncio.sleep(diff.total_seconds() - 3600)
        text = 'ЛЕКЦИЯ' if discipline['lecture'] else '' + discipline['name'] + discipline['time'] + discipline.get('classroom', '')
        await bot.send_message(user_id, f'Осталось менее часа до {text}')
        await asyncio.sleep(3600)
        await bot.send_message(user_id, f'Занятие {text} началось!')


class LessThanHour:
    async def wait(self, username, diff, user_id, discipline, current_datetime, index, bot, logger):
        logger.info(f'{username} - обрабатываем предмет, до которого осталось менее часа, {diff.total_seconds()}, {discipline}')
        text = 'ЛЕКЦИЯ' if discipline['lecture'] else '' + discipline['name'] + discipline['time'] + discipline.get('classroom', '')
        await bot.send_message(user_id, f'Осталось менее часа до {text}')
        await asyncio.sleep(diff.total_seconds())
        await bot.send_message(user_id, f'Занятие {text} началось!')
        try:
            diff = disciplines[index + 1]['lesson_start_time'] - current_datetime - timedelta(hours=1)
        except KeyError:
            pass
        await asyncio.sleep(diff.total_seconds())