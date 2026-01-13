from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from config import ADMIN_IDS
import database as db

# Stages for conversation handler
TITLE, TYPE, CATEGORY, DESCRIPTION, VALUE = range(5)
NEW_CATEGORY_NAME, NEW_CATEGORY_PARENT = range(2)


# Admin check decorator or helper
def is_admin(user_id):
    return user_id in ADMIN_IDS

def get_main_menu_keyboard():
    keyboard = [
        [KeyboardButton("🏠 الرئيسية"), KeyboardButton("📂 الأقسام")],
        [KeyboardButton("❓ مساعدة")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    welcome_text = (
        f"مرحباً {user.first_name}! أهلاً بك في بوت مراقى الوعى .\n"
        "استخدم القائمة أدناه للتنقل."
    )
    if is_admin(user.id):
        welcome_text += (
            "\n\n👮 **لوحة التحكم**:\n"
            "/addlink - إضافة رابط\n"
            "/addfile - إضافة ملف/وسائط\n"
            "/addcategory - إضافة قسم\n"
            "/delete - حذف محتوى\n"
            "/deletecategory - حذف قسم بالكامل"
        )
    await update.message.reply_text(welcome_text, reply_markup=get_main_menu_keyboard())

async def delete_category_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("غير مصرح.")
        return
        
    if not context.args:
        await update.message.reply_text("الاستخدام: /deletecategory <اسم_القسم_بالضبط>")
        return
        
    name = " ".join(context.args)
    # Check if category exists (logic check)
    categories = db.get_categories() # For check we can just check if it exists in DB though get_categories is a bit complex
    
    # We can just call it, if it doesn't exist it won't crash
    db.delete_category(name)
    await update.message.reply_text(f"تم حذف القسم '{name}' وجميع محتوياته بنجاح.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🤖 **دليل البوت**\n\n"
        "**1. الهيكلية**:\n"
        "   🏠 **الرئيسية**: القائمة الرئيسية.\n"
        "   📂 **الأقسام**: تصفح مجلدات المحتوى.\n"
        "      ↳ **أقسام فرعية**: مجلدات داخل مجلدات.\n"
        "      ↳ **الموارد**: ملفات، صوتيات، صور، روابط.\n\n"
        "**2. البحث عن المحتوى**:\n"
        "   • تصفح عبر زر 'الأقسام'.\n"
        "   • استخدم `/search <كلمة>` للبحث عن عناصر محددة.\n\n"
        "**3. المسؤول** (إذا كنت تمتلك الصلاحية):\n"
        "   • إضافة محتوى باستخدام أوامر /add.\n"
        "   • تنظيم الأقسام باستخدام /addcategory."
    )
    await update.message.reply_text(text, parse_mode='Markdown', reply_markup=get_main_menu_keyboard())

async def categories_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Show Top Level Categories
    categories = db.get_categories(parent=None)
    if not categories:
        await update.message.reply_text("لا توجد أقسام.")
        return

    keyboard = []
    for cat in categories:
        keyboard.append([InlineKeyboardButton(f"📁 {cat}", callback_data=f"cat_{cat}")])
    
    markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("اختر قسماً:", reply_markup=markup)

async def category_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    if data.startswith("cat_"):
        category = data[4:]
        
        # 1. Fetch Subcategories
        subcats = db.get_categories(parent=category)
        
        # 2. Fetch Direct Resources
        resources = db.get_resources_by_category(category)
        
        if not subcats and not resources:
            # Maybe show "Empty" but allow going back
            pass

        text = f"القسم: {category}\n"
        keyboard = []
        
        # Subcategories
        for sub in subcats:
             keyboard.append([InlineKeyboardButton(f"📁 {sub}", callback_data=f"cat_{sub}")])
             
        # Resources
        for res in resources:
            icon = "📄"
            if res['type'] == 'audio': icon = "🎵"
            elif res['type'] == 'photo': icon = "🖼️"
            elif res['type'] == 'video': icon = "🎥"
            elif res['type'] == 'link': icon = "🔗"
            
            keyboard.append([InlineKeyboardButton(f"{icon} {res['title']}", callback_data=f"res_{res['title']}")])
        
        # Back button - Ideally find parent of this category to go up one level, 
        # but for simplicity returning to Root Categories is a good start, or we can use a stack.
        # "back_cats" goes to root.
        keyboard.append([InlineKeyboardButton("<< القائمة الرئيسية", callback_data="back_cats")])
        markup = InlineKeyboardMarkup(keyboard)
        
        # If it was empty
        if not subcats and not resources:
             text += "(فارغ)"
             
        await query.edit_message_text(text, reply_markup=markup)
        
    elif data == "back_cats":
        # Re-fetch root categories
        categories = db.get_categories(parent=None)
        keyboard = []
        for cat in categories:
            keyboard.append([InlineKeyboardButton(f"📁 {cat}", callback_data=f"cat_{cat}")])
        markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("اختر قسماً:", reply_markup=markup)

async def resource_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    if data.startswith("res_"):
        title = data[4:]
        resource = db.get_resource_by_title(title)
        if not resource:
            await query.message.reply_text("المحتوى غير موجود.")
            return
            
        if resource.get('message_id') and resource.get('source_chat_id'):
            try:
                # Use forwarding as requested
                await context.bot.forward_message(
                    chat_id=query.message.chat_id,
                    from_chat_id=resource['source_chat_id'],
                    message_id=resource['message_id']
                )
                # Optionally send the description/caption as a separate message if it was a forward, 
                # because we can't edit the caption of a forwarded message easily to include our custom description
                # UNLESS we use copy_message (which is different from forward).
                # User asked for "forward it", so we stick to forward_message.
                # We can send the description below it.
                if resource.get('description') or resource.get('title'):
                     caption = f"**{resource['title']}**\n{resource['description']}"
                     await query.message.reply_text(caption, parse_mode='Markdown')
                return
            except Exception as e:
                # If forwarding fails (e.g. original message deleted), try fallback or report error
                print(f"Forward failed: {e}")
                # Fallback to copy/send by ID if possible (below)

        # Fallback / Legacy behavior
        response_text = (
            f"**{resource['title']}**\n"
            f"النوع: {resource['type']}\n"
            f"الوصف: {resource['description']}\n"
        )
        
        try:
            if resource['type'] == 'photo':
                await query.message.reply_photo(photo=resource['content_value'], caption=response_text, parse_mode='Markdown')
            elif resource['type'] == 'audio':
                await query.message.reply_audio(audio=resource['content_value'], caption=response_text, parse_mode='Markdown')
            elif resource['type'] == 'video':
                 await query.message.reply_video(video=resource['content_value'], caption=response_text, parse_mode='Markdown')
            elif resource['type'] == 'file':
                await query.message.reply_document(document=resource['content_value'], caption=response_text, parse_mode='Markdown')
            else:
                response_text += f"\nالرابط: {resource['content_value']}"
                await query.message.reply_text(response_text, parse_mode='Markdown')
        except Exception as e:
             await query.message.reply_text(f"خطأ في جلب المحتوى: {e}")

async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("الاستخدام: /search <كلمة_البحث>")
        return
    
    keyword = " ".join(context.args)
    results = db.search_resources(keyword)
    
    if not results:
        await update.message.reply_text("لا توجد نتائج.")
        return
        
    text = f"نتائج البحث عن '{keyword}':\n\n"
    keyboard = []
    for res in results:
        keyboard.append([InlineKeyboardButton(res['title'], callback_data=f"res_{res['title']}")])
        
    markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(text, reply_markup=markup)

async def delete_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("غير مصرح.")
        return
        
    if not context.args:
        await update.message.reply_text("الاستخدام: /delete <العنوان_بالضبط>")
        return
        
    title = " ".join(context.args)
    success = db.delete_resource(title)
    if success:
        await update.message.reply_text(f"تم حذف '{title}'.")
    else:
        await update.message.reply_text(f"لم يتم العثور على '{title}'.")

        await update.message.reply_text(f"لم يتم العثور على '{title}'.")

# --- Conversation Handler for Adding Category ---

async def add_category_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("غير مصرح.")
        return ConversationHandler.END
    
    await update.message.reply_text("أدخل اسم القسم الجديد:")
    return NEW_CATEGORY_NAME

async def receive_new_category_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text
    context.user_data['new_cat_name'] = name
    
    # Show existing categories to pick as parent
    categories = db.get_categories(parent=None)
    
    text = f"أدخل اسم القسم الأصلي (Parent) للقسم '{name}' (أو اكتب 'None' ليكون قسماً رئيسياً).\n"
    if categories:
        text += "الأقسام الرئيسية الحالية: " + ", ".join(categories)
        
    await update.message.reply_text(text)
    return NEW_CATEGORY_PARENT

async def receive_new_category_parent(update: Update, context: ContextTypes.DEFAULT_TYPE):
    parent = update.message.text
    if parent.lower() == 'none' or parent == 'لاشيء':
        parent = None
        
    name = context.user_data['new_cat_name']
    
    if db.add_category(name, parent):
        parent_text = f" داخل '{parent}'" if parent else " (قسم رئيسي)"
        await update.message.reply_text(f"تم إضافة القسم '{name}'{parent_text}.")
    else:
        await update.message.reply_text("فشل إضافة القسم.")
    return ConversationHandler.END


async def add_link_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("غير مصرح.")
        return ConversationHandler.END
        
    await update.message.reply_text("أدخل عنوان (Title) الرابط:")
    context.user_data['type'] = 'link'
    return TITLE

async def add_file_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("غير مصرح.")
        return ConversationHandler.END
        
    await update.message.reply_text("أدخل عنوان (Title) الملف:")
    context.user_data['type'] = 'file'
    return TITLE

async def receive_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    title = update.message.text
    if db.get_resource_by_title(title):
        await update.message.reply_text("العنوان موجود بالفعل. الرجاء اختيار عنوان آخر.")
        return TITLE
        
    context.user_data['title'] = title
    
    # Show existing categories as suggestions?
    categories = db.get_categories()
    existing_cats = ", ".join(categories) if categories else "لا يوجد"
    
    await update.message.reply_text(f"أدخل القسم (الأقسام المتاحة: {existing_cats}):")
    return CATEGORY

async def receive_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['category'] = update.message.text
    await update.message.reply_text("أدخل الوصف:")
    return DESCRIPTION

async def receive_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['description'] = update.message.text
    if context.user_data['type'] == 'link':
        await update.message.reply_text("أدخل الرابط (URL):")
    else:
        await update.message.reply_text("قم برفع الملف الآن:")
    return VALUE

async def receive_value_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    context.user_data['content_value'] = url
    return await save_resource(update, context)

async def receive_value_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Determine file type and ID
    file_id = None
    file_type = 'file'
    
    msg = update.message
    if msg.audio:
        file_id = msg.audio.file_id
        file_type = 'audio'
    elif msg.voice:
        file_id = msg.voice.file_id
        file_type = 'audio'
    elif msg.photo:
        file_id = msg.photo[-1].file_id
        file_type = 'photo'
    elif msg.video:
        file_id = msg.video.file_id
        file_type = 'video'
    elif msg.document:
        file_id = msg.document.file_id
        # Keep generic 'file' or check mime_type if needed
        
    if not file_id:
        await update.message.reply_text("الرجاء رفع ملف/صورة/صوت صالح.")
        return VALUE
    
    # Override the initial generic 'file' type if we detected something specific
    context.user_data['type'] = file_type
    context.user_data['content_value'] = file_id
    context.user_data['message_id'] = update.message.message_id
    context.user_data['source_chat_id'] = update.message.chat_id
    
    return await save_resource(update, context)

async def save_resource(update, context):
    data = context.user_data
    db.add_resource(
        data['title'],
        data['type'],
        data['category'],
        data['description'],
        data['content_value'],
        data.get('message_id'),
        data.get('source_chat_id')
    )
    await update.message.reply_text(f"تمت إضافة {data['type']} بنجاح: {data['title']}")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("تم إلغاء العملية.")
    return ConversationHandler.END
