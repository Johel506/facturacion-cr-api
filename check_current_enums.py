#!/usr/bin/env python3
"""Check the current enum values"""

from app.core.database import SessionLocal
from sqlalchemy import text

def check_current_enums():
    with SessionLocal() as session:
        # Check documenttype enum values
        print("Current documenttype enum values:")
        result = session.execute(text("""
            SELECT enumlabel 
            FROM pg_enum e 
            JOIN pg_type t ON e.enumtypid = t.oid 
            WHERE t.typname = 'documenttype'
            ORDER BY e.enumsortorder
        """))
        values = result.fetchall()
        print(f"  Values: {[v[0] for v in values]}")
        
        # Check identificationtype enum values
        print("\nCurrent identificationtype enum values:")
        result = session.execute(text("""
            SELECT enumlabel 
            FROM pg_enum e 
            JOIN pg_type t ON e.enumtypid = t.oid 
            WHERE t.typname = 'identificationtype'
            ORDER BY e.enumsortorder
        """))
        values = result.fetchall()
        print(f"  Values: {[v[0] for v in values]}")

if __name__ == "__main__":
    check_current_enums()
