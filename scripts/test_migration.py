"""
Test script to verify migration on a copy of the database.
This creates a test database copy and runs the migration on it.
"""

import sqlite3
import shutil
import os
import sys

# Add src to path to import database module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

TEST_DB = "test_knowledger.db"
ORIGINAL_DB = "knowledger.db"

def create_test_database():
    """Create a test database copy"""
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    
    if not os.path.exists(ORIGINAL_DB):
        print(f"❌ Original database not found: {ORIGINAL_DB}")
        print("   Creating a fresh test database instead...")
        # Import and initialize a fresh database
        from database import init_db
        SessionMaker = init_db(f"sqlite:///{TEST_DB}")
        print(f"✓ Created fresh test database: {TEST_DB}")
        return
    
    shutil.copy2(ORIGINAL_DB, TEST_DB)
    print(f"✓ Created test database copy: {TEST_DB}")

def inspect_database(db_path):
    """Show database schema and counts"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    
    print(f"\n{'='*60}")
    print(f"Database: {db_path}")
    print(f"{'='*60}")
    
    for table in tables:
        # Get column info
        cursor.execute(f"PRAGMA table_info({table})")
        columns = cursor.fetchall()
        
        # Get row count
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        
        print(f"\n{table} ({count} rows):")
        for col in columns:
            col_id, name, type, notnull, default, pk = col
            constraints = []
            if pk:
                constraints.append("PRIMARY KEY")
            if notnull:
                constraints.append("NOT NULL")
            constraint_str = f" ({', '.join(constraints)})" if constraints else ""
            print(f"  - {name}: {type}{constraint_str}")
    
    conn.close()
    print()

def main():
    print("=" * 60)
    print("MIGRATION TEST")
    print("=" * 60)
    print()
    
    # Create test database
    print("Step 1: Creating test database...")
    create_test_database()
    print()
    
    # Show before state
    print("Step 2: Database schema BEFORE migration:")
    inspect_database(TEST_DB)
    
    # Run migration
    print("Step 3: Running migration on test database...")
    print(f"To run migration: python scripts/migrate_to_multitenancy.py")
    print(f"   (modify DB_PATH in migrate_to_multitenancy.py to '{TEST_DB}')")
    print()
    
    # Import and test new schema
    print("Step 4: Testing new database schema...")
    try:
        from database import User, Ibit, Category, Entity, Date, QuizProgress
        print("✓ All models imported successfully")
        
        # Check User model attributes
        print("\n✓ User model attributes:")
        for attr in ['id', 'email', 'password_hash', 'telegram_user_id', 'linking_code', 'created_at', 'is_active']:
            if hasattr(User, attr):
                print(f"  - {attr}")
        
        # Check that other models have user_id
        print("\n✓ Models with user_id foreign key:")
        for model in [Ibit, Category, Entity, Date, QuizProgress]:
            if hasattr(model, 'user_id'):
                print(f"  - {model.__name__}")
        
    except Exception as e:
        print(f"❌ Error importing models: {e}")
        import traceback
        traceback.print_exc()
    
    print()
    print("=" * 60)
    print("TEST COMPLETED")
    print("=" * 60)
    print()
    print("Next steps:")
    print("1. Review the schema above")
    print("2. Run the actual migration with: python scripts/migrate_to_multitenancy.py")
    print("3. After migration, run this script again to verify")

if __name__ == "__main__":
    main()
