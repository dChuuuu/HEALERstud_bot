from aiogram.fsm.state import StatesGroup, State

class Form(StatesGroup):
    group = State()
    disciplines = State()
    id = State()
    name = State()

