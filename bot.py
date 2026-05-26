import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram.ext import Application, CommandHandler, MessageHandler, filters

import config
import database as db
from handlers import cmd_auto_delete, cmd_delete_all, handle_message
from scheduler import run_auto_delete

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def post_init(application: Application):
    await db.init_db()

    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        run_auto_delete,
        trigger="interval",
        minutes=config.CHECK_INTERVAL_MINUTES,
        args=[application.bot],
        id="auto_delete",
        replace_existing=True,
    )
    scheduler.start()
    application.bot_data["scheduler"] = scheduler
    logger.info("스케줄러 시작 (간격: %d분)", config.CHECK_INTERVAL_MINUTES)


async def post_shutdown(application: Application):
    scheduler = application.bot_data.get("scheduler")
    if scheduler and scheduler.running:
        scheduler.shutdown(wait=False)


def main():
    app = (
        Application.builder()
        .token(config.BOT_TOKEN)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )

    app.add_handler(CommandHandler("자동삭제", cmd_auto_delete))
    app.add_handler(CommandHandler("전체삭제", cmd_delete_all))
    app.add_handler(
        MessageHandler(filters.ALL & ~filters.COMMAND, handle_message)
    )

    logger.info("봇 시작")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
