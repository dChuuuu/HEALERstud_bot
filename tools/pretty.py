from datetime import datetime, timedelta

from aiogram.fsm.context import FSMContext


class MessageText:
    def pretty(self, disciplines_list: list = None, ignorable_keys: list = None):
        emojis = ['&#128557', '&#128548', '&#128529', '&#128521', '&#128527']
        emoji_index = 0
        texts = {}
        answer = ''
        for d in disciplines_list:
            texts.setdefault(d['weekday'], []).append({key: value for key, value in d.items() if key not in ignorable_keys})

        for weekday in texts:

            answer += f'{emojis[emoji_index]}   ' + weekday + '\n\n'
            for discipline in texts[weekday]:
                try:
                    discipline['special_data'] = ', '.join(discipline['special_data'])
                except KeyError:
                    pass
                if discipline['lecture'] is True:
                    answer += 'ЛЕКЦИЯ\n'
                del discipline['lecture']
                #print(answer)
                answer += str(' '.join([value for value in discipline.values()])) + '\n\n'
            emoji_index += 1
        answer += '\nГотово! Сообщи, если нужно ещё что-нибудь'

        return answer


class DateToDateTime:
    async def pretty(self, state: FSMContext, command: str = None):
        weekdays_dict = {'ПОНЕДЕЛЬНИК': 0,
                         'ВТОРНИК': 1,
                         'СРЕДА': 2,
                         'ЧЕТВЕРГ': 3,
                         'ПЯТНИЦА': 4}
        data = await state.get_data()
        disciplines = data.get('disciplines')

        disciplines_answer = []
        # cur_weekday = 1
        # cur_date = datetime(year=2025, month=3, day=3)
        cur_weekday = datetime.today().weekday()

        if command == 'next_week':
            cur_date = datetime.today().date() + timedelta(7)
        else:
            cur_date = datetime.today().date()

        start_of_week = cur_date - timedelta(days=cur_weekday)
        dates = []

        for i in range(0, 5):
            dates.append(start_of_week + timedelta(i))

        for discipline in disciplines:

            if discipline.get('special_data'):

                if any(map(lambda day: datetime.strptime(f"{day}.{datetime.today().year}",
                                                         "%d.%m.%Y").date() in dates, discipline['special_data'])) is True:

                    discipline['current_week'] = True
                else:
                    discipline['current_week'] = False

            else:
                discipline['current_week'] = True



        if command == 'weekly' or command == 'next_week':
            for discipline in disciplines:
                if discipline['current_week'] is True:
                    disciplines_answer.append(discipline)

        elif command == 'daily':
            for discipline in disciplines:
                if discipline['current_week'] is True and weekdays_dict[discipline['weekday']] == cur_weekday:
                    disciplines_answer.append(discipline)

        else:
            raise BaseException('Неверный тип команды')

        return disciplines_answer
