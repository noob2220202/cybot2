import logging
from telegram import Bot
from telegram.error import BadRequest, Forbidden

import database as db

logger = logging.getLogger(__name__)


async def run_auto_delete(bot: Bot):
    settings = await db.get_all_topic_settings()
    for chat_id, thread_id, hours in settings:
        expired = await db.get_expired_messages(chat_id, thread_id, hours)
        if not expired:
            continue

        deleted_ids = []
        for msg_id in expired:
            try:
                await bot.delete_message(chat_id=chat_id, message_id=msg_id)
                deleted_ids.append(msg_id)
            except (BadRequest, Forbidden):
                deleted_ids.append(msg_id)
            except Exception as e:
                logger.warning("메시지 삭제 실패 chat=%s msg=%s: %s", chat_id, msg_id, e)

        if deleted_ids:
            await db.delete_logged_messages(chat_id, thread_id, deleted_ids)
            logger.info("chat=%s thread=%s: %d개 메시지 삭제", chat_id, thread_id, len(deleted_ids))
