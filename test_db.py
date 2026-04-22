import sys
sys.path.append('.')
import database as db

# test logic
col_map = {
    "FYP 1 SV": "fyp_sv_id",
    "FYP 2 SV": "fyp_sv_id",
    "FYP 1 Panel": "fyp1_panel_id",
    "FYP 2 Panel": "fyp2_panel_id",
    "LI Uni SV": "li_sv_id",
    "Email": "email",
    "FYP Title": "fyp_title",
    "FYP 1 Marks": "fyp1_marks",
    "FYP 2 Marks": "fyp2_marks",
    "LI Marks": "li_marks",
    "Lapor Diri": "form_lapor_diri",
    "Aku Janji": "form_aku_janji",
    "Status": "status"
}

field = "LI Marks"
value = 85.0
db_col = col_map.get(field, field.lower().replace(" ", "_"))

if "marks" in db_col:
    # Here is what database.py does:
    val = float(value) if value and value != "-" else None
    print(f"db_col={db_col}, value={value}, val={val}")
