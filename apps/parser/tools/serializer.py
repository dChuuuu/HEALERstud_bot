import re

class Subject:
    # def __init__(self, name: str = None, groups: list = None, time: str = None, lecture: bool = False, classroom: str = None):
    #     self.name = name
    #     self.groups = groups
    #     self.time = time
    #     self.lecture = lecture
    #     self.classroom = None

    def serialize(self, _object):
        lecture = 'ЛЕКЦИЯ' in _object[0]
        _object[0] = _object[0].lstrip('ЛЕКЦИЯ\\n')
        if _object[2] == '':
            pass
        else:
            name = _object[2]
            if ',' in _object[0]:
                groups = _object[0].split(',')
            elif '-' in _object[0]:
                elem_list = _object[0].split('-')

                groups = [str(group) for group in range(int(elem_list[0]), int(elem_list[1]) + 1)]
            else:
                groups = [_object[0]]

            time = _object[1]
            discipline_data = {'name': name,
                               'groups': groups,
                               'time': time,
                               'lecture': lecture}
            classroom = _object[3]

            if classroom != '':
                discipline_data['classroom'] = classroom
            pattern = r'\d{2}\.\d{2}'

            if re.search(pattern, name):
                special_data = re.findall(pattern, name)
                discipline_data['special_data'] = special_data
                name = name[0:name.index(':')]
                discipline_data['name'] = name


            return discipline_data