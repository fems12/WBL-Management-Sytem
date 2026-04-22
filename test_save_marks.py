import sys
sys.path.append('.')
import database as db

# Manually update a student
students = db.get_students()
if not students.empty:
    test_matrix = students.iloc[0]['Matrix_No']
    print(f"Testing on {test_matrix}...")
    success, msg = db.update_student_field(test_matrix, "LI Marks", 85.0)
    print(success, msg)
    
    # Check if it was saved
    updated = db.get_students()
    saved_val = updated[updated['Matrix_No'] == test_matrix]['LI Marks'].iloc[0]
    print(f"Saved value: {saved_val}")
else:
    print("No students.")
