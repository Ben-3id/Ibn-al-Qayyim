import datetime
import os
from supabase import create_client, Client
from config import SUPABASE_URL, SUPABASE_KEY

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def init_db():
    """
    In Supabase, we don't 'init' tables via code like SQLite.
    The user should run the provided SQL script in the Supabase dashboard.
    This function remains as a placeholder to avoid breaking main.py.
    """
    print("Supabase client initialized. Ensure tables are created in the dashboard.")
    pass

# --- Resource Functions ---

def add_resource(title, type_val, category, description, value, message_id=None, source_chat_id=None):
    data = {
        "title": title,
        "type": type_val,
        "category": category,
        "description": description,
        "content_value": value,
        "message_id": message_id,
        "source_chat_id": source_chat_id
    }
    supabase.table("resources").insert(data).execute()

def delete_resource(title):
    response = supabase.table("resources").delete().eq("title", title).execute()
    return len(response.data) > 0

def get_resources_by_category(category):
    if category is None or category == "None" or category == "":
        response = supabase.table("resources").select("*").or_("category.is.null,category.eq.None,category.eq.''").order("title").execute()
    else:
        response = supabase.table("resources").select("*").eq("category", category).order("title").execute()
    return response.data

def get_all_resources():
    response = supabase.table("resources").select("*").order("title").execute()
    return response.data

def update_resource_category(title, new_category):
    response = supabase.table("resources").update({"category": new_category}).eq("title", title).execute()
    return len(response.data) > 0

def search_resources(keyword):
    search_term = f"%{keyword}%"
    response = supabase.table("resources").select("*").or_(f"title.ilike.{search_term},description.ilike.{search_term},category.ilike.{search_term}").execute()
    return response.data

def get_resource_by_title(title):
    response = supabase.table("resources").select("*").eq("title", title).execute()
    return response.data[0] if response.data else None

def rename_resource(old_title, new_title):
    try:
        response = supabase.table("resources").update({"title": new_title}).eq("title", old_title).execute()
        return len(response.data) > 0
    except Exception:
        return False

# --- Category Functions ---

def add_category(name, parent_name=None):
    try:
        data = {"name": name, "parent_name": parent_name}
        supabase.table("categories").insert(data).execute()
        return True
    except Exception:
        return False

def get_categories(parent=None):
    # Get defined categories
    if parent:
        resp = supabase.table("categories").select("name").eq("parent_name", parent).execute()
    else:
        resp = supabase.table("categories").select("name").is_("parent_name", "null").execute()
    
    cats = [row["name"] for row in resp.data]
    
    # If root, also include categories from resources that aren't in categories table
    if parent is None:
        # Note: Supabase doesn't easily support NOT IN with subqueries in a single call,
        # but we can fetch them separately or rely on categories table existence.
        # For simplicity and correctness with hierarchy, we'll mostly rely on categories table.
        # But let's try to match SQLite's UNION if possible.
        res_resp = supabase.table("resources").select("category").neq("category", "None").neq("category", "").execute()
        res_cats = set(row["category"] for row in res_resp.data if row["category"])
        
        for c in res_cats:
            if c not in cats:
                # Check if it has a parent in categories
                p_resp = supabase.table("categories").select("name").eq("name", c).execute()
                if not p_resp.data:
                    cats.append(c)
    
    cats.sort()
    return cats

def get_category_info(name):
    response = supabase.table("categories").select("*").eq("name", name).execute()
    return response.data[0] if response.data else None

def update_category_parent(name, new_parent):
    response = supabase.table("categories").update({"parent_name": new_parent}).eq("name", name).execute()
    return len(response.data) > 0

