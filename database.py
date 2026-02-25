import streamlit as st
import pandas as pd
from datetime import datetime
from supabase_handler import get_supabase_client

# Initialize Supabase Client
sb = get_supabase_client()

def init_db():
    """Reserved for future use. Tables are now created via SQL Editor."""
    pass

# ===========================
# STUDENT FUNCTIONS
# ===========================

def get_students(include_archived=False):
    """Fetch students from Supabase."""
    global sb
    if sb is None:
        sb = get_supabase_client()
        if sb is None:
             st.error("🚨 Critical Error: Database connection failed. Please check Secrets.")
             return pd.DataFrame()

    try:
        # Fetch ALL data first to handle None/Null values safely in Python
        query = sb.table("students").select("*").order("matrix_number")
        # Removed .eq("is_archived", 0) from here to handle it in Pandas
        
        response = query.execute()
        data = response.data
        
        if not data:
            return pd.DataFrame()
            
        df = pd.DataFrame(data)
        
        # 1. Fetch Companies & Staff for Mapping
        companies_df = get_companies()
        staff_df = get_staff()
        
        # Prepare Lookups
        comp_map = {} # ID -> Name
        comp_states = {} # ID -> State
        staff_map = {} # ID -> Name
        
        # Prepare Lookups (Normalized to STRINGS for safety)
        comp_map = {} # ID (str) -> Name
        comp_states = {} # ID (str) -> State
        staff_map = {} # ID (str) -> Name
        
        if not companies_df.empty:
            cid_col = "id" if "id" in companies_df.columns else "company_id"
            cname_col = "Company Name" if "Company Name" in companies_df.columns else "name"
            cstate_col = "State" if "State" in companies_df.columns else "state"
            
            if cid_col in companies_df.columns:
                if cname_col in companies_df.columns:
                    # Force Keys to String
                    comp_map = {str(k): v for k, v in zip(companies_df[cid_col], companies_df[cname_col])}
                if cstate_col in companies_df.columns:
                    comp_states = {str(k): v for k, v in zip(companies_df[cid_col], companies_df[cstate_col])}

        if not staff_df.empty:
            sid_col = "staff_id" if "staff_id" in staff_df.columns else "id"
            # FIX: Check for staff_name as well
            sname_col = "staff_name" if "staff_name" in staff_df.columns else ("name" if "name" in staff_df.columns else "Name")
            
            if sid_col in staff_df.columns and sname_col in staff_df.columns:
                staff_map = {str(k): v for k, v in zip(staff_df[sid_col], staff_df[sname_col])}

        # Helper to safely map IDs (Everything to String)
        def safe_map(val, lookup):
            if pd.isna(val) or val == "" or val is None: return "-"
            # Try exact string match
            val_str = str(val).split('.')[0] # Handle "22.0" -> "22" string
            return lookup.get(val_str, "-")

        # Map Company Names
        # Fallback logic: If fyp_company_id missing, use company_id -> But prefer specific
        fyp_source = "fyp_company_id" if "fyp_company_id" in df.columns else "company_id"
        
        df["FYP_Company"] = df[fyp_source].apply(lambda x: safe_map(x, comp_map)) if fyp_source in df.columns else "-"
        df["LI_Company"] = df["li_company_id"].apply(lambda x: safe_map(x, comp_map)) if "li_company_id" in df.columns else "-"
        
        # Map Company States
        df["FYP_State"] = df[fyp_source].apply(lambda x: safe_map(x, comp_states)) if fyp_source in df.columns else "-"
        df["LI_State"] = df["li_company_id"].apply(lambda x: safe_map(x, comp_states)) if "li_company_id" in df.columns else "-"

        # Map Supervisors
        df["FYP_SV_Name"] = df["fyp_sv_id"].apply(lambda x: safe_map(x, staff_map)) if "fyp_sv_id" in df.columns else "-"
        df["LI_SV_Name"] = df["li_sv_id"].apply(lambda x: safe_map(x, staff_map)) if "li_sv_id" in df.columns else "-"

        # ALIASES FOR APP.PY COMPATIBILITY
        df["FYP 1 SV"] = df["FYP_SV_Name"]
        df["FYP 2 SV"] = df["FYP_SV_Name"]
        df["LI Uni SV"] = df["LI_SV_Name"]
        
        # Map Panelists (Assuming fyp1_panel_id / fyp2_panel_id exist)
        # If they don't exist yet, we default to "-"
        if "fyp1_panel_id" in df.columns:
            df["FYP 1 Panel"] = df["fyp1_panel_id"].apply(lambda x: safe_map(x, staff_map))
        else:
            df["FYP 1 Panel"] = "-"
            
        if "fyp2_panel_id" in df.columns:
            df["FYP 2 Panel"] = df["fyp2_panel_id"].apply(lambda x: safe_map(x, staff_map)) 
        else:
            df["FYP 2 Panel"] = "-"

        # FYP Title Alias (Space vs Underscore)
        df["FYP Title"] = df["FYP_Title"] if "FYP_Title" in df.columns else "-"
        
        # Address Stubs
        df["FYP_Address"] = "-" 
        df["LI_Address"] = "-"
        df["LI Industry SV"] = "-" 




        # Map Supabase columns to App expected columns
        rename_map = {
            "matrix_number": "Matrix_No",
            "name": "Student_Name",
            "program": "Program",
            "cohort": "Cohort",
            "email": "Email",
            "password": "Password",
            "fyp_title": "FYP_Title",
            "is_archived": "is_archived",
            "form_lapor_diri": "Lapor Diri",
            "form_aku_janji": "Aku Janji",
            "fyp1_marks": "FYP 1 Marks",
            "fyp2_marks": "FYP 2 Marks",
            "li_marks": "LI Marks"
        }
        df = df.rename(columns=rename_map)
        
        # Handle Missing Columns (Supabase might not return them if they are null)
        if "Lapor Diri" not in df.columns: df["Lapor Diri"] = "-"
        if "Aku Janji" not in df.columns: df["Aku Janji"] = "-"
        
        # Handle is_archived being None/NaN -> Treat as 0 (Active)
        if "is_archived" not in df.columns:
            df["is_archived"] = 0
        else:
            df["is_archived"] = df["is_archived"].fillna(0).astype(int)
        
        # Filter now
        if not include_archived:
            df = df[df["is_archived"] == 0]

        # Ensure status exists for display
        if "Status" not in df.columns:
            df["Status"] = "Active" 
            
        return df
    except Exception as e:
        st.error(f"Error fetching students: {e}")
        return pd.DataFrame()

