from aiogram.fsm.state import State, StatesGroup

class BotState(StatesGroup):
    waiting_for_agreement = State()
    waiting_for_credentials = State()
    waiting_for_username = State()
    waiting_for_2fa_code = State()
    ready_for_links = State()