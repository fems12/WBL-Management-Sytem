import sys
sys.path.append('.')
import database as db

# Manually update a student with INT
students = db.get_students()
if not students.empty:
    test_matrix = students.iloc[0]['Matrix_No']
    print(f"Testing on {test_matrix}...")
    success, msg = db.update_student_field(test_matrix, "LI Marks", 85)
    print("Testing 85 (int):", success, msg)
    
    # Try with string that contains decimal
    success, msg = db.update_student_field(test_matrix, "FYP 1 Marks", "85")
    print("Testing '85' (str) on FYP 1:", success, msg)
else:
    print("No students.")
