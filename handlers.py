from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from config import ADMIN_IDS
import database as db
import html

# Stages for conversation handler
TITLE, TYPE, CATEGORY, DESCRIPTION, VALUE = range(5)
NEW_CATEGORY_NAME, NEW_CATEGORY_PARENT = range(2)
EDIT_HELP_TEXT = 0
ADD_SERIES_NAME, ADD_SERIES_CATEGORY, ADD_SERIES_DESC = range(3)
SERIES_ITEM_SERIES, SERIES_ITEM_NUMBER, SERIES_ITEM_TITLE, SERIES_ITEM_DESC, SERIES_ITEM_VALUE = range(5)
MOVE_TYPE, MOVE_ITEM_SELECT, MOVE_TARGET_CAT = range(3)
RENAME_TYPE, RENAME_ITEM_SELECT, RENAME_NEW_NAME = range(3)


# Admin check decorator or helper
def is_admin(user_id):
    return user_id in ADMIN_IDS

def get_main_menu_keyboard():
    keyboard = [
        [KeyboardButton("📂 الاقسام"), KeyboardButton("🏠 الرئيسيه")],
        [KeyboardButton("❓ المساعده")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_cancel_keyboard():
    keyboard = [[KeyboardButton("❌ إلغاء")]]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_category_selection_markup(parent_name=None, prefix="ser"):
    """Generate markup for hierarchical category selection."""
    categories = db.get_categories(parent=parent_name)
    keyboard = []
    
    # Navigation to subcategories
    for cat in categories:
        keyboard.append([InlineKeyboardButton(f"📁 {cat}", callback_data=f"{prefix}_nav_{cat}")])
    
    # Action buttons
    actions = []
    if parent_name:
        # Up button
        parent_info = db.get_category_info(parent_name)
        up_callback = f"{prefix}_nav_{parent_info['parent_name']}" if parent_info and parent_info['parent_name'] else f"{prefix}_nav_root"
        actions.append(InlineKeyboardButton("⬅️ رجوع", callback_data=up_callback))
        # Select current button
        actions.append(InlineKeyboardButton("✅ اختيار هذا القسم", callback_data=f"{prefix}_sel_{parent_name}"))
    else:
        # Root level
        actions.append(InlineKeyboardButton("⏭️ بدون قسم (رئيسي)", callback_data=f"{prefix}_sel_none"))
        
    if actions:
        keyboard.append(actions)
        
    # Always add a cancel button at the bottom
    keyboard.append([InlineKeyboardButton("❌ إلغاء", callback_data="cancel_conv")])
        
    return InlineKeyboardMarkup(keyboard)

def get_move_find_markup(move_type, parent_name=None):
    """Generate markup for finding the item to move hierarchical."""
    categories = db.get_categories(parent=parent_name)
    keyboard = []
    
    # Categories / Folders
    for cat in categories:
        row = [InlineKeyboardButton(f"📁 {cat}", callback_data=f"mfind_nav_{cat}")]
        if move_type == 'cat':
             row.append(InlineKeyboardButton("✅ انقل هذه", callback_data=f"mfind_sel_{cat}"))
        keyboard.append(row)
    
    # Items
    if move_type == 'res':
        resources = db.get_resources_by_category(parent_name)
        for res in resources:
            keyboard.append([InlineKeyboardButton(f"📄 {res['title']} (نقل)", callback_data=f"mfind_sel_{res['title']}")])
    elif move_type == 'ser':
        series_list = db.get_series_by_category(parent_name)
        for ser in series_list:
            keyboard.append([InlineKeyboardButton(f"📚 {ser['name']} (نقل)", callback_data=f"mfind_sel_{ser['name']}")])
            
    # Action buttons
    actions = []
    if parent_name:
        parent_info = db.get_category_info(parent_name)
        up_callback = f"mfind_nav_{parent_info['parent_name']}" if parent_info and parent_info['parent_name'] else "mfind_nav_root"
        actions.append(InlineKeyboardButton("⬅️ رجوع", callback_data=up_callback))
        
    if actions:
        keyboard.append(actions)
        
    # Always add a cancel button at the bottom
    keyboard.append([InlineKeyboardButton("❌ إلغاء", callback_data="cancel_conv")])
        
    return InlineKeyboardMarkup(keyboard)

def get_rename_find_markup(rename_type, parent_name=None):
    """Generate markup for finding the item to rename hierarchical."""
    categories = db.get_categories(parent=parent_name)
    keyboard = []
    
    # Categories / Folders
    for cat in categories:
        row = [InlineKeyboardButton(f"📁 {cat}", callback_data=f"rfind_nav_{cat}")]
        if rename_type == 'cat':
             row.append(InlineKeyboardButton("✏️ اختر للتعديل", callback_data=f"rfind_sel_{cat}"))
        keyboard.append(row)
    
    # Items
    if rename_type == 'res':
        resources = db.get_resources_by_category(parent_name)
        for res in resources:
            keyboard.append([InlineKeyboardButton(f"📄 {res['title']} (تعديل)", callback_data=f"rfind_sel_{res['title']}")])
    elif rename_type == 'ser' or rename_type == 'sitem':
        series_list = db.get_series_by_category(parent_name)
        for ser in series_list:
            if rename_type == 'ser':
                keyboard.append([InlineKeyboardButton(f"📚 {ser['name']} (تعديل)", callback_data=f"rfind_sel_{ser['name']}")])
            else:
                keyboard.append([InlineKeyboardButton(f"📚 {ser['name']} (ادخل السلسلة)", callback_data=f"rfind_pickser_{ser['name']}")])
            
    # Action buttons
    actions = []
    if parent_name:
        parent_info = db.get_category_info(parent_name)
        up_callback = f"rfind_nav_{parent_info['parent_name']}" if parent_info and parent_info['parent_name'] else "rfind_nav_root"
        actions.append(InlineKeyboardButton("⬅️ رجوع", callback_data=up_callback))
        
    if actions:
        keyboard.append(actions)
        
    # Always add a cancel button at the bottom
    keyboard.append([InlineKeyboardButton("❌ إلغاء", callback_data="cancel_conv")])
        
    return InlineKeyboardMarkup(keyboard)

def get_series_item_rename_markup(series_name):
    """List items in a series for renaming."""
    items = db.get_series_items(series_name)
    keyboard = []
    for item in items:
        keyboard.append([InlineKeyboardButton(f"#{item['item_number']} {item['title']}", callback_data=f"rfind_selsitem_{item['item_number']}")])
    
    keyboard.append([InlineKeyboardButton("⬅️ رجوع", callback_data=f"rename_type_sitem")])
    keyboard.append([InlineKeyboardButton("❌ إلغاء", callback_data="cancel_conv")])
    return InlineKeyboardMarkup(keyboard)

def is_valid_category_name(name: str):
    # Check if it looks like a command, is exactly 'command', or is the cancel button
    if name.startswith('/') or name.lower() == 'command' or name == "❌ إلغاء":
        return False
    return True

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    welcome_text = (
        f"مرحباً {user.first_name}! أهلاً بك في بوت مراقى الوعى .\n"
        "استخدم القائمة أدناه للتنقل."
    )
    if is_admin(user.id):
        welcome_text += (
            "\n\n👮 **لوحة التحكم**:\n"
            "أوامر التعامل مع الوسائط\n"
            "/addlink - إضافة رابط\n"
            "/addfile - إضافة ملف/وسائط\n"
            "/move - نقل (قسم/سلسلة/مادة)\n"
            "/rename - تعديل اسم (قسم/سلسلة/مادة)\n"
            "/delete - حذف محتوى\n"
            "أوامر الاقسام\n"
            "/addcategory - إضافة قسم\n"
            "/deletecategory - حذف قسم بالكامل\n"
            "أوامر السلاسل \n"
            "/addseries - إضافة سلسلة\n"
            "/addtoseries - إضافة محتوى لسلسلة\n"
            "/deleteseries - حذف سلسلة\n"
            "أوامر متقدمة\n"
            "/edithelp - تعديل رسالة المساعدة"
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
    # Store name for confirmation
    context.user_data['delete_cat_name'] = name
    
    keyboard = [
        [InlineKeyboardButton("✅ نعم، احذف", callback_data=f"confirm_del_cat_{name}")],
        [InlineKeyboardButton("❌ تراجع", callback_data="cancel_del")]
    ]
    markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(f"هل أنت متأكد من حذف القسم '{name}' وجميع محتوياته؟", reply_markup=markup)

async def confirm_delete_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    name = query.data.replace("confirm_del_cat_", "")
    
    db.delete_category(name)
    await query.edit_message_text(f"تم حذف القسم '{name}' وجميع محتوياته بنجاح.")
    await query.message.reply_text("تم العوده للقائمة الرئيسية.", reply_markup=get_main_menu_keyboard())

async def cancel_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("تم إلغاء التراجع عن الحذف.")
    await query.message.reply_text("تم العوده للقائمة الرئيسية.", reply_markup=get_main_menu_keyboard())


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    default_text = (
        "🤖 **دليل البوت**\n\n"
        "**1. الهيكلية**:\n"
        "   🏠 **الرئيسيه**: القائمة الرئيسية.\n"
        "   📂 **الاقسام**: تصفح مجلدات المحتوى.\n"
        "      ↳ **أقسام فرعية**: مجلدات داخل مجلدات.\n"
        "      ↳ **الموارد**: ملفات، صوتيات، صور، روابط.\n\n"
    )
    text = db.get_setting("help_text", default_text)
    await update.message.reply_text(text, parse_mode='HTML', reply_markup=get_main_menu_keyboard())

async def edit_help_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("غير مصرح.")
        return ConversationHandler.END
    
    current_help = db.get_setting("help_text", "لم يتم ضبط رسالة المساعدة بعد.")
    await update.message.reply_text(
        f"أرسل رسالة المساعدة الجديدة الآن.\n\nالرسالة الحالية:\n---\n{current_help}\n---", 
        reply_markup=get_cancel_keyboard()
    )
    return EDIT_HELP_TEXT

async def receive_help_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    new_text = update.message.text
    db.set_setting("help_text", new_text)
    await update.message.reply_text("تم تحديث رسالة المساعدة بنجاح.", reply_markup=get_main_menu_keyboard())
    return ConversationHandler.END

async def categories_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Show Top Level Categories, Series, and Resources
    user = update.effective_user
    print(f"Categories command triggered by user {user.id} ({user.username})")
    
    categories = db.get_categories(parent=None)
    series_list = db.get_series_by_category(None)
    resources = db.get_resources_by_category(None)
    
    if not categories and not series_list and not resources:
        await update.message.reply_text("لا توجد محتويات في القائمة الرئيسية.")
        return

    keyboard = []
    # Categories
    for cat in categories:
        keyboard.append([InlineKeyboardButton(f"📁 {cat}", callback_data=f"cat_{cat}")])
    
    # Series
    for series in series_list:
        keyboard.append([InlineKeyboardButton(f"📚 سلسلة {series['name']}", callback_data=f"cat_ser_{series['name']}")])
    
    # Resources
    for res in resources:
        icon = "📄"
        if res['type'] == 'audio': icon = "🎵"
        elif res['type'] == 'photo': icon = "🖼️"
        elif res['type'] == 'video': icon = "🎥"
        elif res['type'] == 'link': icon = "🔗"
        keyboard.append([InlineKeyboardButton(f"{icon} {res['title']}", callback_data=f"res_{res['title']}")])
    
    markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("اختر قسماً أو مادة:", reply_markup=markup)

async def category_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    if data.startswith("cat_ser_"):
        # User clicked on a series from category view
        series_name = data[8:]  # Remove "cat_ser_" prefix
        items = db.get_series_items(series_name)
        
        if not items:
            await query.edit_message_text(f"السلسلة '{html.escape(series_name)}' فارغة.")
            return
        
        text = f"📚 السلسلة: {html.escape(series_name)}\n\n"
        keyboard = []
        
        for item in items:
            icon = "📄"
            if item['type'] == 'audio': icon = "🎵"
            elif item['type'] == 'photo': icon = "🖼️"
            elif item['type'] == 'video': icon = "🎥"
            elif item['type'] == 'link': icon = "🔗"
            
            # Make each item clickable
            button_text = f"{item['item_number']}. {icon} {item['title']}"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f"ser_item_{series_name}_{item['item_number']}")])
        
        keyboard.append([InlineKeyboardButton("<< رجوع", callback_data="back_cats")])
        markup = InlineKeyboardMarkup(keyboard)
        
        text += "اختر مادة لعرضها:"
        await query.edit_message_text(text, reply_markup=markup, parse_mode='HTML')

    elif data.startswith("cat_"):
        category = data[4:]
        
        # 1. Fetch Subcategories
        subcats = db.get_categories(parent=category)
        
        # 2. Fetch Direct Resources
        resources = db.get_resources_by_category(category)
        
        # 3. Fetch Series in this category
        series_list = db.get_series_by_category(category)
        
        if not subcats and not resources and not series_list:
            # Maybe show "Empty" but allow going back
            pass

        text = f"القسم: {html.escape(category)}\n"
        keyboard = []
        
        # Subcategories
        for sub in subcats:
             keyboard.append([InlineKeyboardButton(f"📁 {sub}", callback_data=f"cat_{sub}")])
        
        # Series in this category
        for series in series_list:
            keyboard.append([InlineKeyboardButton(f"📚 سلسلة {series['name']}", callback_data=f"cat_ser_{series['name']}")])
             
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
        if not subcats and not resources and not series_list:
             text += "(فارغ)"
             
        await query.edit_message_text(text, reply_markup=markup, parse_mode='HTML')
    
    elif data == "back_cats":
        # Re-fetch root content
        categories = db.get_categories(parent=None)
        series_list = db.get_series_by_category(None)
        resources = db.get_resources_by_category(None)
        
        keyboard = []
        for cat in categories:
            keyboard.append([InlineKeyboardButton(f"📁 {cat}", callback_data=f"cat_{cat}")])
        for series in series_list:
            keyboard.append([InlineKeyboardButton(f"📚 سلسلة {series['name']}", callback_data=f"cat_ser_{series['name']}")])
        for res in resources:
            icon = "📄"
            if res['type'] == 'audio': icon = "🎵"
            elif res['type'] == 'photo': icon = "🖼️"
            elif res['type'] == 'video': icon = "🎥"
            elif res['type'] == 'link': icon = "🔗"
            keyboard.append([InlineKeyboardButton(f"{icon} {res['title']}", callback_data=f"res_{res['title']}")])
            
        markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("اختر قسماً أو مادة:", reply_markup=markup, parse_mode='HTML')
    
    elif data.startswith("ser_item_"):
        # User clicked on a specific series item from category view
        # Format: ser_item_{series_name}_{item_number}
        parts = data[9:].rsplit('_', 1)  # Split from the right, once
        if len(parts) != 2:
            await query.message.reply_text("خطأ في البيانات.")
            return
        
        series_name = parts[0]
        try:
            item_number = int(parts[1])
        except ValueError:
            await query.message.reply_text("رقم المادة غير صحيح.")
            return
        
        # Get the specific item
        items = db.get_series_items(series_name)
        item = None
        for i in items:
            if i['item_number'] == item_number:
                item = i
                break
        
        if not item:
            await query.message.reply_text("المادة غير موجودة.")
            return
        
        # Send the item using the helper function
        await send_series_item_direct(query, context, item)

