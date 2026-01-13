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
            handlers.TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.receive_title)],
            handlers.CATEGORY: [MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.receive_category)],
            handlers.DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.receive_description)],
            handlers.VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.receive_value_link)],
        },
        fallbacks=[CommandHandler("cancel", handlers.cancel)]
    )

    # Conversation Handler for Adding Files
    add_file_conv = ConversationHandler(
        entry_points=[CommandHandler("addfile", handlers.add_file_start)],
        states={
            handlers.TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.receive_title)],
            handlers.CATEGORY: [MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.receive_category)],
            handlers.DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.receive_description)],
            handlers.VALUE: [MessageHandler(filters.ALL & ~filters.COMMAND, handlers.receive_value_file)],
        },
        fallbacks=[CommandHandler("cancel", handlers.cancel)]
    )

    # Conversation Handler for Adding Categories
    add_category_conv = ConversationHandler(
        entry_points=[CommandHandler("addcategory", handlers.add_category_start)],
        states={
            handlers.NEW_CATEGORY_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.receive_new_category_name)],
            handlers.NEW_CATEGORY_PARENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.receive_new_category_parent)],
        },
        fallbacks=[CommandHandler("cancel", handlers.cancel)]
    )

    app.add_handler(CommandHandler("start", handlers.start))
    app.add_handler(CommandHandler("help", handlers.help_command))
    app.add_handler(CommandHandler("categories", handlers.categories_command))
    app.add_handler(CommandHandler("search", handlers.search_command))
    app.add_handler(CommandHandler("delete", handlers.delete_command))
    app.add_handler(CommandHandler("deletecategory", handlers.delete_category_command))
    
    app.add_handler(add_link_conv)
    app.add_handler(add_file_conv)
    app.add_handler(add_category_conv)
    
    app.add_handler(CallbackQueryHandler(handlers.category_callback, pattern="^cat_|back_cats"))
    app.add_handler(CallbackQueryHandler(handlers.resource_callback, pattern="^res_"))

    app.add_handler(CallbackQueryHandler(handlers.category_callback, pattern="^cat_|back_cats"))
    app.add_handler(CallbackQueryHandler(handlers.resource_callback, pattern="^res_"))

    # Menu Text Handlers
    app.add_handler(MessageHandler(filters.Regex("^🏠 الرئيسية$"), handlers.start))
    app.add_handler(MessageHandler(filters.Regex("^📂 الأقسام$"), handlers.categories_command))
    app.add_handler(MessageHandler(filters.Regex("^❓ مساعدة$"), handlers.help_command))

    print("جاري تشغيل البوت...")
    keep_alive()
    app.run_polling()

if __name__ == "__main__":
    main()