# Aliases for compatibility
get_all_students_data = get_students

def get_students_for_marking(staff_db_id):
    """
    Fetches students where this staff is assigned as SV or Panel.
    """
    try:
        # Construct OR query
        # fyp_sv_id.eq.ID, li_sv_id.eq.ID, fyp1_panel_id.eq.ID, fyp2_panel_id.eq.ID
        # Supabase syntax: column.operator.value
        or_filter = f"fyp_sv_id.eq.{staff_db_id},li_sv_id.eq.{staff_db_id},fyp1_panel_id.eq.{staff_db_id},fyp2_panel_id.eq.{staff_db_id}"
        
        response = sb.table("students").select("*").or_(or_filter).execute()
        
        df = pd.DataFrame(response.data) if response.data else pd.DataFrame()
        
        if df.empty: return df
        
        # Apply standard cleaning/renaming
        rename_map = {
            "matrix_number": "Matrix_No",
            "name": "Student_Name",
            "program": "Program",
            "cohort": "Cohort",
            "email": "Email",
            "fyp_title": "FYP_Title",
            "fyp1_marks": "FYP 1 Marks",
            "fyp2_marks": "FYP 2 Marks",
            "li_marks": "LI Marks",
            "company_id": "company_id",
            "fyp_company_id": "fyp_company_id",
            "li_company_id": "li_company_id",
            "fyp_sv_id": "fyp_sv_id",
            "li_sv_id": "li_sv_id",
            "fyp1_panel_id": "fyp1_panel_id",
            "fyp2_panel_id": "fyp2_panel_id"
        }
        df = df.rename(columns=rename_map)
        
        # SYNTHETIC COLUMNS for App Logic Compatibility
        # App expects 'fyp1_sv_id', 'fyp2_sv_id' etc. but DB has 'fyp_sv_id'
        if "fyp_sv_id" in df.columns:
            df["fyp1_sv_id"] = df["fyp_sv_id"]
            df["fyp2_sv_id"] = df["fyp_sv_id"]
            
        if "li_sv_id" in df.columns:
            df["li_uni_sv_id"] = df["li_sv_id"]
            df["li_industry_sv_id"] = None # Not tracked for Staff Marking usually, or mapped elsewhere
            
        # Fill missing likely for display
        cols = ["FYP 1 Marks", "FYP 2 Marks", "LI Marks"]
        for c in cols:
            if c not in df.columns: df[c] = None
            
        return df
    except Exception as e:
        st.error(f"Error fetching students for marking: {e}")
        return pd.DataFrame()

