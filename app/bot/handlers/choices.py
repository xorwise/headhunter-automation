from aiogram import Router, types, F

from storage.sqlite_impl import SQLiteRepository

router = Router()

def setup(repo: SQLiteRepository) -> Router:
    @router.callback_query(F.data.startswith("resume:"))
    async def choose_resume(q: types.CallbackQuery):
        resume_id = q.data.removeprefix("resume:")
        f = await repo.get_filters(q.from_user.id)
        f["resume_id"] = resume_id
        await repo.set_filters(q.from_user.id, f)
        await q.answer("Резюме сохранено", show_alert=True)

    @router.callback_query(F.data.startswith("exp:"))
    async def choose_experience(q: types.CallbackQuery):
        exp_id = q.data.removeprefix("exp:")
        f = await repo.get_filters(q.from_user.id)
        f["experience"] = [exp_id]
        await repo.set_filters(q.from_user.id, f)
        await q.answer("Опыт сохранен", show_alert=True)

    return router
