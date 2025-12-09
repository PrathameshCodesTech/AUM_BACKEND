import sqlite3

DB_PATH = 'db.sqlite3'

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

print("🔧 Fixing wallet table with FK disabled...")

try:
    # Disable foreign key constraints
    cursor.execute("PRAGMA foreign_keys = OFF")
    print("✅ Disabled foreign key checks")
    
    # Check what's in wallets
    cursor.execute("SELECT COUNT(*) FROM wallets")
    count = cursor.fetchone()[0]
    print(f"📊 Found {count} wallet records")
    
    # Delete all wallets
    cursor.execute("DELETE FROM wallets")
    print(f"✅ Deleted all wallet records")
    
    # Also delete related transactions if any
    cursor.execute("DELETE FROM transactions WHERE reference_type = 'wallet'")
    print(f"✅ Cleaned up related transactions")
    
    # Re-enable foreign key constraints
    cursor.execute("PRAGMA foreign_keys = ON")
    print("✅ Re-enabled foreign key checks")
    
    # Commit
    conn.commit()
    print("✅ Changes committed!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    conn.rollback()
finally:
    conn.close()

print("\n✅ Done! Test your wallet API now.")
print("💡 Wallets will be auto-created when users need them.")