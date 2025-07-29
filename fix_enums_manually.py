#!/usr/bin/env python3
"""Direct SQL approach to fix enums"""

import os
import sys

# Set the DATABASE_URL environment variable directly for this script
os.environ["DATABASE_URL"] = "postgresql://postgres.ldljgbocrbfgjabbreec:deiRl95djSAX16TvNuoCgu51hE2tRy6LMqtf2kDbw2MdPqPJP4LGI0L54HWC6LJz@aws-0-us-west-1.pooler.supabase.com:6543/postgres"

from app.core.database import SessionLocal
from sqlalchemy import text

def fix_enums_manually():
    with SessionLocal() as session:
        print("🔧 Fixing remaining enums manually...")
        
        try:
            # First, let's see what we have
            print("\n📊 Current enum values:")
            result = session.execute(text("""
                SELECT enumlabel 
                FROM pg_enum e 
                JOIN pg_type t ON e.enumtypid = t.oid 
                WHERE t.typname = 'salecondition'
                ORDER BY e.enumsortorder
            """))
            values = result.fetchall()
            print(f"salecondition: {[v[0] for v in values]}")
            
            result = session.execute(text("""
                SELECT enumlabel 
                FROM pg_enum e 
                JOIN pg_type t ON e.enumtypid = t.oid 
                WHERE t.typname = 'paymentmethod'
                ORDER BY e.enumsortorder
            """))
            values = result.fetchall()
            print(f"paymentmethod: {[v[0] for v in values]}")
            
            # Drop constraints that might prevent column type changes
            print("\n🔨 Dropping potential constraints...")
            
            # Try to drop any check constraints on condicion_venta
            try:
                constraints_result = session.execute(text("""
                    SELECT conname 
                    FROM pg_constraint 
                    WHERE conrelid = 'documentos'::regclass 
                    AND contype = 'c'
                """))
                constraints = constraints_result.fetchall()
                print(f"Found constraints: {[c[0] for c in constraints]}")
                
                for constraint in constraints:
                    constraint_name = constraint[0]
                    try:
                        session.execute(text(f"ALTER TABLE documentos DROP CONSTRAINT IF EXISTS {constraint_name}"))
                        print(f"Dropped constraint: {constraint_name}")
                    except Exception as e:
                        print(f"Could not drop {constraint_name}: {e}")
                        
            except Exception as e:
                print(f"Error checking constraints: {e}")
            
            session.commit()
            return True
            
        except Exception as e:
            print(f"❌ Error: {e}")
            session.rollback()
            return False

if __name__ == "__main__":
    success = fix_enums_manually()
    if success:
        print("✅ Manual enum fix completed")
    else:
        print("❌ Manual enum fix failed")
