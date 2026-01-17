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
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        );
        CREATE TABLE IF NOT EXISTS series (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            description TEXT,
            category TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS series_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            series_id INTEGER NOT NULL,
            item_number INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            type TEXT NOT NULL,
            content_value TEXT NOT NULL,
            message_id INTEGER,
            source_chat_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (series_id) REFERENCES series(id) ON DELETE CASCADE,
            UNIQUE(series_id, item_number)
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

    # Migration for series category
    try:
        c = conn.cursor()
        c.execute("ALTER TABLE series ADD COLUMN category TEXT")
        conn.commit()
    except Exception:
        pass # Column likely exists

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
        AND category != "None" AND category != "" AND category IS NOT NULL
        """
        
    query += " ORDER BY 1"
    
    c.execute(query, tuple(params))
    categories = [row[0] for row in c.fetchall()]
    conn.close()
    return categories

def get_category_info(name):
    """Get category info including parent_name."""
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM categories WHERE name = ?', (name,))
    result = c.fetchone()
    conn.close()
    return dict(result) if result else None

    return True

def update_category_parent(name, new_parent):
    """Update the parent of a category."""
    conn = get_connection()
    c = conn.cursor()
    c.execute('UPDATE categories SET parent_name = ? WHERE name = ?', (new_parent, name))
    rows = c.rowcount
    conn.commit()
    conn.close()
    return rows > 0

def get_resources_by_category(category):
    conn = get_connection()
    c = conn.cursor()
    if category is None:
        c.execute('SELECT * FROM resources WHERE category IS NULL OR category = "None" OR category = "" ORDER BY title')
    else:
        c.execute('SELECT * FROM resources WHERE category = ? ORDER BY title', (category,))
    results = [dict(row) for row in c.fetchall()]
    conn.close()
    return results

def get_all_resources():
    """Get all resources."""
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM resources ORDER BY title')
    results = [dict(row) for row in c.fetchall()]
    conn.close()
    return results

def update_resource_category(title, new_category):
    """Update the category of a resource."""
    conn = get_connection()
    c = conn.cursor()
    c.execute('UPDATE resources SET category = ? WHERE title = ?', (new_category, title))
    rows = c.rowcount
    conn.commit()
    conn.close()
    return rows > 0

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

def get_setting(key, default=None):
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT value FROM settings WHERE key = ?', (key,))
    row = c.fetchone()
    conn.close()
    if row:
        return row[0]
    return default

def set_setting(key, value):
    conn = get_connection()
    c = conn.cursor()
    c.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)', (key, value))
    conn.commit()
    conn.close()

# --- Series Management Functions ---

def add_series(name, description=None, category=None):
    """Create a new series."""
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute('INSERT INTO series (name, description, category) VALUES (?, ?, ?)', (name, description, category))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False  # Series already exists
    finally:
        conn.close()

def update_series_category(name, new_category):
    """Update the category of a series."""
    conn = get_connection()
    c = conn.cursor()
    c.execute('UPDATE series SET category = ? WHERE name = ?', (new_category, name))
    rows = c.rowcount
    conn.commit()
    conn.close()
    return rows > 0

def get_all_series():
    """Get all series."""
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM series ORDER BY name')
    results = [dict(row) for row in c.fetchall()]
    conn.close()
    return results

def get_series_by_category(category):
    """Get all series in a specific category."""
    conn = get_connection()
    c = conn.cursor()
    if category is None:
        c.execute('SELECT * FROM series WHERE category IS NULL OR category = "None" OR category = "" ORDER BY name')
    else:
        c.execute('SELECT * FROM series WHERE category = ? ORDER BY name', (category,))
    results = [dict(row) for row in c.fetchall()]
    conn.close()
    return results

def get_series_by_name(name):
    """Get a series by name."""
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM series WHERE name = ?', (name,))
    row = c.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None

def delete_series(name):
    """Delete a series and all its items."""
    conn = get_connection()
    c = conn.cursor()
    c.execute('DELETE FROM series WHERE name = ?', (name,))
    rows = c.rowcount
    conn.commit()
    conn.close()
    return rows > 0

def add_series_item(series_name, item_number, title, type_val, description, content_value, message_id=None, source_chat_id=None):
    """Add an item to a series."""
    series = get_series_by_name(series_name)
    if not series:
        return False
    
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute('''
            INSERT INTO series_items (series_id, item_number, title, type, description, content_value, message_id, source_chat_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (series['id'], item_number, title, type_val, description, content_value, message_id, source_chat_id))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False  # Item number already exists in this series
    finally:
        conn.close()

def get_series_items(series_name):
    """Get all items in a series, ordered by item_number."""
    series = get_series_by_name(series_name)
    if not series:
        return []
    
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM series_items WHERE series_id = ? ORDER BY item_number', (series['id'],))
    results = [dict(row) for row in c.fetchall()]
    conn.close()
    return results

def delete_series_item(series_name, item_number):
    """Delete a specific item from a series."""
    series = get_series_by_name(series_name)
    if not series:
        return False
    
    conn = get_connection()
    c = conn.cursor()
    c.execute('DELETE FROM series_items WHERE series_id = ? AND item_number = ?', (series['id'], item_number))
    rows = c.rowcount
    conn.commit()
    conn.close()
    return rows > 0