def add_student(name, matrix, email, program, cohort, 
                fyp_cid=None, li_cid=None, 
                f1s_id=None, f1p_id=None, 
                f2s_id=None, f2p_id=None, 
                li_i_sv_id=None, li_u_sv_id=None, 
                fyp_title=None, password=None):
    """Adds a new student with all initial assignments."""
    try:
        data = {
            "name": name,
            "matrix_number": matrix,
            "email": email,
            "program": program,
            "cohort": cohort,
            "fyp_company_id": fyp_cid,
            "li_company_id": li_cid,
            "fyp_sv_id": f1s_id,
            "fyp1_panel_id": f1p_id,
            "fyp2_panel_id": f2p_id,
            "li_sv_id": li_u_sv_id,
            # If industry SV is a staff member, store it, but usually its external string.
            # Assuming DB column matches the key name if provided.
            "fyp_title": fyp_title,
            "password": password if password else matrix,
            "is_archived": 0
        }
        sb.table("students").insert(data).execute()
        return True, "Student added successfully."
    except Exception as e:
        return False, str(e)

def bulk_add_students(df):
    """
    Adds students in bulk from a DataFrame.
    Expected Columns: Name, Matrix Number, Email, Program, Cohort
    """
    count = 0
    errors = []
    try:
        col_names = list(df.columns)
        
        # Check for matching column names flexibly
        name_col = next((c for c in col_names if c.strip().lower() in ['name', 'student_name', 'student name']), None)
        matrix_col = next((c for c in col_names if c.strip().lower() in ['matrix number', 'matrix_no', 'matrix no']), None)
        email_col = next((c for c in col_names if c.strip().lower() in ['email']), None)
        prog_col = next((c for c in col_names if c.strip().lower() in ['program', 'programme']), None)
        cohort_col = next((c for c in col_names if c.strip().lower() in ['cohort']), None)

        if not name_col or not matrix_col:
            return 0, ["Required columns ('Name' and 'Matrix Number') not found in uploaded file. Found columns: " + ", ".join(col_names)]

        records = []
        for _, row in df.iterrows():
            # Basic validation
            name = str(row.get(name_col, '')).strip()
            matrix = str(row.get(matrix_col, '')).strip()
            
            # Skip empty or completely 'nan' rows from Excel
            if not name or not matrix or name.lower() == 'nan' or matrix.lower() == 'nan':
                continue
                
            email_val = str(row.get(email_col, '')).strip() if email_col else ""
            prog_val = str(row.get(prog_col, '')).strip() if prog_col else ""
            cohort_val = str(row.get(cohort_col, '')).strip() if cohort_col else ""

            rec = {
                "name": name,
                "matrix_number": matrix,
                "email": email_val if email_val.lower() != 'nan' else "",
                "program": prog_val if prog_val.lower() != 'nan' else "",
                "cohort": cohort_val if cohort_val.lower() != 'nan' else "",
                "password": matrix, # Default
                "is_archived": 0
            }
            records.append(rec)
            
        if not records:
            return 0, ["No valid student entries found in the file."]
            
        sb.table("students").insert(records).execute()
        count = len(records)
        return count, errors
    except Exception as e:
        return 0, [str(e)]

def verify_student_login(matrix, password):
    """
    Verifies student credentials.
    Returns student dict if success, else None.
    """
    try:
        res = sb.table("students").select("*").eq("matrix_number", matrix).eq("password", password).execute()
        if res.data and len(res.data) > 0:
            return res.data[0]
        else:
            return None
    except Exception as e:
        return None