async def send_series_item_direct(query, context, item):
    """Helper function to send a series item directly"""
    chat_id = query.message.chat_id
    
    if item.get('message_id') and item.get('source_chat_id'):
        try:
            # Use copy_message to avoid the "Forwarded from" tag
            await context.bot.copy_message(
                chat_id=chat_id,
                from_chat_id=item['source_chat_id'],
                message_id=item['message_id']
            )
            # We don't need a separate caption if copy_message is used, 
            # but user said "dont show a mesage forward" which might mean they want the clean copy.
            # If there was a custom description, we can send it or use caption in copy_message.
            return
        except Exception as e:
            print(f"Copy failed: {e}")

    # Fallback / Legacy behavior
    response_text = (
        f"<b>{html.escape(item['title'])}</b>\n"
        f"النوع: {item['type']}\n"
        f"الوصف: {html.escape(item['description'])}\n"
    )
    
    try:
        if item['type'] == 'photo':
            await context.bot.send_photo(chat_id=chat_id, photo=item['content_value'], caption=response_text, parse_mode='HTML')
        elif item['type'] == 'audio':
            await context.bot.send_audio(chat_id=chat_id, audio=item['content_value'], caption=response_text, parse_mode='HTML')
        elif item['type'] == 'video':
             await context.bot.send_video(chat_id=chat_id, video=item['content_value'], caption=response_text, parse_mode='HTML')
        elif item['type'] == 'file':
            await context.bot.send_document(chat_id=chat_id, document=item['content_value'], caption=response_text, parse_mode='HTML')
        else:
            response_text += f"\nالرابط: {item['content_value']}"
            await context.bot.send_message(chat_id=chat_id, text=response_text, parse_mode='HTML')
    except Exception as e:
         print(f"Error sending item: {e}")

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
                # Use copy_message to avoid the "Forwarded from" tag
                await context.bot.copy_message(
                    chat_id=query.message.chat_id,
                    from_chat_id=resource['source_chat_id'],
                    message_id=resource['message_id']
                )
                return
            except Exception as e:
                print(f"Copy failed: {e}")

        # Fallback / Legacy behavior
        response_text = (
            f"<b>{html.escape(resource['title'])}</b>\n"
            f"النوع: {resource['type']}\n"
            f"الوصف: {html.escape(resource['description'])}\n"
        )
        
        try:
            if resource['type'] == 'photo':
                await query.message.reply_photo(photo=resource['content_value'], caption=response_text, parse_mode='HTML')
            elif resource['type'] == 'audio':
                await query.message.reply_audio(audio=resource['content_value'], caption=response_text, parse_mode='HTML')
            elif resource['type'] == 'video':
                 await query.message.reply_video(video=resource['content_value'], caption=response_text, parse_mode='HTML')
            elif resource['type'] == 'file':
                await query.message.reply_document(document=resource['content_value'], caption=response_text, parse_mode='HTML')
            else:
                response_text += f"\nالرابط: {resource['content_value']}"
                await query.message.reply_text(response_text, parse_mode='HTML')
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
    resource = db.get_resource_by_title(title)
    if not resource:
        await update.message.reply_text(f"لم يتم العثور على '{title}'.")
        return

    keyboard = [
        [InlineKeyboardButton("✅ نعم، احذف", callback_data=f"confirm_del_res_{title}")],
        [InlineKeyboardButton("❌ تراجع", callback_data="cancel_del")]
    ]
    markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(f"هل أنت متأكد من حذف '{title}'؟", reply_markup=markup)

