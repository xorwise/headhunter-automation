from aiogram import Router, types, F
from auth.oauth import OAuthManager


def build_router(oauth: OAuthManager) -> Router:
    router = Router()

    @router.message(F.text.casefold() == "/connect")
    async def connect(message: types.Message):
        url = oauth.build_authorize_url(message.from_user.id)
        kb = types.InlineKeyboardMarkup(
                inline_keyboard=[
                    [types.InlineKeyboardButton(text="Авторизоваться в HH.ru", url=url)]
                    ]
                )
        await message.answer("Нажмите кнопку ниже, подтвердите права и вернитесь в чат.", reply_markup=kb)

    return router