def update_student(matrix, updates):
    """Update student details."""
    try:
        # Map back to DB column names if input uses App names
        db_updates = {}
        key_map = {
            "Student_Name": "name",
            "Matrix_No": "matrix_number",
            "Program": "program",
            "Cohort": "cohort",
            "Email": "email",
            "Password": "password",
            "FYP_Title": "fyp_title"
        }
        for k, v in updates.items():
            db_key = key_map.get(k, k) # Use map or original
            db_updates[db_key] = v
            
        sb.table("students").update(db_updates).eq("matrix_number", matrix).execute()
        return True, "Updated successfully."
    except Exception as e:
        return False, str(e)

def delete_student(matrix, changed_by="System"):
    """Soft Delete / Archive."""
    try:
        sb.table("students").update({"is_archived": 1}).eq("matrix_number", matrix).execute()
        return True, "Student deactivated/archived."
    except Exception as e:
        return False, str(e)

def archive_students_by_cohort(cohort, changed_by="System"):
    try:
        sb.table("students").update({"is_archived": 1}).eq("cohort", cohort).execute()
        return True, f"Cohort {cohort} archived."
    except Exception as e: return False, str(e)

def unarchive_students_by_cohort(cohort, changed_by="System"):
    try:
        sb.table("students").update({"is_archived": 0}).eq("cohort", cohort).execute()
        return True, f"Cohort {cohort} restored."
    except Exception as e: return False, str(e)


# Wrapper for Dashboard "Save" action on Company/SV changes
def update_student_company(matrix, company_id, type_="fyp", changed_by="System"):
    """
    Updates student's company/SV assignment.
    type_: 'fyp' or 'li'
    """
    try:
        # STRICT MAPPING for Separation
        if type_.lower() == "fyp":
             col_name = "fyp_company_id" 
        elif type_.lower() == "li":
             col_name = "li_company_id"
        else:
             col_name = "company_id"

        # FIX: Allow UUIDs (strings) or Ints. Only force Int if it purely digits.
        if company_id is not None:
            if str(company_id).isdigit():
                val = int(company_id)
            else:
                val = str(company_id) # Preserve UUID
        else:
            val = None
        
        res = sb.table("students").update({col_name: val}).eq("matrix_number", matrix).execute()
        
        # Detect silent RLS failure (0 rows actually updated)
        if hasattr(res, 'data') and len(res.data) == 0:
            return False, "Database blocked the update! (Row-Level Security policy error). Check your Supabase key."
        
        # Log it
        log_audit(matrix, f"{type_.upper()} Company", "Old", str(val), changed_by)
        return True, "Updated successfully"
    except Exception as e:
        return False, str(e)
        