async def confirm_delete_resource(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    title = query.data.replace("confirm_del_res_", "")
    
    success = db.delete_resource(title)
    if success:
        await query.edit_message_text(f"تم حذف '{title}'.")
    else:
        await query.edit_message_text(f"فشل حذف '{title}'.")
    
    await query.message.reply_text("تم العوده للقائمة الرئيسية.", reply_markup=get_main_menu_keyboard())

# --- Conversation Handler for Adding Category ---

def get_add_cat_selection_markup(parent_name=None):
    """Generate markup for hierarchical category selection during category creation."""
    categories = db.get_categories(parent=parent_name)
    keyboard = []
    
    # Navigation to subcategories
    for cat in categories:
        keyboard.append([InlineKeyboardButton(f"📁 {cat}", callback_data=f"ac_nav_{cat}")])
    
    # Action buttons
    actions = []
    if parent_name:
        # Up button
        parent_info = db.get_category_info(parent_name)
        up_callback = f"ac_nav_{parent_info['parent_name']}" if parent_info and parent_info['parent_name'] else "ac_nav_root"
        actions.append(InlineKeyboardButton("⬅️ رجوع", callback_data=up_callback))
        # Select current button
        actions.append(InlineKeyboardButton("✅ اختيار هذا القسم", callback_data=f"ac_sel_{parent_name}"))
    else:
        # Root level
        actions.append(InlineKeyboardButton("⏭️ بدون قسم (رئيسي)", callback_data="ac_sel_none"))
        
    if actions:
        keyboard.append(actions)
        
    # Always add a cancel button at the bottom
    keyboard.append([InlineKeyboardButton("❌ إلغاء", callback_data="cancel_conv")])
        
    return InlineKeyboardMarkup(keyboard)

async def add_category_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("غير مصرح.")
        return ConversationHandler.END
    
    await update.message.reply_text("أدخل اسم القسم الجديد:", reply_markup=get_cancel_keyboard())
    return NEW_CATEGORY_NAME

async def receive_new_category_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text
    if not is_valid_category_name(name):
        await update.message.reply_text("اسم القسم غير صالح. يرجى عدم البدء بـ '/' أو استخدام كلمة 'command'.", reply_markup=get_cancel_keyboard())
        return NEW_CATEGORY_NAME

    context.user_data['new_cat_name'] = name
    
    # Show hierarchical selection from root
    markup = get_add_cat_selection_markup(None)
    await update.message.reply_text(f"اختر القسم الأصلي (Parent) للقسم '{name}':", reply_markup=markup)
    return NEW_CATEGORY_PARENT

async def receive_new_category_parent_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data.startswith("ac_nav_"):
        # Navigation
        category_name = data.replace("ac_nav_", "")
        if category_name == "root":
            category_name = None
            text = f"اختر القسم الأصلي (Parent) للقسم '{context.user_data['new_cat_name']}':"
        else:
            text = f"القسم الحالي: {category_name}\nيمكنك وضع القسم الجديد هنا أو الدخول لقسم فرعي:"
            
        markup = get_add_cat_selection_markup(category_name)
        await query.edit_message_text(text, reply_markup=markup)
        return NEW_CATEGORY_PARENT
        
    elif data.startswith("ac_sel_"):
        # Selection
        parent_data = data.replace("ac_sel_", "")
        if parent_data == "none":
            parent = None
        else:
            parent = parent_data
            
        name = context.user_data['new_cat_name']
        
        if db.add_category(name, parent):
            parent_text = f" داخل '{parent}'" if parent else " (قسم رئيسي)"
            await query.edit_message_text(f"تم إضافة القسم '{name}'{parent_text}.")
            await query.message.reply_text("تم العوده للقائمة الرئيسية.", reply_markup=get_main_menu_keyboard())
        else:
            await query.edit_message_text("فشل إضافة القسم.")
            await query.message.reply_text("تم العوده للقائمة الرئيسية.", reply_markup=get_main_menu_keyboard())
        return ConversationHandler.END

async def receive_new_category_parent(update: Update, context: ContextTypes.DEFAULT_TYPE):
    parent = update.message.text
    if parent.lower() == 'none' or parent == 'لاشيء':
        parent = None
        
    name = context.user_data['new_cat_name']
    
    if db.add_category(name, parent):
        parent_text = f" داخل '{parent}'" if parent else " (قسم رئيسي)"
        await update.message.reply_text(f"تم إضافة القسم '{name}'{parent_text}.", reply_markup=get_main_menu_keyboard())
    else:
        await update.message.reply_text("فشل إضافة القسم.", reply_markup=get_main_menu_keyboard())
    return ConversationHandler.END


async def add_link_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("غير مصرح.")
        return ConversationHandler.END
        
    await update.message.reply_text("أدخل عنوان (Title) الرابط:", reply_markup=get_cancel_keyboard())
    context.user_data['type'] = 'link'
    return TITLE

async def add_file_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("غير مصرح.")
        return ConversationHandler.END
        
    await update.message.reply_text("أدخل عنوان (Title) الملف:", reply_markup=get_cancel_keyboard())
    context.user_data['type'] = 'file'
    return TITLE

async def receive_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    title = update.message.text
    if db.get_resource_by_title(title):
        await update.message.reply_text("العنوان موجود بالفعل. الرجاء اختيار عنوان آخر.")
        return TITLE
        
    context.user_data['title'] = title
    
    # Show hierarchical selection from root
    markup = get_category_selection_markup(None, prefix="rsel")
    await update.message.reply_text("اختر قسماً للمحتوى (أو تنقل بين الأقسام):", reply_markup=markup)
    return CATEGORY

async def receive_category_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data.startswith("rsel_nav_"):
        # Navigation
        category_name = data.replace("rsel_nav_", "")
        if category_name == "root":
            category_name = None
            text = "اختر قسماً للمحتوى (أو تنقل بين الأقسام):"
        else:
            text = f"القسم الحالي: {category_name}\nيمكنك وضع المحتوى هنا أو الدخول لقسم فرعي:"
            
        markup = get_category_selection_markup(category_name, prefix="rsel")
        await query.edit_message_text(text, reply_markup=markup)
        return CATEGORY
        
    elif data.startswith("rsel_sel_"):
        # Selection
        category = data.replace("rsel_sel_", "")
        if category == "none":
            context.user_data['category'] = None
            await query.edit_message_text("تم اختيار: بدون قسم (رئيسي).")
        else:
            context.user_data['category'] = category
            await query.edit_message_text(f"تم اختيار القسم: {category}")
        
        keyboard = [[InlineKeyboardButton("⏭️ تخطي (بدون وصف)", callback_data="skip_desc")]]
        markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text("أدخل الوصف (يمكنك الضغط على زر التخطي):", reply_markup=markup)
        return DESCRIPTION

async def receive_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    category = update.message.text
    if not is_valid_category_name(category):
         await update.message.reply_text("اسم القسم غير صالح. يرجى التغيير.", reply_markup=get_cancel_keyboard())
         return CATEGORY
         
    context.user_data['category'] = category
    context.user_data['category'] = category
    keyboard = [[InlineKeyboardButton("⏭️ تخطي (بدون وصف)", callback_data="skip_desc")]]
    markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("أدخل الوصف (يمكنك الضغط على زر التخطي):", reply_markup=markup)
    return DESCRIPTION

async def receive_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['description'] = update.message.text
    if context.user_data['type'] == 'link':
        await update.message.reply_text("أدخل الرابط (URL):")
    else:
        await update.message.reply_text("قم برفع الملف الآن:")
    return VALUE

async def skip_description_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['description'] = ""
    if context.user_data['type'] == 'link':
        await query.edit_message_text("تم تخطي الوصف. أدخل الرابط (URL):")
    else:
        await query.edit_message_text("تم تخطي الوصف. قم برفع الملف الآن:")
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
    await update.message.reply_text(f"تمت إضافة {data['type']} بنجاح: {data['title']}", reply_markup=get_main_menu_keyboard())
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message if update.message else update.callback_query.message
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text("تم إلغاء العملية.")
        await msg.reply_text("تم العوده للقائمة الرئيسية.", reply_markup=get_main_menu_keyboard())
    else:
        await msg.reply_text("تم إلغاء العملية.", reply_markup=get_main_menu_keyboard())
    return ConversationHandler.END

# --- Admin: Add Series ---

async def add_series_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("غير مصرح.")
        return ConversationHandler.END
    
    await update.message.reply_text("أدخل اسم السلسلة الجديدة:", reply_markup=get_cancel_keyboard())
    return ADD_SERIES_NAME

async def receive_series_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text
    if not is_valid_category_name(name):
        await update.message.reply_text("اسم السلسلة غير صالح. يرجى عدم البدء بـ '/' أو استخدام كلمة 'command'.", reply_markup=get_cancel_keyboard())
        return ADD_SERIES_NAME
    
    context.user_data['series_name'] = name
    
    # Start hierarchical selection from root
    markup = get_category_selection_markup(None)
    await update.message.reply_text("اختر قسماً للسلسلة (أو تنقل بين الأقسام):", reply_markup=markup)
    return ADD_SERIES_CATEGORY

async def receive_series_category_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data.startswith("ser_nav_"):
        # Navigation
        category_name = data.replace("ser_nav_", "")
        if category_name == "root":
            category_name = None
            text = "اختر قسماً للسلسلة (أو تنقل بين الأقسام):"
        else:
            text = f"القسم الحالي: {category_name}\nيمكنك تنزيل السلسلة هنا أو الدخول لقسم فرعي:"
            
        markup = get_category_selection_markup(category_name)
        await query.edit_message_text(text, reply_markup=markup)
        return ADD_SERIES_CATEGORY
        
    elif data.startswith("ser_sel_"):
        # Selection
        category_data = data.replace("ser_sel_", "")
        if category_data == "none":
            context.user_data['series_category'] = None
            await query.edit_message_text("تم اختيار: بدون قسم (رئيسي).")
        else:
            context.user_data['series_category'] = category_data
            await query.edit_message_text(f"تم اختيار القسم: {category_data}")
        
        keyboard = [[InlineKeyboardButton("⏭️ تخطي (بدون وصف)", callback_data="skip_ser_desc")]]
        markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text("أدخل وصفاً للسلسلة (اختياري):", reply_markup=markup)
        return ADD_SERIES_DESC

async def receive_series_category_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    category = update.message.text
    if category.lower() in ['لا', 'no', 'none']:
        context.user_data['series_category'] = None
    else:
        context.user_data['series_category'] = category
    
    keyboard = [[InlineKeyboardButton("⏭️ تخطي (بدون وصف)", callback_data="skip_ser_desc")]]
    markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("أدخل وصفاً للسلسلة (اختياري):", reply_markup=markup)
    return ADD_SERIES_DESC

async def receive_series_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    description = update.message.text
    if description.lower() in ['لا', 'no', 'none']:
        description = None
    
    name = context.user_data['series_name']
    category = context.user_data.get('series_category')
    
    if db.add_series(name, description, category):
        category_text = f" في القسم '{category}'" if category else ""
        await update.message.reply_text(f"تم إضافة سلسلة '{name}'{category_text} بنجاح.", reply_markup=get_main_menu_keyboard())
    else:
        await update.message.reply_text(f"فشل إضافة السلسلة. ربما الاسم موجود بالفعل.", reply_markup=get_main_menu_keyboard())
    
    return ConversationHandler.END

# --- Admin: Add to Series ---

async def add_to_series_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("غير مصرح.")
        return ConversationHandler.END
    
    series_list = db.get_all_series()
    if not series_list:
        await update.message.reply_text("لا توجد سلاسل. يرجى إضافة سلسلة أولاً باستخدام /addseries")
        return ConversationHandler.END
    
    keyboard = []
    for series in series_list:
        keyboard.append([InlineKeyboardButton(f"📚 {series['name']}", callback_data=f"add_to_{series['name']}")])
    
    keyboard.append([InlineKeyboardButton("❌ إلغاء", callback_data="cancel_conv")])
    
    markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("اختر السلسلة لإضافة محتوى إليها:", reply_markup=markup)
    return SERIES_ITEM_SERIES

async def receive_series_for_item(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    series_name = query.data.replace("add_to_", "")
    context.user_data['target_series'] = series_name
    
    await query.edit_message_text(f"تم اختيار السلسلة: {series_name}")
    await query.message.reply_text("أدخل رقم المادة في السلسلة (مثال: 1, 2, 3...):", reply_markup=get_cancel_keyboard())
    return SERIES_ITEM_NUMBER

async def receive_item_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        item_number = int(update.message.text)
        if item_number < 1:
            raise ValueError
        context.user_data['item_number'] = item_number
        await update.message.reply_text("أدخل عنوان المادة:")
        return SERIES_ITEM_TITLE
    except ValueError:
        await update.message.reply_text("يرجى إدخال رقم صحيح أكبر من 0:")
        return SERIES_ITEM_NUMBER

async def receive_item_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['item_title'] = update.message.text
    keyboard = [[InlineKeyboardButton("⏭️ تخطي (بدون وصف)", callback_data="skip_item_desc")]]
    markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("أدخل وصف المادة (اختياري):", reply_markup=markup)
    return SERIES_ITEM_DESC

async def receive_item_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['item_description'] = update.message.text
    await update.message.reply_text("قم برفع الملف أو أرسل الرابط:")
    return SERIES_ITEM_VALUE

async def skip_ser_description_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    name = context.user_data['series_name']
    category = context.user_data.get('series_category')
    
    if db.add_series(name, None, category):
        category_text = f" في القسم '{category}'" if category else ""
        await query.edit_message_text(f"تم إضافة سلسلة '{name}'{category_text} بنجاح (بدون وصف).")
    else:
        await query.edit_message_text(f"فشل إضافة السلسلة. ربما الاسم موجود بالفعل.")
    
    await query.message.reply_text("تم العوده للقائمة الرئيسية.", reply_markup=get_main_menu_keyboard())
    return ConversationHandler.END

async def skip_item_description_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['item_description'] = ""
    await query.edit_message_text("تم تخطي الوصف. قم برفع الملف أو أرسل الرابط:")
    return SERIES_ITEM_VALUE

async def receive_item_value(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Determine if it's a file or link
    file_id = None
    file_type = 'file'
    message_id = None
    source_chat_id = None
    content_value = None
    
    msg = update.message
    
    # Check for text (link)
    if msg.text:
        content_value = msg.text
        file_type = 'link'
    # Check for media
    elif msg.audio:
        file_id = msg.audio.file_id
        file_type = 'audio'
        message_id = msg.message_id
        source_chat_id = msg.chat_id
        content_value = file_id
    elif msg.voice:
        file_id = msg.voice.file_id
        file_type = 'audio'
        message_id = msg.message_id
        source_chat_id = msg.chat_id
        content_value = file_id
    elif msg.photo:
        file_id = msg.photo[-1].file_id
        file_type = 'photo'
        message_id = msg.message_id
        source_chat_id = msg.chat_id
        content_value = file_id
    elif msg.video:
        file_id = msg.video.file_id
        file_type = 'video'
        message_id = msg.message_id
        source_chat_id = msg.chat_id
        content_value = file_id
    elif msg.document:
        file_id = msg.document.file_id
        file_type = 'file'
        message_id = msg.message_id
        source_chat_id = msg.chat_id
        content_value = file_id
    else:
        await update.message.reply_text("الرجاء رفع ملف/صورة/صوت صالح أو إرسال رابط.")
        return SERIES_ITEM_VALUE
    
    # Save to database
    series_name = context.user_data['target_series']
    item_number = context.user_data['item_number']
    title = context.user_data['item_title']
    description = context.user_data['item_description']
    
    success = db.add_series_item(
        series_name, item_number, title, file_type, 
        description, content_value, message_id, source_chat_id
    )
    
    if success:
        await update.message.reply_text(
            f"تم إضافة المادة #{item_number} إلى السلسلة '{series_name}' بنجاح.", 
            reply_markup=get_main_menu_keyboard()
        )
    else:
        await update.message.reply_text(
            f"فشل إضافة المادة. ربما الرقم {item_number} موجود بالفعل في هذه السلسلة.", 
            reply_markup=get_main_menu_keyboard()
        )
    
    return ConversationHandler.END

# --- Admin: Delete Series ---

async def delete_series_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("غير مصرح.")
        return
        
    if not context.args:
        await update.message.reply_text("الاستخدام: /deleteseries <اسم_السلسلة_بالضبط>")
        return
        
    name = " ".join(context.args)
    
    keyboard = [
        [InlineKeyboardButton("✅ نعم، احذف", callback_data=f"confirm_del_ser_{name}")],
        [InlineKeyboardButton("❌ تراجع", callback_data="cancel_del")]
    ]
    markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(f"هل أنت متأكد من حذف السلسلة '{name}' وجميع محتوياتها؟", reply_markup=markup)

async def confirm_delete_series(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    name = query.data.replace("confirm_del_ser_", "")
    
    if db.delete_series(name):
        await query.edit_message_text(f"تم حذف السلسلة '{name}' وجميع محتوياتها بنجاح.")
    else:
        await query.edit_message_text(f"فشل حذف السلسلة '{name}'.")
    
    await query.message.reply_text("تم العوده للقائمة الرئيسية.", reply_markup=get_main_menu_keyboard())

# --- Admin: Move Content ---

async def move_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("غير مصرح.")
        return ConversationHandler.END
    
    keyboard = [
        [InlineKeyboardButton("📄 مادة (Resource)", callback_data="move_type_res")],
        [InlineKeyboardButton("📚 سلسلة (Series)", callback_data="move_type_ser")],
        [InlineKeyboardButton("📁 قسم (Category)", callback_data="move_type_cat")],
        [InlineKeyboardButton("❌ إلغاء", callback_data="cancel_conv")]
    ]
    markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("ماذا تريد أن تنقل؟", reply_markup=markup)
    return MOVE_TYPE

async def receive_move_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    move_type = query.data.replace("move_type_", "")
    context.user_data['move_type'] = move_type
    
    markup = get_move_find_markup(move_type, None)
    await query.edit_message_text("تصفح الاقسام لاختيار العنصر الذي تريد نقله:", reply_markup=markup)
    return MOVE_ITEM_SELECT

async def receive_move_item_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    move_type = context.user_data['move_type']
    
    if data.startswith("mfind_nav_"):
        # Navigation
        category_name = data.replace("mfind_nav_", "")
        if category_name == "root":
            category_name = None
            text = "تصفح الاقسام لاختيار العنصر:"
        else:
            text = f"القسم الحالي: {category_name}\nاختر العنصر المراد نقله أو ادخل لقسم فرعي:"
            
        markup = get_move_find_markup(move_type, category_name)
        await query.edit_message_text(text, reply_markup=markup)
        return MOVE_ITEM_SELECT
        
    elif data.startswith("mfind_sel_"):
        # Selection
        item_name = data.replace("mfind_sel_", "")
        context.user_data['move_item_name'] = item_name
        
        # Show target category selection
        markup = get_category_selection_markup(None)
        await query.edit_message_text(f"اختر القسم الجديد لـ '{item_name}':", reply_markup=markup)
        return MOVE_TARGET_CAT

async def receive_move_target_cat_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data.startswith("ser_nav_"):
        # Navigation
        category_name = data.replace("ser_nav_", "")
        if category_name == "root":
            category_name = None
            text = "اختر القسم الجديد (أو تنقل بين الأقسام):"
        else:
            text = f"القسم الحالي: {category_name}\nيمكنك النقل هنا أو الدخول لقسم فرعي:"
            
        markup = get_category_selection_markup(category_name)
        await query.edit_message_text(text, reply_markup=markup)
        return MOVE_TARGET_CAT
        
    elif data.startswith("ser_sel_"):
        # Selection
        target_cat = data.replace("ser_sel_", "")
        if target_cat == "none":
            target_cat = None
        
        move_type = context.user_data['move_type']
        item_name = context.user_data['move_item_name']
        
        success = False
        if move_type == 'res':
            # For resources, 'category' is NOT NULL
            # If target_cat is None (Root), we use "None" to represent root
            new_cat_val = target_cat if target_cat else "None"
            success = db.update_resource_category(item_name, new_cat_val)
        elif move_type == 'ser':
            success = db.update_series_category(item_name, target_cat)
        elif move_type == 'cat':
            if item_name == target_cat:
                 await query.edit_message_text("لا يمكن نقل القسم إلى نفسه!")
                 return ConversationHandler.END
            success = db.update_category_parent(item_name, target_cat)
            
        if success:
            cat_text = target_cat if target_cat else "الرئيسي"
            await query.edit_message_text(f"تم نقل '{item_name}' إلى '{cat_text}' بنجاح.")
            await query.message.reply_text("تم العوده للقائمة الرئيسية.", reply_markup=get_main_menu_keyboard())
        else:
            await query.edit_message_text(f"فشل نقل '{item_name}'.")
            await query.message.reply_text("تم العوده للقائمة الرئيسية.", reply_markup=get_main_menu_keyboard())
            
        return ConversationHandler.END

# --- Admin: Rename Content ---

async def rename_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("غير مصرح.")
        return ConversationHandler.END
    
    keyboard = [
        [InlineKeyboardButton("📁 قسم (Category)", callback_data="rename_type_cat")],
        [InlineKeyboardButton("📚 سلسلة (Series)", callback_data="rename_type_ser")],
        [InlineKeyboardButton("📄 مادة (Resource)", callback_data="rename_type_res")],
        [InlineKeyboardButton("🔢 مادة داخل سلسلة (Series Item)", callback_data="rename_type_sitem")],
        [InlineKeyboardButton("❌ إلغاء", callback_data="cancel_conv")]
    ]
    markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("ماذا تريد أن تعدل اسمه؟", reply_markup=markup)
    return RENAME_TYPE

async def receive_rename_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    rtype = query.data.replace("rename_type_", "")
    context.user_data['rename_type'] = rtype
    
    markup = get_rename_find_markup(rtype, None)
    await query.edit_message_text("تصفح الاقسام لاختيار العنصر الذي تريد تعديل اسمه:", reply_markup=markup)
    return RENAME_ITEM_SELECT

async def receive_rename_item_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    rtype = context.user_data['rename_type']
    
    if data.startswith("rfind_nav_"):
        # Navigation
        category_name = data.replace("rfind_nav_", "")
        if category_name == "root":
            category_name = None
            text = "تصفح الاقسام لاختيار العنصر:"
        else:
            text = f"القسم الحالي: {category_name}\nاختر العنصر المراد تعديله أو ادخل لقسم فرعي:"
            
        markup = get_rename_find_markup(rtype, category_name)
        await query.edit_message_text(text, reply_markup=markup)
        return RENAME_ITEM_SELECT
        
    elif data.startswith("rfind_pickser_"):
        # Picking a series to see its items
        series_name = data.replace("rfind_pickser_", "")
        context.user_data['rename_series_name'] = series_name
        markup = get_series_item_rename_markup(series_name)
        await query.edit_message_text(f"السلسلة: {series_name}\nاختر المادة المراد تعديل اسمها:", reply_markup=markup)
        return RENAME_ITEM_SELECT

    elif data.startswith("rfind_selsitem_"):
        # Selection of series item
        item_number = data.replace("rfind_selsitem_", "")
        context.user_data['rename_item_number'] = item_number
        await query.edit_message_text(f"أرسل الاسم الجديد للمادة رقم {item_number}:")
        return RENAME_NEW_NAME

    elif data.startswith("rfind_sel_"):
        # Selection
        item_name = data.replace("rfind_sel_", "")
        context.user_data['rename_old_name'] = item_name
        await query.edit_message_text(f"أرسل الاسم الجديد لـ '{item_name}':")
        return RENAME_NEW_NAME

async def receive_rename_new_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    new_name = update.message.text
    rtype = context.user_data['rename_type']
    
    success = False
    old_name = context.user_data.get('rename_old_name')
    
    if rtype == 'cat':
        if not is_valid_category_name(new_name):
             await update.message.reply_text("اسم القسم غير صالح.")
             return RENAME_NEW_NAME
        success = db.rename_category(old_name, new_name)
    elif rtype == 'ser':
        success = db.rename_series(old_name, new_name)
    elif rtype == 'res':
        success = db.rename_resource(old_name, new_name)
    elif rtype == 'sitem':
        series_name = context.user_data['rename_series_name']
        item_number = int(context.user_data['rename_item_number'])
        success = db.rename_series_item(series_name, item_number, new_name)
        old_name = f"المادة رقم {item_number} في سلسلة {series_name}"

    if success:
        await update.message.reply_text(f"تم تعديل الاسم بنجاح إلى: {new_name}", reply_markup=get_main_menu_keyboard())
    else:
        await update.message.reply_text("فشل تعديل الاسم. ربما الاسم الجديد موجود بالفعل.", reply_markup=get_main_menu_keyboard())
        
    return ConversationHandler.END
