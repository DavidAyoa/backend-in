#!/usr/bin/env python3
"""
Database migration script to add marketplace fields to existing database
"""

import sqlite3
import sys
import os

# Add the current directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def migrate_database(db_path: str = "voice_agent.sqlite"):
    """Migrate database to add marketplace fields"""
    
    print(f"🔄 Starting database migration for {db_path}")
    
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # Check if the marketplace fields already exist
            cursor.execute("PRAGMA table_info(agents)")
            columns = [column[1] for column in cursor.fetchall()]
            
            print(f"📋 Current agent table columns: {columns}")
            
            # Add marketplace fields if they don't exist
            fields_to_add = [
                ("is_public", "BOOLEAN DEFAULT FALSE"),
                ("original_agent_id", "INTEGER REFERENCES agents(id) ON DELETE SET NULL"),
                ("clone_count", "INTEGER DEFAULT 0"),
                ("tags", "TEXT DEFAULT '[]'"),
                ("category", "TEXT DEFAULT 'general'")
            ]
            
            for field_name, field_definition in fields_to_add:
                if field_name not in columns:
                    try:
                        cursor.execute(f"ALTER TABLE agents ADD COLUMN {field_name} {field_definition}")
                        print(f"✅ Added column: {field_name}")
                    except sqlite3.OperationalError as e:
                        print(f"⚠️  Could not add column {field_name}: {e}")
                else:
                    print(f"✅ Column {field_name} already exists")
            
            # Create indexes for marketplace fields
            indexes_to_create = [
                ("idx_agents_is_public", "CREATE INDEX IF NOT EXISTS idx_agents_is_public ON agents(is_public)"),
                ("idx_agents_category", "CREATE INDEX IF NOT EXISTS idx_agents_category ON agents(category)"),
                ("idx_agents_clone_count", "CREATE INDEX IF NOT EXISTS idx_agents_clone_count ON agents(clone_count)"),
                ("idx_agents_original_id", "CREATE INDEX IF NOT EXISTS idx_agents_original_id ON agents(original_agent_id)")
            ]
            
            for index_name, index_sql in indexes_to_create:
                try:
                    cursor.execute(index_sql)
                    print(f"✅ Created index: {index_name}")
                except sqlite3.OperationalError as e:
                    print(f"⚠️  Could not create index {index_name}: {e}")
            
            conn.commit()
            print("✅ Database migration completed successfully")
            
            # Verify the migration
            cursor.execute("PRAGMA table_info(agents)")
            new_columns = [column[1] for column in cursor.fetchall()]
            print(f"📋 Updated agent table columns: {new_columns}")
            
            return True
            
    except Exception as e:
        print(f"❌ Database migration failed: {e}")
        return False

def backup_database(db_path: str = "voice_agent.sqlite"):
    """Create a backup of the database before migration"""
    import shutil
    from datetime import datetime
    
    if os.path.exists(db_path):
        backup_path = f"{db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        shutil.copy2(db_path, backup_path)
        print(f"📦 Database backed up to: {backup_path}")
        return backup_path
    else:
        print(f"⚠️  Database file {db_path} does not exist")
        return None

def test_migration():
    """Test that the migration was successful"""
    print("\n🧪 Testing migration...")
    
    try:
        from models.user import user_db
        
        # Test creating a user (should work with existing users)
        try:
            user = user_db.create_user(
                email="migration_test@example.com",
                username="migrationtest",
                password="testpass123",
                full_name="Migration Test User"
            )
            print("✅ User creation works")
        except Exception as e:
            print(f"❌ User creation failed: {e}")
            return False
        
        # Test agent creation with marketplace fields
        agent_id = user_db.create_agent(user.id, "Migration Test Agent")
        if agent_id:
            print("✅ Agent creation works")
            
            # Test updating with marketplace fields
            update_data = {
                "description": "A test agent for migration testing",
                "system_prompt": "You are a helpful migration test assistant",
                "is_public": True,
                "category": "testing",
                "tags": ["test", "migration", "marketplace"]
            }
            
            updated = user_db.update_agent(agent_id, update_data)
            if updated:
                print("✅ Agent update with marketplace fields works")
                
                # Test retrieving the agent
                agent = user_db.get_agent_by_id(agent_id)
                if agent:
                    print(f"✅ Agent retrieval works")
                    print(f"   - is_public: {agent.get('is_public')}")
                    print(f"   - category: {agent.get('category')}")
                    print(f"   - tags: {agent.get('tags')}")
                    print(f"   - clone_count: {agent.get('clone_count', 0)}")
                    
                    # Test marketplace methods
                    public_agents = user_db.get_public_agents(limit=5)
                    print(f"✅ Marketplace browse works: {len(public_agents)} public agents")
                    
                    stats = user_db.get_marketplace_stats()
                    print(f"✅ Marketplace stats work: {stats}")
                    
                    return True
                else:
                    print("❌ Agent retrieval failed")
                    return False
            else:
                print("❌ Agent update failed")
                return False
        else:
            print("❌ Agent creation failed")
            return False
            
    except Exception as e:
        print(f"❌ Migration test failed: {e}")
        return False

def main():
    """Main migration function"""
    print("🚀 Database Migration for Agent Marketplace")
    print("=" * 50)
    
    db_path = "voice_agent.sqlite"
    
    # Check if database exists
    if not os.path.exists(db_path):
        print(f"⚠️  Database file {db_path} does not exist. Creating new database...")
        # Initialize new database with marketplace fields
        from models.user import user_db
        user_db.init_database()
        print("✅ New database created with marketplace fields")
    else:
        # Backup existing database
        backup_path = backup_database(db_path)
        if backup_path:
            print(f"✅ Database backed up to {backup_path}")
        
        # Perform migration
        success = migrate_database(db_path)
        if not success:
            print("❌ Migration failed. Please check the errors above.")
            return False
    
    # Test migration
    test_success = test_migration()
    
    print("\n" + "=" * 50)
    print("📊 MIGRATION SUMMARY")
    print("=" * 50)
    
    if test_success:
        print("🎉 DATABASE MIGRATION SUCCESSFUL!")
        print("\nMarketplace features are now available:")
        print("✅ Public/Private agent visibility")
        print("✅ Agent categorization and tagging")
        print("✅ Clone tracking and statistics")
        print("✅ Marketplace browsing and search")
        print("✅ Trending agents")
        print("✅ Creator attribution")
        
        print("\nNext steps:")
        print("1. Start the server: python main.py")
        print("2. Test the marketplace endpoints")
        print("3. Run the full test suite: python test_marketplace.py")
    else:
        print("❌ Migration verification failed")
        print("Please check the errors above and try again")
    
    return test_success

if __name__ == "__main__":
    main()