def update_student_field(matrix, field, value, changed_by="Admin"):
    """
    Generic updater for single field from Dashboard.
    Maps App-Friendly Names -> DB Columns.
    """
    try:
        # 1. Map Field Name -> DB Column
        col_map = {
            "FYP 1 SV": "fyp_sv_id",
            "FYP 2 SV": "fyp_sv_id", # Assume same SV for now
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
        
        db_col = col_map.get(field, field.lower().replace(" ", "_")) # Fallback
        
        # 2. Handle Data Types
        # Marks should be float
        if "marks" in db_col:
            val = float(value) if value and value != "-" else None
        # IDs should be Int
        elif "_id" in db_col:
             if value is None or value == "-":
                 val = None
             elif str(value).isdigit():
                 val = int(value)
             else:
                 val = None # ID must be int usually
        else:
            val = value
            
        res = sb.table("students").update({db_col: val}).eq("matrix_number", matrix).execute()
        
        # Detect silent RLS failure
        if hasattr(res, 'data') and len(res.data) == 0:
            return False, "Database blocked the update! (Row-Level Security policy error)."
            
        log_audit(matrix, field, "Old", str(val), changed_by)
        return True, "Updated"
    except Exception as e:
        return False, str(e)

def update_student_marks(matrix, fyp1, fyp2, li, changed_by="Staff"):
    """
    Updates all 3 mark fields at once.
    """
    try:
        data = {
            "fyp1_marks": float(fyp1) if fyp1 is not None else None,
            "fyp2_marks": float(fyp2) if fyp2 is not None else None,
            "li_marks": float(li) if li is not None else None
        }
        sb.table("students").update(data).eq("matrix_number", matrix).execute()
        
        # Log it (just summary)
        log_audit(matrix, "Marks Update", "Detailed", f"{fyp1}|{fyp2}|{li}", changed_by)
        return True, "Marks updated successfully."
    except Exception as e:
        return False, str(e)

def sync_student_data(matrix):
    """
    Syncs FYP 1 data to FYP 2 (Company, Title) and LI columns.
    1. FYP Company -> LI Company
    2. FYP 1 Panel -> FYP 2 Panel
    3. FYP 1 SV -> LI Uni SV
    """
    try:
        # Get current data
        res = sb.table("students").select("*").eq("matrix_number", matrix).execute()
        if not res.data: return False, "Student not found"
        
        student = res.data[0]
        
        updates = {}
        
        # 1. Sync Company (FYP -> LI)
        if not student.get("li_company_id") and student.get("fyp_company_id"):
            updates["li_company_id"] = student["fyp_company_id"]
            
        # 2. Sync Panel (FYP 1 -> FYP 2)
        # If FYP 2 Panel is empty, use FYP 1 Panel
        if not student.get("fyp2_panel_id") and student.get("fyp1_panel_id"):
            updates["fyp2_panel_id"] = student["fyp1_panel_id"]

        # 3. Sync SV (FYP 1 SV -> LI Uni SV)
        # If LI SV is empty, use FYP SV
        if not student.get("li_sv_id") and student.get("fyp_sv_id"):
            updates["li_sv_id"] = student["fyp_sv_id"]
        
        if updates:
            sb.table("students").update(updates).eq("matrix_number", matrix).execute()
            return True, f"Synced {len(updates)} fields."
        else:
            return True, "Nothing to sync (already set)"
            
    except Exception as e:
        return False, str(e)
        
def bulk_update_titles(df):
    """Updates FYP Titles from DataFrame."""
    count = 0
    errors = []
    # Expects columns: 'Matrix Number', 'FYP Title'
    try:
        for _, row in df.iterrows():
            mat = str(row['Matrix Number']).strip()
            title = str(row['FYP Title']).strip()
            
            try:
                sb.table("students").update({"fyp_title": title}).eq("matrix_number", mat).execute()
                count += 1
            except Exception as e:
                errors.append(f"{mat}: {e}")
        return count, errors
    except Exception as e:
        return 0, [str(e)]

# ===========================
# STAFF FUNCTIONS
# ===========================

def get_staff():
    try:
        response = sb.table("staff").select("*").execute()
        return pd.DataFrame(response.data) if response.data else pd.DataFrame()
    except Exception as e:
        return pd.DataFrame()

# Alias for compatibility
get_all_staff = get_staff

def add_staff(name, staff_id, email, password):
    try:
        data = {"staff_name": name, "staff_id_number": staff_id, "staff_email": email, "staff_password": password}
        sb.table("staff").insert(data).execute()
        return True, "Staff added."
    except Exception as e:
        return False, str(e)

def delete_staff(staff_id):
    try:
        sb.table("staff").delete().eq("staff_id", staff_id).execute()
        return True
    except: return False

def get_staff_by_email(email):
    try:
        res = sb.table("staff").select("*").eq("staff_email", email).execute()
        if res.data: return pd.Series(res.data[0])
    except: pass
    return None

def verify_staff_login(staff_id_num, password):
    """
    Verifies staff credentials.
    Returns staff dict if success, else None.
    """
    try:
        # Match against 'staff_id_number' and 'staff_password' columns
        res = sb.table("staff").select("*").eq("staff_id_number", staff_id_num).eq("staff_password", password).execute()
        
        if res.data and len(res.data) > 0:
            return res.data[0] # Return the first matching staff record
        else:
            return None
    except Exception as e:
        print(f"Login Error: {e}")
        return None

# ===========================
# COMPANY FUNCTIONS
# ===========================

def get_companies():
    try:
        response = sb.table("companies").select("*").order("company_id").execute()
        df = pd.DataFrame(response.data) if response.data else pd.DataFrame()
        # Rename for App compatibility if needed
        # app uses 'Company Name'? Let's check. 
        # Usually checking column names is safer.
        rename = {"company_name": "Company Name", "address": "Address", "state": "State"}
        df = df.rename(columns=rename)
        # Normalize company_id to ensure it's a clean integer
        if "company_id" in df.columns:
            df["company_id"] = pd.to_numeric(df["company_id"], errors="coerce").fillna(0).astype(int)
        return df
    except: return pd.DataFrame()

get_all_companies_full = get_companies

def add_company(name, address=None, state=None):
    try:
        data = {"company_name": name, "address": address, "state": state}
        sb.table("companies").insert(data).execute()
        return True, "Company added."
    except Exception as e:
        return False, str(e)

def bulk_add_companies(df):
    count = 0
    errors = []
    # Mapping
    # Excel Name -> DB Name
    # 'Company Name' -> 'company_name'
    try:
        records = []
        for _, row in df.iterrows():
            rec = {
                "company_name": row.get('Company Name'),
                "address": row.get('Address'),
                "state": row.get('State')
            }
            if rec["company_name"]:
                records.append(rec)
        
        if records:
            # Batch insert
            sb.table("companies").insert(records).execute()
            count = len(records)
        return count, errors
    except Exception as e:
        return 0, [str(e)]


# Helper for Dropdowns
def get_company_labels():
    """Returns a dict { 'Company Name': company_id }"""
    df = get_companies()
    if df.empty: return {}
    # get_companies renames 'company_name' -> 'Company Name'
    # 'company_id' should still be there as 'company_id' unless dropped.
    # If not found, fall back safely.
    id_col = "company_id" if "company_id" in df.columns else "id"
    name_col = "Company Name" if "Company Name" in df.columns else "name"
    
    if id_col not in df.columns or name_col not in df.columns:
        return {}
        
    return dict(zip(df[name_col], df[id_col]))

def get_staff_options():
    """Returns a dict { 'Staff Name': staff_id }"""
    df = get_staff()
    if df.empty: return {}
    
    # FIX: Robust column finding based on debug output (staff_name)
    name_col = "staff_name" if "staff_name" in df.columns else ("name" if "name" in df.columns else "Name")
    id_col = "staff_id" if "staff_id" in df.columns else ("id" if "id" in df.columns else "Staff_ID")
    
    if name_col not in df.columns or id_col not in df.columns:
        return {}

    return dict(zip(df[name_col], df[id_col]))

# ===========================
# RUBRIC FUNCTIONS
# ===========================

def get_rubrics():
    try:
        response = sb.table("rubrics").select("*").execute()
        return pd.DataFrame(response.data) if response.data else pd.DataFrame()
    except: return pd.DataFrame()

def add_rubric(subject, cohort, item_name, filename):
    try:
        data = {"subject": subject, "cohort": cohort, "item_name": item_name, "filename": filename}
        sb.table("rubrics").insert(data).execute()
        return True, "Rubric saved."
    except Exception as e:
        return False, str(e)

def update_rubric(rubric_id, subject, cohort, item_name, filename=None):
    try:
        data = {"subject": subject, "cohort": cohort, "item_name": item_name}
        if filename:
            data["filename"] = filename
        sb.table("rubrics").update(data).eq("rubric_id", rubric_id).execute()
        return True, "Rubric updated."
    except Exception as e:
        return False, str(e)

def delete_rubric(rubric_id):
    try:
        sb.table("rubrics").delete().eq("rubric_id", rubric_id).execute()
        return True
    except: return False

# ===========================
# AUDIT & LOG FUNCTIONS
# ===========================

def get_audit_logs():
    try:
        res = sb.table("audit_logs").select("*").order("timestamp", desc=True).limit(100).execute()
        return pd.DataFrame(res.data) if res.data else pd.DataFrame()
    except: return pd.DataFrame()

def log_audit(matrix, field, old_val, new_val, changed_by):
    try:
        data = {
            "matrix_no": matrix,
            "field_changed": field,
            "old_value": str(old_val),
            "new_value": str(new_val),
            "changed_by": changed_by,
            "timestamp": datetime.now().isoformat()
        }
        sb.table("audit_logs").insert(data).execute()
    except: pass

def clear_all_data():
    """Danger Zone: Clear all data."""
    try:
        # Delete dependent first
        # sb.table("students").delete().neq("matrix_number", "00000").execute() # delete all
        # Supabase-py doesn't allow delete without WHERE usually to prevent accidents.
        # But we can try: 
        sb.table("students").delete().neq("matrix_number", "xyz_safety").execute()
        sb.table("companies").delete().neq("company_id", -1).execute()
        sb.table("staff").delete().neq("staff_id", -1).execute()
        sb.table("rubrics").delete().neq("rubric_id", -1).execute()
        return True, "All data wiped."
    except Exception as e:
        return False, str(e)
