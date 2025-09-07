import asyncio

from sqlalchemy import select

from apps.database.models import Discipline
from apps.database.database import SessionLocal
from datetime import datetime, timedelta

from tools.pretty import DateToDateTime
from tools.waiters import UntilTomorrow, LessThanHour, MoreThanHour

from tools.to_dict import to_dict


async def sender(user_id, state, bot, logger):
    current_weekday = datetime.today().weekday()


    weekdays_dict = {'ПОНЕДЕЛЬНИК': 0,
                     'ВТОРНИК': 1,
                     'СРЕДА': 2,
                     'ЧЕТВЕРГ': 3,
                     'ПЯТНИЦА': 4}

    while True:

        data = await state.get_data()
        username = data.get('name')
        group_number = data.get('group')
        async with SessionLocal() as db:
            stmt = select(Discipline).where(Discipline.groups.any(group_number))
            result = await db.execute(stmt)
            disciplines = result.scalars().all()
            disciplines_list = [await to_dict(d) for d in disciplines]
            await state.update_data(disciplines=disciplines_list)
            disciplines = await DateToDateTime().pretty(state, command='weekly')

        for discipline in disciplines:
            time_str = discipline['time'].split(' – ')[0]

            lesson_time = datetime.strptime(time_str, '%H.%M').time()
            discipline['lesson_start_time'] = datetime.combine(datetime.today(), lesson_time)


        todays_disciplines = [discipline for discipline in disciplines if weekdays_dict[discipline['weekday']] == current_weekday]

        for index, discipline in enumerate(todays_disciplines):
            current_datetime = datetime.now()

            diff = discipline['lesson_start_time'] - current_datetime
            if index == len(todays_disciplines) - 1:
                if diff.total_seconds() <= 3600:

                    try:
                        await LessThanHour().wait(username, diff, user_id, discipline, current_datetime, index, bot, logger)
                    except IndexError:
                        break
                else:
                    await MoreThanHour().wait(username, diff, discipline, user_id, bot, logger)

                await UntilTomorrow().wait(current_datetime, username, diff, logger)

            elif diff.total_seconds() < 0:
                logger.info(f'{username} - пропускаем сегодняшний прошедший предмет, {diff.total_seconds()}, {discipline}')
                pass

            elif diff.total_seconds() <= 3600:
                logger.info(f'{username} - обрабатываем предмет, до которого осталось менее часа, {diff.total_seconds()}, {discipline}')
                await bot.send_message(user_id, f'Остался час до {discipline}')
                if index == 0:
                    await asyncio.sleep(diff.total_seconds())
                    await bot.send_message(user_id, f'Занятие {discipline} началось!')
                else:
                    try:
                        await LessThanHour().wait(username, diff, user_id, discipline, current_datetime, index, bot, logger)
                    except IndexError:
                        break

            else:
                await MoreThanHour().wait(username, diff, discipline, user_id, bot, logger)

        if current_weekday <= 4:
            current_weekday += 1
        elif current_weekday == 5 or current_weekday == 6:
            logger.info('Ждём следующую неделю')
            current_datetime = datetime.now()
            target_datetime = (current_datetime + timedelta(days=7 - current_weekday)).replace(hour=0, minute=0, second=0)
            diff = target_datetime - current_datetime
            await asyncio.sleep(diff.total_seconds())
            current_weekday = 0