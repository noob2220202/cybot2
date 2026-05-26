import logging
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ChatMemberStatus
from telegram.error import BadRequest, Forbidden

import database as db

logger = logging.getLogger(__name__)


def get_thread_id(update: Update) -> int:
    return update.effective_message.message_thread_id or 0


async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    try:
        member = await context.bot.get_chat_member(chat_id, user_id)
        return member.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER)
    except Exception:
        return False


async def cmd_auto_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    thread_id = get_thread_id(update)
    args = context.args

    if not args:
        hours = await db.get_topic_hours(chat_id, thread_id)
        topic_label = f"토픽 {thread_id}" if thread_id else "일반 채팅"
        if hours:
            await update.message.reply_text(
                f"현재 {topic_label}의 자동삭제 설정: {hours}시간\n"
                f"해제하려면 /autodelete 0"
            )
        else:
            await update.message.reply_text(
                f"현재 {topic_label}에 자동삭제가 설정되어 있지 않습니다.\n"
                f"설정하려면 /autodelete [시간] (예: /autodelete 48)"
            )
        return

    if not await is_admin(update, context):
        await update.message.reply_text("관리자만 자동삭제를 설정할 수 있습니다.")
        return

    try:
        hours = int(args[0])
        if hours < 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("올바른 숫자를 입력하세요. 예: /autodelete 48")
        return

    topic_label = f"토픽 {thread_id}" if thread_id else "일반 채팅"

    if hours == 0:
        await db.delete_topic_setting(chat_id, thread_id)
        await update.message.reply_text(f"{topic_label}의 자동삭제를 해제했습니다.")
    else:
        await db.set_topic_hours(chat_id, thread_id, hours)
        await update.message.reply_text(
            f"{topic_label}에 자동삭제를 설정했습니다.\n"
            f"기준: {hours}시간 이상 된 메시지 자동 삭제 (5분마다 실행)"
        )


async def cmd_delete_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    thread_id = get_thread_id(update)

    if not await is_admin(update, context):
        await update.message.reply_text("관리자만 전체삭제를 실행할 수 있습니다.")
        return

    message_ids = await db.get_all_logged_messages(chat_id, thread_id)
    if not message_ids:
        await update.message.reply_text("삭제할 메시지가 없습니다.")
        return

    deleted = 0
    for msg_id in message_ids:
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=msg_id)
            deleted += 1
        except (BadRequest, Forbidden):
            pass

    await db.delete_all_logged_messages(chat_id, thread_id)

    topic_label = f"토픽 {thread_id}" if thread_id else "일반 채팅"
    await update.message.reply_text(
        f"{topic_label}에서 총 {deleted}개 메시지를 삭제했습니다."
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_message or not update.effective_chat:
        return

    chat_id = update.effective_chat.id
    thread_id = get_thread_id(update)
    message_id = update.effective_message.message_id

    hours = await db.get_topic_hours(chat_id, thread_id)
    if hours:
        await db.log_message(chat_id, thread_id, message_id)
