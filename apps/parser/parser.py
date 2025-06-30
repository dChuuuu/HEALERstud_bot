from docx_parser import DocumentParser
from tools.serializer import Subject

infile = 'file/rasp.docx'
doc = DocumentParser(infile)

disciplines = {}
WEEKDAYS = ['ПОНЕДЕЛЬНИК', 'ВТОРНИК', 'СРЕДА', 'ЧЕТВЕРГ', 'ПЯТНИЦА']
key = ''

for _type, item in doc.parse():
    for elem in item['data'][1:]:

        if elem[2] in WEEKDAYS:
            key = elem[2]
        else:
            discipline_data = Subject().serialize(_object = elem)
            if discipline_data:
                disciplines.setdefault(key, []).append(discipline_data)

