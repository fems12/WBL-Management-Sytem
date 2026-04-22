import psycopg2

URL = "postgresql://postgres.urxhdmldesbjkirwxuls:Taktahu1278@aws-1-ap-south-1.pooler.supabase.com:6543/postgres"

def alter_columns():
    try:
        conn = psycopg2.connect(URL)
        cur = conn.cursor()
        print("Connected.")
        
        # Alter all marks columns to numeric(5,2) so they can store values like 100.00 or 85.50
        alter_query = """
        ALTER TABLE students
        ALTER COLUMN fyp1_marks TYPE numeric USING fyp1_marks::numeric,
        ALTER COLUMN fyp2_marks TYPE numeric USING fyp2_marks::numeric,
        ALTER COLUMN li_marks TYPE numeric USING li_marks::numeric;
        """
        cur.execute(alter_query)
        conn.commit()
        print("Altered columns successfully!")
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

alter_columns()
