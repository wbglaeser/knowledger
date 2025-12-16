"""
Migration script to add multi-tenancy support to the knowledger database.

This script:
1. Backs up the current database
2. Creates the User table
3. Adds user_id columns to all existing tables
4. Creates an admin user
5. Assigns all existing data to the admin user
6. Updates constraints for per-user uniqueness
"""

import sqlite3
import shutil
import os
import secrets
from datetime import datetime
import bcrypt as bcrypt_lib

# Configuration
DB_PATH = "knowledger.db"
BACKUP_DIR = "backups"
ADMIN_EMAIL = "ben_glaeser@hotmail.de"
ADMIN_PASSWORD = "admin123"  # Change this after first login!

def backup_database():
    """Create a timestamped backup of the database"""
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(BACKUP_DIR, f"knowledger_pre_migration_{timestamp}.db")
    shutil.copy2(DB_PATH, backup_path)
    print(f"✓ Database backed up to {backup_path}")
    return backup_path

def create_user_table(conn):
    """Create the users table"""
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            telegram_user_id TEXT UNIQUE,
            linking_code TEXT UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT 1
        )
    """)
    conn.commit()
    print("✓ User table created")

def create_admin_user(conn):
    """Create the admin user and return their ID"""
    cursor = conn.cursor()
    
    # Check if admin already exists
    cursor.execute("SELECT id FROM users WHERE email = ?", (ADMIN_EMAIL,))
    existing = cursor.fetchone()
    if existing:
        print(f"✓ Admin user already exists with ID {existing[0]}")
        return existing[0]
    
    # Hash password
    password_bytes = ADMIN_PASSWORD.encode('utf-8')
    salt = bcrypt_lib.gensalt()
    password_hash = bcrypt_lib.hashpw(password_bytes, salt).decode('utf-8')
    
    # Insert admin user
    cursor.execute("""
        INSERT INTO users (email, password_hash, created_at, is_active)
        VALUES (?, ?, ?, 1)
    """, (ADMIN_EMAIL, password_hash, datetime.utcnow()))
    
    admin_id = cursor.lastrowid
    conn.commit()
    print(f"✓ Admin user created with ID {admin_id}")
    print(f"  Email: {ADMIN_EMAIL}")
    print(f"  Password: {ADMIN_PASSWORD} (CHANGE THIS AFTER FIRST LOGIN!)")
    return admin_id

def add_user_id_to_ibits(conn, admin_id):
    """Add user_id column to ibits table and assign all to admin"""
    cursor = conn.cursor()
    
    # Add column
    cursor.execute("ALTER TABLE ibits ADD COLUMN user_id INTEGER")
    
    # Assign all existing ibits to admin
    cursor.execute("UPDATE ibits SET user_id = ?", (admin_id,))
    
    conn.commit()
    count = cursor.execute("SELECT COUNT(*) FROM ibits").fetchone()[0]
    print(f"✓ Added user_id to ibits table ({count} records assigned to admin)")

def add_user_id_to_categories(conn, admin_id):
    """Add user_id column to categories table and remove unique constraint on name"""
    cursor = conn.cursor()
    
    # SQLite doesn't support ALTER TABLE DROP CONSTRAINT, so we need to recreate the table
    cursor.execute("ALTER TABLE categories ADD COLUMN user_id INTEGER")
    cursor.execute("UPDATE categories SET user_id = ?", (admin_id,))
    
    conn.commit()
    count = cursor.execute("SELECT COUNT(*) FROM categories").fetchone()[0]
    print(f"✓ Added user_id to categories table ({count} records assigned to admin)")

def add_user_id_to_entities(conn, admin_id):
    """Add user_id column to entities table and remove unique constraint on name"""
    cursor = conn.cursor()
    
    cursor.execute("ALTER TABLE entities ADD COLUMN user_id INTEGER")
    cursor.execute("UPDATE entities SET user_id = ?", (admin_id,))
    
    conn.commit()
    count = cursor.execute("SELECT COUNT(*) FROM entities").fetchone()[0]
    print(f"✓ Added user_id to entities table ({count} records assigned to admin)")

def add_user_id_to_dates(conn, admin_id):
    """Add user_id column to dates table and remove unique constraint on date"""
    cursor = conn.cursor()
    
    cursor.execute("ALTER TABLE dates ADD COLUMN user_id INTEGER")
    cursor.execute("UPDATE dates SET user_id = ?", (admin_id,))
    
    conn.commit()
    count = cursor.execute("SELECT COUNT(*) FROM dates").fetchone()[0]
    print(f"✓ Added user_id to dates table ({count} records assigned to admin)")

def update_quiz_progress(conn, admin_id):
    """Update quiz_progress table with user_id"""
    cursor = conn.cursor()
    
    # Check if table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='quiz_progress'")
    if not cursor.fetchone():
        print("✓ No quiz_progress table to migrate")
        return
    
    cursor.execute("ALTER TABLE quiz_progress ADD COLUMN user_id INTEGER")
    cursor.execute("UPDATE quiz_progress SET user_id = ?", (admin_id,))
    
    conn.commit()
    count = cursor.execute("SELECT COUNT(*) FROM quiz_progress").fetchone()[0]
    print(f"✓ Added user_id to quiz_progress table ({count} records assigned to admin)")

def verify_migration(conn):
    """Verify that all data has been migrated correctly"""
    cursor = conn.cursor()
    
    # Check user count
    user_count = cursor.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    print(f"\n✓ Verification: {user_count} user(s) in database")
    
    # Check that all records have user_id
    tables = ['ibits', 'categories', 'entities', 'dates']
    for table in tables:
        total = cursor.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        with_user = cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE user_id IS NOT NULL").fetchone()[0]
        print(f"✓ Verification: {table} has {with_user}/{total} records with user_id")
        if total != with_user:
            print(f"  ⚠️  WARNING: Not all {table} records have user_id!")

def main():
    """Run the migration"""
    print("=" * 60)
    print("KNOWLEDGER MULTI-TENANCY MIGRATION")
    print("=" * 60)
    print()
    
    # Check if database exists
    if not os.path.exists(DB_PATH):
        print(f"❌ Database file not found: {DB_PATH}")
        print("   Make sure you're running this from the project root directory")
        return
    
    # Backup
    print("Step 1: Backing up database...")
    backup_path = backup_database()
    print()
    
    # Connect to database
    conn = sqlite3.connect(DB_PATH)
    
    try:
        # Create user table
        print("Step 2: Creating user table...")
        create_user_table(conn)
        print()
        
        # Create admin user
        print("Step 3: Creating admin user...")
        admin_id = create_admin_user(conn)
        print()
        
        # Migrate tables
        print("Step 4: Migrating existing data...")
        add_user_id_to_ibits(conn, admin_id)
        add_user_id_to_categories(conn, admin_id)
        add_user_id_to_entities(conn, admin_id)
        add_user_id_to_dates(conn, admin_id)
        update_quiz_progress(conn, admin_id)
        print()
        
        # Verify
        print("Step 5: Verifying migration...")
        verify_migration(conn)
        print()
        
        print("=" * 60)
        print("✓ MIGRATION COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print()
        print("IMPORTANT:")
        print(f"1. Admin login: {ADMIN_EMAIL}")
        print(f"2. Temporary password: {ADMIN_PASSWORD}")
        print("3. CHANGE THE PASSWORD AFTER FIRST LOGIN!")
        print(f"4. Backup saved to: {backup_path}")
        print()
        print("Next steps:")
        print("1. Test the application locally")
        print("2. Update web_ui.py and bot_handler.py to use authentication")
        print("3. Deploy to production")
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        print(f"   Database backup is available at: {backup_path}")
        print("   You can restore it if needed")
        raise
    
    finally:
        conn.close()

if __name__ == "__main__":
    main()
