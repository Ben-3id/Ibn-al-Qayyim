import sqlite3
import datetime
import os

# Allow overriding DB location for volume persistence
DATA_DIR = os.getenv("DATA_DIR", ".")
DB_NAME = os.path.join(DATA_DIR, "educational_bot.db")

def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    c = conn.cursor()
    c.executescript('''
        CREATE TABLE IF NOT EXISTS resources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            type TEXT NOT NULL,
            category TEXT NOT NULL,
            description TEXT,
            content_value TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS categories (
            name TEXT PRIMARY KEY,
            parent_name TEXT
        );
    ''')
    
    # Migration for existing DBs that might lack parent_name
    try:
        c = conn.cursor()
        c.execute("ALTER TABLE categories ADD COLUMN parent_name TEXT")
        conn.commit()
    except Exception:
        pass # Column likely exists or table was just created

    # Migration for forwarding (message_id, source_chat_id)
    try:
        c = conn.cursor()
        c.execute("ALTER TABLE resources ADD COLUMN message_id INTEGER")
        c.execute("ALTER TABLE resources ADD COLUMN source_chat_id INTEGER")
        conn.commit()
    except Exception:
        pass # Columns likely exist

    conn.commit()
    conn.close()

def add_resource(title, type_val, category, description, value, message_id=None, source_chat_id=None):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        INSERT INTO resources (title, type, category, description, content_value, message_id, source_chat_id)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (title, type_val, category, description, value, message_id, source_chat_id))
    conn.commit()
    conn.close()

def delete_resource(title):
    conn = get_connection()
    c = conn.cursor()
    c.execute('DELETE FROM resources WHERE title = ?', (title,))
    rows = c.rowcount
    conn.commit()
    conn.close()
    return rows > 0

def get_categories(parent=None):
    conn = get_connection()
    c = conn.cursor()
    # Union of used categories and explicitly defined categories
    # Note: 'resources' table doesn't have parent info, so we rely on 'categories' table for hierarchy.
    # If a category is in 'resources' but not in 'categories', we treat it as top-level (parent IS NULL).
    
    # Complex query to merge both data sources:
    # 1. Categories from 'categories' table matching parent
    # 2. Categories from 'resources' NOT in 'categories' table (only if we are asking for root i.e. parent=None)
    
    query = "SELECT name FROM categories WHERE "
    params = []
    if parent:
         query += "parent_name = ?"
         params.append(parent)
    else:
         query += "parent_name IS NULL"
    
    if parent is None:
        query += """
        UNION
        SELECT DISTINCT category FROM resources 
        WHERE category NOT IN (SELECT name FROM categories)
        """
        
    query += " ORDER BY 1"
    
    c.execute(query, tuple(params))
    categories = [row[0] for row in c.fetchall()]
    conn.close()
    return categories

def add_category(name, parent=None):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute('INSERT OR IGNORE INTO categories (name, parent_name) VALUES (?, ?)', (name, parent))
        # If it existed, maybe update parent? For now, ignore collision.
        conn.commit()
    finally:
        conn.close()
    return True

def get_resources_by_category(category):
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM resources WHERE category = ? ORDER BY title', (category,))
    results = [dict(row) for row in c.fetchall()]
    conn.close()
    return results

def search_resources(keyword):
    conn = get_connection()
    c = conn.cursor()
    search_term = f"%{keyword}%"
    c.execute('''
        SELECT * FROM resources 
        WHERE title LIKE ? OR description LIKE ? OR category LIKE ?
    ''', (search_term, search_term, search_term))
    results = [dict(row) for row in c.fetchall()]
    conn.close()
    return results

def get_resource_by_title(title):
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM resources WHERE title = ?', (title,))
    row = c.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None

def delete_category(name):
    """Recursively delete a category, its subcategories, and its resources."""
    conn = get_connection()
    c = conn.cursor()
    
    # 1. Find and delete subcategories recursively
    c.execute('SELECT name FROM categories WHERE parent_name = ?', (name,))
    subcategories = [row[0] for row in c.fetchall()]
    for sub in subcategories:
        delete_category(sub)
        
    # 2. Delete resources in this category
    c.execute('DELETE FROM resources WHERE category = ?', (name,))
    
    # 3. Delete the category itself
    c.execute('DELETE FROM categories WHERE name = ?', (name,))
    
    conn.commit()
    conn.close()
    return True
