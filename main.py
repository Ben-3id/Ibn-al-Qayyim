from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ConversationHandler, MessageHandler, filters
from config import BOT_TOKEN
import handlers
import database as db
import logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

from keep_alive import keep_alive

def main():
    if not BOT_TOKEN:
        print("Error: BOT_TOKEN not found. Please set it in .env or config.py")
        return

    # Initialize Database
    db.init_db()
    print("تم تهيئة قاعدة البيانات.")

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Conversation Handler for Adding Links
    add_link_conv = ConversationHandler(
        entry_points=[CommandHandler("addlink", handlers.add_link_start)],
        states={
            handlers.TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex("^❌ إلغاء$"), handlers.receive_title)],
            handlers.CATEGORY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex("^❌ إلغاء$"), handlers.receive_category),
                CallbackQueryHandler(handlers.receive_category_callback, pattern="^sel_cat_")
            ],
            handlers.DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex("^❌ إلغاء$"), handlers.receive_description)],
            handlers.VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex("^❌ إلغاء$"), handlers.receive_value_link)],
        },
        fallbacks=[
            CommandHandler("cancel", handlers.cancel),
            MessageHandler(filters.Regex("^❌ إلغاء$"), handlers.cancel),
            CallbackQueryHandler(handlers.cancel, pattern="^cancel_conv")
        ]
    )

    # Conversation Handler for Adding Files
    add_file_conv = ConversationHandler(
        entry_points=[CommandHandler("addfile", handlers.add_file_start)],
        states={
            handlers.TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex("^❌ إلغاء$"), handlers.receive_title)],
            handlers.CATEGORY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex("^❌ إلغاء$"), handlers.receive_category),
                CallbackQueryHandler(handlers.receive_category_callback, pattern="^sel_cat_")
            ],
            handlers.DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex("^❌ إلغاء$"), handlers.receive_description)],
            handlers.VALUE: [MessageHandler(filters.ALL & ~filters.COMMAND & ~filters.Regex("^❌ إلغاء$"), handlers.receive_value_file)],
        },
        fallbacks=[
            CommandHandler("cancel", handlers.cancel),
            MessageHandler(filters.Regex("^❌ إلغاء$"), handlers.cancel),
            CallbackQueryHandler(handlers.cancel, pattern="^cancel_conv")
        ]
    )

    # Conversation Handler for Adding Categories
    add_category_conv = ConversationHandler(
        entry_points=[CommandHandler("addcategory", handlers.add_category_start)],
        states={
            handlers.NEW_CATEGORY_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex("^❌ إلغاء$"), handlers.receive_new_category_name)],
            handlers.NEW_CATEGORY_PARENT: [MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex("^❌ إلغاء$"), handlers.receive_new_category_parent)],
        },
        fallbacks=[
            CommandHandler("cancel", handlers.cancel),
            MessageHandler(filters.Regex("^❌ إلغاء$"), handlers.cancel),
            CallbackQueryHandler(handlers.cancel, pattern="^cancel_conv")
        ]
    )

    # Conversation Handler for Editing Help Text
    edit_help_conv = ConversationHandler(
        entry_points=[CommandHandler("edithelp", handlers.edit_help_start)],
        states={
            handlers.EDIT_HELP_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex("^❌ إلغاء$"), handlers.receive_help_text)],
        },
        fallbacks=[
            CommandHandler("cancel", handlers.cancel),
            MessageHandler(filters.Regex("^❌ إلغاء$"), handlers.cancel),
            CallbackQueryHandler(handlers.cancel, pattern="^cancel_conv")
        ]
    )

    # Conversation Handler for Add Series
    add_series_conv = ConversationHandler(
        entry_points=[CommandHandler("addseries", handlers.add_series_start)],
        states={
            handlers.ADD_SERIES_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex("^❌ إلغاء$"), handlers.receive_series_name)],
            handlers.ADD_SERIES_CATEGORY: [
                CallbackQueryHandler(handlers.receive_series_category_callback, pattern="^ser_(nav|sel)_"),
                MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex("^❌ إلغاء$"), handlers.receive_series_category_text)
            ],
            handlers.ADD_SERIES_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex("^❌ إلغاء$"), handlers.receive_series_description)],
        },
        fallbacks=[
            CommandHandler("cancel", handlers.cancel),
            MessageHandler(filters.Regex("^❌ إلغاء$"), handlers.cancel),
            CallbackQueryHandler(handlers.cancel, pattern="^cancel_conv")
        ]
    )

    # Conversation Handler for Add to Series
    add_to_series_conv = ConversationHandler(
        entry_points=[CommandHandler("addtoseries", handlers.add_to_series_start)],
        states={
            handlers.SERIES_ITEM_SERIES: [CallbackQueryHandler(handlers.receive_series_for_item, pattern="^add_to_")],
            handlers.SERIES_ITEM_NUMBER: [MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex("^❌ إلغاء$"), handlers.receive_item_number)],
            handlers.SERIES_ITEM_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex("^❌ إلغاء$"), handlers.receive_item_title)],
            handlers.SERIES_ITEM_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex("^❌ إلغاء$"), handlers.receive_item_description)],
            handlers.SERIES_ITEM_VALUE: [MessageHandler(filters.ALL & ~filters.COMMAND & ~filters.Regex("^❌ إلغاء$"), handlers.receive_item_value)],
        },
        fallbacks=[
            CommandHandler("cancel", handlers.cancel),
            MessageHandler(filters.Regex("^❌ إلغاء$"), handlers.cancel),
            CallbackQueryHandler(handlers.cancel, pattern="^cancel_conv")
        ]
    )

    # Conversation Handler for Move Content
    move_conv = ConversationHandler(
        entry_points=[CommandHandler("move", handlers.move_start)],
        states={
            handlers.MOVE_TYPE: [CallbackQueryHandler(handlers.receive_move_type, pattern="^move_type_")],
            handlers.MOVE_ITEM_SELECT: [CallbackQueryHandler(handlers.receive_move_item_select, pattern="^mfind_(nav|sel)_")],
            handlers.MOVE_TARGET_CAT: [CallbackQueryHandler(handlers.receive_move_target_cat_callback, pattern="^ser_(nav|sel)_")],
        },
        fallbacks=[
            CommandHandler("cancel", handlers.cancel),
            MessageHandler(filters.Regex("^❌ إلغاء$"), handlers.cancel),
            CallbackQueryHandler(handlers.cancel, pattern="^cancel_conv")
        ]
    )

    # Conversation Handler for Rename Content
    rename_conv = ConversationHandler(
        entry_points=[CommandHandler("rename", handlers.rename_start)],
        states={
            handlers.RENAME_TYPE: [CallbackQueryHandler(handlers.receive_rename_type, pattern="^rename_type_")],
            handlers.RENAME_ITEM_SELECT: [CallbackQueryHandler(handlers.receive_rename_item_select, pattern="^rfind_(nav|sel|pickser|selsitem)_")],
            handlers.RENAME_NEW_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex("^❌ إلغاء$"), handlers.receive_rename_new_name)],
        },
        fallbacks=[
            CommandHandler("cancel", handlers.cancel),
            MessageHandler(filters.Regex("^❌ إلغاء$"), handlers.cancel),
            CallbackQueryHandler(handlers.cancel, pattern="^cancel_conv")
        ]
    )

    app.add_handler(CommandHandler("start", handlers.start))
    app.add_handler(CommandHandler("help", handlers.help_command))
    app.add_handler(CommandHandler("categories", handlers.categories_command))
    app.add_handler(CommandHandler("search", handlers.search_command))
    app.add_handler(CommandHandler("delete", handlers.delete_command))
    app.add_handler(CommandHandler("deletecategory", handlers.delete_category_command))
    app.add_handler(CommandHandler("deleteseries", handlers.delete_series_command))
    app.add_handler(CommandHandler("dbdownload", handlers.dbdownload))
    
    app.add_handler(add_link_conv)
    app.add_handler(add_file_conv)
    app.add_handler(add_category_conv)
    app.add_handler(edit_help_conv)
    app.add_handler(add_series_conv)
    app.add_handler(add_to_series_conv)
    app.add_handler(move_conv)
    app.add_handler(rename_conv)
    
    # Generic Callback Query Handlers
    app.add_handler(CallbackQueryHandler(handlers.category_callback, pattern="^cat_|back_cats"))
    app.add_handler(CallbackQueryHandler(handlers.resource_callback, pattern="^res_"))
    
    # Deletion confirmations
    app.add_handler(CallbackQueryHandler(handlers.confirm_delete_category, pattern="^confirm_del_cat_"))
    app.add_handler(CallbackQueryHandler(handlers.confirm_delete_resource, pattern="^confirm_del_res_"))
    app.add_handler(CallbackQueryHandler(handlers.confirm_delete_series, pattern="^confirm_del_ser_"))
    app.add_handler(CallbackQueryHandler(handlers.cancel_delete, pattern="^cancel_del"))

    # Menu Text Handlers
    app.add_handler(MessageHandler(filters.Regex("^🏠 الرئيسيه$"), handlers.start))
    app.add_handler(MessageHandler(filters.Regex("^📂 الاقسام$"), handlers.categories_command))
    app.add_handler(MessageHandler(filters.Regex("^❓ المساعده$"), handlers.help_command))

    # Error Handler
    async def error_handler(update, context):
        logging.error(f"Update {update} caused error {context.error}")
    app.add_error_handler(error_handler)

    print("جاري تشغيل البوت...")
    keep_alive()
    app.run_polling()

if __name__ == "__main__":
    main()