def delete_category(name):
    # Recursive delete is harder in SDK without a stored proc, 
    # but we can do it manually or rely on ON DELETE CASCADE in Supabase SQL.
    # We set up ON DELETE SET NULL for parent_name, but resources and series need cleanup.
    
    # 1. Delete resources in this category
    supabase.table("resources").delete().eq("category", name).execute()
    
    # 2. Delete series in this category
    supabase.table("series").delete().eq("category", name).execute()
    
    # 3. Subcategories: if we want recursive delete, we must fetch them.
    sub_resp = supabase.table("categories").select("name").eq("parent_name", name).execute()
    for sub in sub_resp.data:
        delete_category(sub['name'])
        
    # 4. Delete the category itself
    supabase.table("categories").delete().eq("name", name).execute()
    return True

def rename_category(old_name, new_name):
    try:
        # SQL handles foreign keys if set up correctly.
        # Here we manually update references if needed, but Supabase/Postgres 
        # usually needs ON UPDATE CASCADE. Our migration script didn't include it.
        # Let's do it via API for safety.
        
        # 1. Update the category itself
        supabase.table("categories").update({"name": new_name}).eq("name", old_name).execute()
        # 2. Update parent_name references
        supabase.table("categories").update({"parent_name": new_name}).eq("parent_name", old_name).execute()
        # 3. Update resources
        supabase.table("resources").update({"category": new_name}).eq("category", old_name).execute()
        # 4. Update series
        supabase.table("series").update({"category": new_name}).eq("category", old_name).execute()
        
        return True
    except Exception:
        return False

# --- Settings Functions ---

def get_setting(key, default=None):
    response = supabase.table("settings").select("value").eq("key", key).execute()
    if response.data:
        return response.data[0]["value"]
    return default

def set_setting(key, value):
    # Upsert logic
    supabase.table("settings").upsert({"key": key, "value": value}).execute()

# --- Series Functions ---

def add_series(name, description=None, category=None):
    try:
        data = {"name": name, "description": description, "category": category}
        supabase.table("series").insert(data).execute()
        return True
    except Exception:
        return False

def update_series_category(name, new_category):
    response = supabase.table("series").update({"category": new_category}).eq("name", name).execute()
    return len(response.data) > 0

def get_all_series():
    response = supabase.table("series").select("*").order("name").execute()
    return response.data

def get_series_by_category(category):
    if category is None or category == "None" or category == "":
        response = supabase.table("series").select("*").or_("category.is.null,category.eq.None,category.eq.''").order("name").execute()
    else:
        response = supabase.table("series").select("*").eq("category", category).order("name").execute()
    return response.data

def get_series_by_name(name):
    response = supabase.table("series").select("*").eq("name", name).execute()
    return response.data[0] if response.data else None

def delete_series(name):
    response = supabase.table("series").delete().eq("name", name).execute()
    return len(response.data) > 0

def rename_series(old_name, new_name):
    try:
        response = supabase.table("series").update({"name": new_name}).eq("name", old_name).execute()
        return len(response.data) > 0
    except Exception:
        return False

# --- Series Item Functions ---

def add_series_item(series_name, item_number, title, type_val, description, content_value, message_id=None, source_chat_id=None):
    series = get_series_by_name(series_name)
    if not series:
        return False
    
    try:
        data = {
            "series_id": series["id"],
            "item_number": item_number,
            "title": title,
            "type": type_val,
            "description": description,
            "content_value": content_value,
            "message_id": message_id,
            "source_chat_id": source_chat_id
        }
        supabase.table("series_items").insert(data).execute()
        return True
    except Exception:
        return False

def get_series_items(series_name):
    series = get_series_by_name(series_name)
    if not series:
        return []
    
    response = supabase.table("series_items").select("*").eq("series_id", series["id"]).order("item_number").execute()
    return response.data

def delete_series_item(series_name, item_number):
    series = get_series_by_name(series_name)
    if not series:
        return False
    
    response = supabase.table("series_items").delete().eq("series_id", series["id"]).eq("item_number", item_number).execute()
    return len(response.data) > 0

def rename_series_item(series_name, item_number, new_title):
    series = get_series_by_name(series_name)
    if not series:
        return False
    
    try:
        response = supabase.table("series_items").update({"title": new_title}).eq("series_id", series["id"]).eq("item_number", item_number).execute()
        return len(response.data) > 0
    except Exception:
        return False
