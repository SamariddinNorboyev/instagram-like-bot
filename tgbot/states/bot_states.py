from aiogram.fsm.state import State, StatesGroup

class BotState(StatesGroup):
    waiting_for_agreement = State()
    waiting_for_credentials = State()
    ready_for_links = State()