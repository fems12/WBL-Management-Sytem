import streamlit as st
import database as db
import pandas as pd
import os
import smtplib
import base64
import requests
import supabase_handler as sb
from email.mime.text import MIMEText

def send_recovery_email(to_email, password):
    """Sends password recovery email if secrets are configured."""
    has_secrets = False
    try:
        # Check if secrets exist without throwing error if file is missing
        if "EMAIL_USER" in st.secrets and "EMAIL_PASSWORD" in st.secrets:
            has_secrets = True
    except Exception:
        pass # Secrets file likely missing

    if not has_secrets:
        st.warning("⚠️ Email configuration missing. Please add `EMAIL_USER` and `EMAIL_PASSWORD` to `.streamlit/secrets.toml`.")
        # Fallback for demo purposes locally
        st.info(f"[DEV MODE] Simulated Email to {to_email}: Your password is {password}")
        return False
    
    sender_email = st.secrets["EMAIL_USER"]
    sender_password = st.secrets["EMAIL_PASSWORD"]
    
    subject = "WBL System - Password Recovery"
    body = f"Hello,\n\nYou requested a password recovery.\n\nYour Password: {password}\n\nPlease verify this is you."
    
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = sender_email
    msg['To'] = to_email
    
    try:
        # Defaulting to Gmail SMTP
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
        st.success(f"✅ Password has been sent to {to_email}")
        return True
    except Exception as e:
        st.error(f"Error sending email: {str(e)}")
        return False

# Page Configuration


st.set_page_config(
    page_title="WBL Student Management System", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize DB and Filesystem
db.init_db()
os.makedirs("uploads", exist_ok=True)

def main():
    st.markdown("""
        <style>
               .block-container {
                    padding-top: 1rem;
                    padding-bottom: 0rem;
                    margin-top: 1rem;
                }
        </style>
    """, unsafe_allow_html=True)
    st.title("🎓 WBL Student Management System")
    
    # Session State for Admin
    if "admin_logged_in" not in st.session_state:
        st.session_state["admin_logged_in"] = False

    # Sidebar Navigation
    st.sidebar.markdown("---")
    
    if st.session_state["admin_logged_in"]:
        st.sidebar.success("🔑 Admin Access")
        menu = ["Dashboard", "Add Student", "Register Company", "Manage Staff", "Rubric Manager", "Manage Data", "Student Portal"]
    else:
        menu = ["Student Portal", "Staff Portal", "Admin Login"]
        
    choice = st.sidebar.radio("🧭 MAIN MENU", menu)
    
    # SECURITY: Auto-logout when switching views
    if choice != "Staff Portal":
        # Clear Staff Session if navigating away
        if st.session_state.get("staff_id_num"):
            st.session_state["staff_id_num"] = None
            st.session_state["staff_name"] = None
            
    if choice != "Student Portal":
         # Clear Student Session if navigating away
         if st.session_state.get("student_matrix"):
             st.session_state["student_matrix"] = None
             st.session_state["student_name"] = None
    
    if choice == "Dashboard":
        show_dashboard()
    elif choice == "Student Portal":
        show_student_portal()
    elif choice == "Staff Portal":
        show_staff_marking_portal()
    elif choice == "Add Student":
        show_add_student()
    elif choice == "Register Company":
        show_register_company()
    elif choice == "Manage Staff":
        show_manage_staff()
    elif choice == "Rubric Manager":
        show_rubric_manager()
    elif choice == "Manage Data":
        show_manage_data()
    elif choice == "Admin Login":
        show_admin_login()

    # Dedicated Logout Button for Admin
    if st.session_state["admin_logged_in"]:
        st.sidebar.markdown("---")
        if st.sidebar.button("🚪 Logout Admin"):
            st.session_state["admin_logged_in"] = False
            st.rerun()

    # Dedicated Logout Button for Student
    if "student_matrix" in st.session_state and st.session_state["student_matrix"]:
        st.sidebar.markdown("---")
        st.sidebar.info(f"👤 {st.session_state['student_name']}")
        if st.sidebar.button("🚪 Logout Student"):
            st.session_state["student_matrix"] = None
            st.session_state["student_name"] = None
            st.rerun()

def show_staff_marking_portal():
    st.header("📝 Staff Marking Portal")
    
    if "staff_id_num" not in st.session_state:
        st.session_state["staff_id_num"] = None
        st.session_state["staff_name"] = None

    # Login Section
    if not st.session_state["staff_id_num"]:
        st.info("Enter your Staff ID and Password to view your students.")
        sid = st.text_input("Staff ID Number")
        spwd = st.text_input("Password", type="password")
        
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Access Portal", use_container_width=True):
                staff_data = db.verify_staff_login(sid, spwd)
                if staff_data:
                    st.session_state["staff_id_num"] = sid
                    st.session_state["staff_db_id"] = staff_data['staff_id']
                    st.session_state["staff_name"] = staff_data['staff_name']
                    st.session_state["staff_dept"] = staff_data.get('department')
                    st.success("Login successful!")
                    st.rerun()
                else:
                    st.error("Invalid Staff ID or Password.")
        
        with c2:
            with st.expander("❓ Forgot Password"):
                st.write("Enter your ID and registered Email to recover.")
                rec_id = st.text_input("Staff ID", key="rec_sid")
                rec_em = st.text_input("Email", key="rec_sem")
                if st.button("Recover Password"):
                    sd = db.get_staff_by_id_number(rec_id)
                    if sd and sd['staff_email'] == rec_em:
                        send_recovery_email(rec_em, sd['staff_password'])
                    else: st.error("ID and Email do not match our records.")
        return

    # User Profile / Logout / Change Pwd Header
    with st.expander(f"👤 Logged in as: {st.session_state['staff_name']}", expanded=False):
        cp1, cp2 = st.columns(2)
        with cp1:
            new_p = st.text_input("New Password", type="password")
            if st.button("Change Password"):
                if new_p:
                    s, m = db.update_staff_password(st.session_state["staff_id_num"], new_p)
                    if s: st.success(m)
                    else: st.error(m)
        with cp2:
            if st.button("🚪 Logout Staff", use_container_width=True):
                st.session_state["staff_id_num"] = None
                st.rerun()
        st.markdown("---")

    # Marking Section
    st.subheader("Your Students")
    df = db.get_students_for_marking(st.session_state["staff_db_id"])
    
    # Filter by Department if set
    dept = st.session_state.get("staff_dept")
    if dept and not df.empty:
        # Filter where Program matches Department (case-insensitive partial match or exact?)
        # User requested "same department/program". Let's assume exact match first, or contain.
        # df['Program'] contains the program name.
        df = df[df['Program'] == dept]
    
    if df.empty:
        st.warning("No students assigned to you.")
        return

    # --- RUBRICS SECTION ---
    with st.expander("📂 Reference Rubrics & Documents (Click to Expand)", expanded=False):
         relevant_cohorts = df['Cohort'].unique().tolist()
         staff_id = st.session_state["staff_db_id"]
         
         # Check relevant subjects for this staff
         has_fyp1 = ((df['fyp1_sv_id'] == staff_id) | (df['fyp1_panel_id'] == staff_id)).any()
         has_fyp2 = ((df['fyp2_sv_id'] == staff_id) | (df['fyp2_panel_id'] == staff_id)).any()
         has_li = ((df['li_industry_sv_id'] == staff_id) | (df['li_uni_sv_id'] == staff_id)).any()
         
         rubrics_df = db.get_rubrics()
         
         if not rubrics_df.empty:
             mask = pd.Series([False] * len(rubrics_df))
             if has_fyp1: mask |= ((rubrics_df['subject'] == "FYP 1") & (rubrics_df['cohort'].isin(relevant_cohorts)))
             if has_fyp2: mask |= ((rubrics_df['subject'] == "FYP 2") & (rubrics_df['cohort'].isin(relevant_cohorts)))
             if has_li: mask |= ((rubrics_df['subject'] == "LI") & (rubrics_df['cohort'].isin(relevant_cohorts)))
             
             visible_rubrics = rubrics_df[mask]
             
             if not visible_rubrics.empty:
                 cols = st.columns(3)
                 for i, sub in enumerate(["FYP 1", "FYP 2", "LI"]):
                     with cols[i]:
                         sub_rubs = visible_rubrics[visible_rubrics['subject'] == sub]
                         if not sub_rubs.empty:
                             st.markdown(f"**{sub}**")
                             for _, r in sub_rubs.iterrows():
                                 fname = r['filename']
                                 iname = r['item_name']
                                 coh = r['cohort']
                                 import os
                                 fpath = os.path.join("uploads", "rubrics", fname)
                                
                                 # Use Cloud Storage Link
                                 url = sb.get_signed_url("rubrics", fname)
                                 if not url:
                                      # Fallback to Public
                                      url = sb.get_public_url("rubrics", fname)
                                      
                                 if url:
                                     st.link_button(f"📥 {iname} (Open/Download)", url)
                                     st.caption(f"Cohort: {coh}")
                                 elif os.path.exists(fpath):
                                     # Fallback to Local if exists (Dev mode)
                                      with open(fpath, "rb") as f:
                                         st.download_button(f"📥 {iname}", f, file_name=fname, key=f"rub_{r['rubric_id']}")
                                         st.caption(f"Cohort: {coh}")
                                 else:
                                     st.error(f"File not found: {fname}")
             else:
                 st.info("No rubrics found for your assigned subjects/cohorts.")
         else:
             st.info("No rubrics available.")
    
    st.markdown("---")

    # Filters for Staff Portal
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        search_q = st.text_input("🔍 Search", "")
    with c2:
        subject_filter = st.selectbox("📚 Subject", ["All", "FYP 1", "FYP 2", "LI"])
    with c3:
        role_filter = st.selectbox("🎯 Role", ["All", "SV Only", "Panel Only"])
    with c4:
        progs = ["All"] + sorted(df['Program'].dropna().unique().tolist())
        selected_prog = st.selectbox("🎓 Program", progs)
    with c5:
        cohorts = ["All"] + sorted(df['Cohort'].dropna().unique().tolist())
        selected_cohort = st.selectbox("📅 Cohort", cohorts)
    
    filtered_df = df.copy()
    staff_id = st.session_state["staff_db_id"]
    
    # 1. Filter by Subject & Role
    if subject_filter == "FYP 1":
        if role_filter == "SV Only":
            filtered_df = filtered_df[filtered_df['fyp1_sv_id'] == staff_id]
        elif role_filter == "Panel Only":
            filtered_df = filtered_df[filtered_df['fyp1_panel_id'] == staff_id]
        else:
            filtered_df = filtered_df[(filtered_df['fyp1_sv_id'] == staff_id) | (filtered_df['fyp1_panel_id'] == staff_id)]
    
    elif subject_filter == "FYP 2":
        if role_filter == "SV Only":
            filtered_df = filtered_df[filtered_df['fyp2_sv_id'] == staff_id]
        elif role_filter == "Panel Only":
            filtered_df = filtered_df[filtered_df['fyp2_panel_id'] == staff_id]
        else:
            filtered_df = filtered_df[(filtered_df['fyp2_sv_id'] == staff_id) | (filtered_df['fyp2_panel_id'] == staff_id)]
            
    elif subject_filter == "LI":
        if role_filter == "SV Only":
            filtered_df = filtered_df[(filtered_df['li_industry_sv_id'] == staff_id) | (filtered_df['li_uni_sv_id'] == staff_id)]
        elif role_filter == "Panel Only":
            filtered_df = filtered_df.iloc[0:0] # Panels don't exist for LI in this logic
        else:
            filtered_df = filtered_df[(filtered_df['li_industry_sv_id'] == staff_id) | (filtered_df['li_uni_sv_id'] == staff_id)]
            
    else: # Subject: All
        if role_filter == "SV Only":
            mask = (filtered_df['fyp1_sv_id'] == staff_id) | (filtered_df['fyp2_sv_id'] == staff_id) | \
                   (filtered_df['li_industry_sv_id'] == staff_id) | (filtered_df['li_uni_sv_id'] == staff_id)
            filtered_df = filtered_df[mask]
        elif role_filter == "Panel Only":
            mask = (filtered_df['fyp1_panel_id'] == staff_id) | (filtered_df['fyp2_panel_id'] == staff_id)
            filtered_df = filtered_df[mask]

    # 2. Filter by Search
    if search_q:
        filtered_df = filtered_df[
            (filtered_df['Student_Name'].str.contains(search_q, case=False, na=False)) | 
            (filtered_df['Matrix_No'].str.contains(search_q, case=False, na=False))
        ]

    # 3. Filter by Program & Cohort
    if selected_prog != "All": filtered_df = filtered_df[filtered_df['Program'] == selected_prog]
    if selected_cohort != "All": filtered_df = filtered_df[filtered_df['Cohort'] == selected_cohort]

    # Editable Table Configuration
    st.info(f"Showing {len(filtered_df)} student(s). Edit marks and click 'Save Marks' below.")
    
    # Hide irrelevant mark columns based on subject filter
    config = {
        "Student_Name": st.column_config.Column("Name", disabled=True, width="medium"),
        "Matrix_No": st.column_config.Column("Matrix No", disabled=True, width="small"),
        "Program": st.column_config.Column(disabled=True, width="small"),
        "Cohort": st.column_config.Column(disabled=True, width="small"),
        "FYP_Title": st.column_config.Column("FYP Title", disabled=True, width="large"),
        "FYP 1 Marks": st.column_config.NumberColumn(min_value=0, max_value=100, format="%.2f"),
        "FYP 2 Marks": st.column_config.NumberColumn(min_value=0, max_value=100, format="%.2f"),
        "LI Marks": st.column_config.NumberColumn(min_value=0, max_value=100, format="%.2f")
    }

    # Hide columns based on filter
    hidden_cols = []
    if subject_filter == "FYP 1":
        hidden_cols.extend(["FYP 2 Marks", "LI Marks"])
    elif subject_filter == "FYP 2":
        hidden_cols.extend(["FYP 1 Marks", "LI Marks"])
    elif subject_filter == "LI":
        hidden_cols.extend(["FYP 1 Marks", "FYP 2 Marks"])

    # Force Column Order for better visibility
    # We construct a new DF with ONLY the cols we want to show/edit
    desired_order = ["Matrix_No", "Student_Name", "Program", "Cohort", "FYP_Title", "FYP 1 Marks", "FYP 2 Marks", "LI Marks"]
    
    # Ensure all exist
    final_cols = [c for c in desired_order if c in filtered_df.columns and c not in hidden_cols]
    
    # If there are other columns we want to keep hidden but need for logic? 
    # Actually data_editor returns a DF with the same columns as input.
    # So we should pass only what we want to see.
    
    df_to_show = filtered_df[final_cols].copy()

    edited_df = st.data_editor(
        df_to_show,
        column_config=config,
        hide_index=True,
        use_container_width=True,
        key="marking_editor"
    )

    if st.button("Save Marks", type="primary"):
        success_count = 0
        errors = []
        for index, row in edited_df.iterrows():
            # Check if any marks changed vs original 'df' is tricky in direct loop without comparing.
            # We'll just update all valid rows for robustness or only changed if we wanted to optimize.
            # Simple update for now.
            matrix = row['Matrix_No']
            f1 = row['FYP 1 Marks']
            f2 = row['FYP 2 Marks']
            li = row['LI Marks']
            
            # Validation (handled by UI constraint mostly, but double check)
            if (pd.notna(f1) and (f1 < 0 or f1 > 100)) or \
               (pd.notna(f2) and (f2 < 0 or f2 > 100)) or \
               (pd.notna(li) and (li < 0 or li > 100)):
               st.toast(f"⚠️ Validation Error for {matrix}: Marks must be between 0 and 100.", icon="⚠️")
               errors.append(f"Validation Error for {matrix}: Marks must be between 0 and 100.")
               continue

            changed_by = st.session_state.get("staff_name", "Staff")
            success, msg = db.update_student_marks(matrix, f1, f2, li, changed_by=changed_by)
            if success: success_count += 1
            else: errors.append(f"Error {matrix}: {msg}")
            
        if success_count > 0:
            st.success(f"Updated marks for {success_count} students!")
        if errors:
            for e in errors: st.error(e)

def show_admin_login():
    st.header("🔐 Admin Login")
    
    with st.form("admin_login"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")
        
        if submitted:
            if username == "admin" and password == "admin":
                st.session_state["admin_logged_in"] = True
                st.success("Login successful!")
                st.rerun()
            else:
                st.error("Invalid credentials.")

def show_student_portal():
    st.header("📂 Student Portal")
    
    # Initialize session state for student login if not present
    if "student_matrix" not in st.session_state:
        st.session_state["student_matrix"] = None
        st.session_state["student_name"] = None

    # Login Logic
    if not st.session_state["student_matrix"]:
        st.info("Enter your Matrix Number and Password to access your profile.")
        matrix_input = st.text_input("Matrix Number")
        pwd_input = st.text_input("Password", type="password")
        
        lc1, lc2 = st.columns(2)
        with lc1:
            if st.button("Student Login", type="primary", use_container_width=True):
                student_data = db.verify_student_login(matrix_input, pwd_input)
                if student_data:
                    st.session_state["student_matrix"] = matrix_input
                    st.session_state["student_name"] = student_data['name']
                    st.success("Welcome back!")
                    st.rerun()
                else:
                    st.error("Invalid Matrix Number or Password.")
        
        with lc2:
            with st.expander("❓ Forgot Password"):
                st.write("Enter your ID and registered Email to recover.")
                rec_sid = st.text_input("Matrix Number", key="r_mid")
                rec_sem = st.text_input("Email", key="r_mem")
                if st.button("Retrieve Password", use_container_width=True):
                    sd = db.get_student_by_matrix(rec_sid)
                    if sd and sd.get('email') == rec_sem:
                        send_recovery_email(rec_sem, sd['password'])
                    else: st.error("No record found with this ID/Email combo.")
        return

    # User Profile / Logout / Change Pwd Header
    with st.expander(f"👋 Welcome, {st.session_state['student_name']}", expanded=True):
        cp1, cp2 = st.columns(2)
        with cp1:
            new_p = st.text_input("New Password", type="password")
            if st.button("Change Password"):
                if new_p:
                    ok, msg = db.update_student_password(st.session_state["student_matrix"], new_p)
                    if ok: st.success(msg)
                    else: st.error(msg)
        with cp2:
            if st.button("🚪 Logout Portal", use_container_width=True):
                st.session_state["student_matrix"] = None
                st.session_state["student_name"] = None
                st.rerun()

    # Upload View (Only shown if logged in)
    st.markdown("---")
    st.write("Please upload your documents below.")
    
    matrix_no = st.session_state["student_matrix"]
    
    c1, c2 = st.columns(2)
    
    # Helper to handle upload
    def handle_upload(uploaded_file, doc_type):
        if uploaded_file:
            if uploaded_file.type != "application/pdf":
                st.error("Only PDF files are allowed.")
                return
            
            # Ensure uploads dir exists
            import os
            if not os.path.exists("uploads"):
                os.makedirs("uploads")
                
            # Save File
            filename = f"{matrix_no}_{doc_type}.pdf"
            save_path = os.path.join("uploads", filename)
            
            with open(save_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            # Update DB
            success, msg = db.update_student_docs(matrix_no, doc_type, filename)
            if success: st.success(f"✅ {msg}")
            else: st.error(f"❌ {msg}")

    with c1:
        st.subheader("Borang Lapor Diri")
        f1 = st.file_uploader("Upload PDF", type=["pdf"], key="u1")
        if st.button("Submit Lapor Diri"):
            handle_upload(f1, "lapor_diri")

    with c2:
        st.subheader("Borang Aku Janji")
        f2 = st.file_uploader("Upload PDF", type=["pdf"], key="u2")
        if st.button("Submit Aku Janji"):
            handle_upload(f2, "aku_janji")

def show_dashboard():
    st.header("📊 Student Dashboard")
    
    view_archived = st.sidebar.toggle("📂 View Archived Students", value=False)
    
    df = db.get_all_students_data(include_archived=view_archived)
    
    if view_archived:
        # Filter to show ONLY archived if toggle is ON
        if "is_archived" in df.columns:
            df = df[df["is_archived"] == 1]
    
    if df.empty:
        st.info("No students found. Please add students to view them here.")
        return


    st.divider()

    # Data needed for editors
    companies_map = db.get_company_labels()
    company_options = ["-"] + list(companies_map.keys())
    staff_options_map = db.get_staff_options() # Label: ID
    staff_labels = ["-"] + list(staff_options_map.keys())

    # Sidebar Filters
    st.sidebar.markdown("---")
    st.sidebar.subheader("Filters")
    programs = ["All"] + sorted(df['Program'].dropna().unique().tolist())
    cohorts = ["All"] + sorted(df['Cohort'].dropna().unique().tolist())
    states = ["All"] + sorted(set(df['FYP_State'].tolist() + df['LI_State'].tolist()))
    if "-" in states: states.remove("-")
    
    selected_program = st.sidebar.selectbox("Filter by Program", programs)
    selected_cohort = st.sidebar.selectbox("Filter by Cohort", cohorts)
    selected_state = st.sidebar.selectbox("Filter by State", ["All"] + sorted(states))
    
    # New Filters: Search and Staff
    st.sidebar.markdown("---")
    st.sidebar.subheader("🔍 Search & Staff")
    search_query = st.sidebar.text_input("🔍 Search Student (Name/Matrix)", "")
    staff_filter_options = ["All"] + sorted(list(staff_options_map.keys()))
    selected_staff = st.sidebar.selectbox("🧑‍🏫 Filter by Staff", staff_filter_options)
    
    # Staff Role Filter
    selected_role = st.sidebar.selectbox("🎯 Filter by Role", ["Both (Any)", "Supervisor (SV)", "Panelist"])
    
    filtered_df = df.copy()
    if selected_program != "All": filtered_df = filtered_df[filtered_df['Program'] == selected_program]
    if selected_cohort != "All": filtered_df = filtered_df[filtered_df['Cohort'] == selected_cohort]
    if selected_state != "All":
        filtered_df = filtered_df[(filtered_df['FYP_State'] == selected_state) | (filtered_df['LI_State'] == selected_state)]
    
    if search_query:
        filtered_df = filtered_df[
            (filtered_df['Student_Name'].str.contains(search_query, case=False, na=False)) | 
            (filtered_df['Matrix_No'].str.contains(search_query, case=False, na=False))
        ]
    
    if selected_staff != "All":
        if selected_role == "Supervisor (SV)":
            staff_cols = ["FYP 1 SV", "FYP 2 SV", "LI Industry SV", "LI Uni SV"]
        elif selected_role == "Panelist":
            staff_cols = ["FYP 1 Panel", "FYP 2 Panel"]
        else: # Both (Any)
            staff_cols = ["FYP 1 SV", "FYP 1 Panel", "FYP 2 SV", "FYP 2 Panel", "LI Industry SV", "LI Uni SV"]
            
        # Match the exact staff label in the specified columns
        mask = filtered_df[staff_cols].apply(lambda row: selected_staff in row.values, axis=1)
        filtered_df = filtered_df[mask]

    # Selection & Bulk Sync (Moved to Top)
    # Selection Header
    c1, c2 = st.columns([2, 8], gap="small")
    with c1:
        select_all = st.checkbox("✅ Select All Students", value=False)
    
    # --- Analytics Header (Dynamic) ---
    st.divider()
    with st.container():
        # Metrics Calculation based on filtered_df
        t_students = len(filtered_df)
        
        # Companies: Count unique non-null FYP and LI companies in filtered view
        # Companies are in column 'FYP_Company' and 'LI_Company' but they are formatted strings "Name (State)"
        # A rough unique count is fine.
        unique_companies = set(filtered_df['FYP_Company'].unique().tolist() + filtered_df['LI_Company'].unique().tolist())
        unique_companies.discard("-")
        unique_companies.discard(None)
        t_companies = len(unique_companies)
        
        # Docs Pending: Count where Lapor Diri or Aku Janji is invalid (before icon conversion)
        # Note: In the raw DB, empty strings or NULL are problem. 
        # In df from get_all_students_data, COALESCE is used so they are '' if null.
        docs_pending = len(filtered_df[
            (filtered_df['Lapor Diri'] == '') | (filtered_df['Aku Janji'] == '')
        ])
        
        # Grading Pending: Check marks. In df, they are floats or None.
        grading_pending = len(filtered_df[
            ((filtered_df['FYP 1 Marks'].isna()) | (filtered_df['FYP 1 Marks'] == 0)) &
            ((filtered_df['FYP 2 Marks'].isna()) | (filtered_df['FYP 2 Marks'] == 0)) &
            ((filtered_df['LI Marks'].isna()) | (filtered_df['LI Marks'] == 0))
        ])
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Students", t_students)
        m2.metric("Active Companies", t_companies)
        m3.metric("Documents Pending", docs_pending)
        m4.metric("Grading Pending", grading_pending)
        


    st.divider()

    # Calculate Status Column
    def get_status(row):
        # 1. Check Docs (Raw values before icon conversion)
        if row['Lapor Diri'] == '' or row['Aku Janji'] == '':
            return "Incomplete"
            
        # 2. Check Marks
        def valid_mark(m):
            try:
                return pd.notna(m) and float(m) > 0
            except: return False
            
        f1 = row['FYP 1 Marks']
        f2 = row['FYP 2 Marks']
        li = row['LI Marks']
        
        if valid_mark(f1) and valid_mark(f2) and valid_mark(li):
            return "Graded"
            
        return "Ongoing"

    filtered_df['Status'] = filtered_df.apply(get_status, axis=1)

    # Add Document Status Icons to DF for display
    def get_icon(val):
        return "✅" if val and val != "" else "❌"
    
    filtered_df['Lapor Diri'] = filtered_df['Lapor Diri'].apply(get_icon)
    filtered_df['Aku Janji'] = filtered_df['Aku Janji'].apply(get_icon)

    # Add Selection Column for Syncing (RESTORED)
    filtered_df.insert(0, "Sync?", select_all)
    filtered_df = filtered_df.fillna("-").replace("", "-")
    filtered_df.insert(1, 'No.', range(1, len(filtered_df) + 1))

    # Column Visibility (Tick Boxes in Expander)
    all_optional_cols = {
        "Sync": "Sync?",
        "No.": "No.",
        "Status": "Status",
        "Student Name": "Student_Name",
        "Matrix Number": "Matrix_No",
        "Email": "Email",
        "Password": "Password",
        "Program": "Program",
        "Cohort": "Cohort",
        "Lapor Diri": "Lapor_Diri",
        "Aku Janji": "Aku_Janji",
        "Company": "Company",
        "Address": "Address",
        "State Profile": "State",
        "Uni SV": "Uni_SV",
        "Industry SV": "Industry_SV",
        "Panelist": "Panelist",
        "Marks": "Marks",
        "FYP Title": "FYP Title"
    }
    
    def get_visible_cols(subject_type, shown):
        """Builds column list based on current visibility for FYP_1, FYP_2, or LI"""
        # Base columns always shown
        v_cols = []
        if "Sync" in shown: v_cols.append("Sync?")
        if "No." in shown: v_cols.append("No.")
        if "Status" in shown: v_cols.append("Status")
        if "Student Name" in shown: v_cols.append("Student_Name")
        if "Matrix Number" in shown: v_cols.append("Matrix_No")
        
        # Add Optional Columns based on selection
        if "Email" in shown: v_cols.append("Email")
        if "Password" in shown: v_cols.append("Password")
        if "Program" in shown: v_cols.append("Program")
        if "Cohort" in shown: v_cols.append("Cohort")
        if "Lapor Diri" in shown: v_cols.append("Lapor Diri")
        if "Aku Janji" in shown: v_cols.append("Aku Janji")
        
        # Subject Specific
        if subject_type in ["FYP_1", "FYP_2"]:
            if "Company" in shown: v_cols.append("FYP_Company")
            if "Address" in shown: v_cols.append("FYP_Address")
            if "State Profile" in shown: v_cols.append("FYP_State")
            
            if subject_type == "FYP_1":
                if "Marks" in shown: v_cols.append("FYP 1 Marks")
                if "Uni SV" in shown: v_cols.append("FYP 1 SV")
                if "Panelist" in shown: v_cols.append("FYP 1 Panel")
                if "FYP Title" in shown: v_cols.append("FYP Title")
            else: # FYP_2
                if "Marks" in shown: v_cols.append("FYP 2 Marks")
                if "Uni SV" in shown: v_cols.append("FYP 2 SV")
                if "Panelist" in shown: v_cols.append("FYP 2 Panel")
                if "FYP Title" in shown: v_cols.append("FYP Title")
        else: # LI
            if "Company" in shown: v_cols.append("LI_Company")
            if "Address" in shown: v_cols.append("LI_Address")
            if "State Profile" in shown: v_cols.append("LI_State")
            
            if "Marks" in shown: v_cols.append("LI Marks")
            if "Industry SV" in shown: v_cols.append("LI Industry SV")
            if "Uni SV" in shown: v_cols.append("LI Uni SV")
            
        return v_cols

    def render_tab_config(subject_type):
        """Renders the configuration expander and returns final columns"""
        with st.expander("👁️ Configure Table Columns", expanded=False):
            shown_local = []
            rows = [list(all_optional_cols.keys())[i:i + 4] for i in range(0, len(all_optional_cols), 4)]
            for row in rows:
                cols = st.columns(len(row))
                for i, col_name in enumerate(row):
                    # Default visibility for common columns
                    is_default = col_name in ["Sync", "No.", "Status", "Student Name", "Matrix Number", "Program", "Cohort"]
                    
                    # Default visibility for subject-specific columns
                    if subject_type == "FYP_1":
                        if col_name in ["Company", "State Profile", "Uni SV", "Panelist", "Marks"]: is_default = True
                    elif subject_type == "FYP_2":
                        if col_name in ["Company", "State Profile", "Uni SV", "Panelist", "Marks"]: is_default = True
                    elif subject_type == "LI":
                        if col_name in ["Company", "State Profile", "Uni SV", "Industry SV", "Marks"]: is_default = True

                    # Unique key per tab
                    if cols[i].checkbox(col_name, value=is_default, key=f"chk_{subject_type}_{col_name}"):
                        shown_local.append(col_name)
        return get_visible_cols(subject_type, shown_local)

    # Identify ticked students across tabs for Sync and Document actions
    ticked_matrices = set()
    rows_to_download = [] # List of (Name, Matrix, LaporPath, AkuPath)
    tab_keys = ["editor_FYP_1", "editor_FYP_2", "editor_LI"]
    
    for idx, row in filtered_df.iterrows():
        matrix = row["Matrix_No"]
        is_ticked = select_all 
        for key in tab_keys:
            if key in st.session_state:
                edits = st.session_state[key].get("edited_rows", {})
                if str(idx) in edits and "Sync?" in edits[str(idx)]:
                    is_ticked = edits[str(idx)]["Sync?"]
                elif idx in edits and "Sync?" in edits[idx]:
                    is_ticked = edits[idx]["Sync?"]
        if is_ticked:
            ticked_matrices.add(matrix)
            src_row = df[df['Matrix_No'] == matrix].iloc[0]
            rows_to_download.append(src_row)

    def render_subject_analytics(df_viz, subject):
        """Displays metrics and charts for a specific subject (FYP 1, FYP 2, LI)"""
        with st.container():
            st.markdown(f"### 📊 Analysis for {subject}")
            
            # 1. Config mapping
            if subject == "FYP 1":
                mark_col = "FYP 1 Marks"
                comp_col = "FYP_Company"
                sv_col = "FYP 1 SV"
            elif subject == "FYP 2":
                mark_col = "FYP 2 Marks"
                comp_col = "FYP_Company"
                sv_col = "FYP 2 SV"
            else: # LI
                mark_col = "LI Marks"
                comp_col = "LI_Company"
                sv_col = "LI Industry SV" 

            # 2. Metrics Calculation
            total_students = len(df_viz)
            
            # Assigned Rate: Count non-null/non-dash SVs
            assigned_count = len(df_viz[ (df_viz[sv_col] != "-") & (df_viz[sv_col].notna()) ])
            assign_rate = (assigned_count / total_students * 100) if total_students > 0 else 0
            
            # Grading Progress: Marks > 0
            # Ensure marks are numeric (handle cases where they might be strings like "-")
            numeric_vals = pd.to_numeric(df_viz[mark_col], errors='coerce')
            
            graded_df = df_viz[ (numeric_vals.notna()) & (numeric_vals > 0) ]
            graded_count = len(graded_df)
            grade_rate = (graded_count / total_students * 100) if total_students > 0 else 0
            
            # Avg Marks
            # use the numeric series for mean calculation
            avg_marks = numeric_vals[numeric_vals > 0].mean() if not numeric_vals[numeric_vals > 0].empty else 0
            
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Total Students", total_students)
            m2.metric("Assignment Rate", f"{assign_rate:.1f}%")
            m3.metric("Grading Progress", f"{grade_rate:.1f}%")
            m4.metric("Average Marks", f"{avg_marks:.2f}")

            st.markdown("---")
            
            # State Distribution Chart (Context Aware)
            state_col = "LI_State" if "LI" in subject.upper() or "Li" in subject else "FYP_State"
            if state_col in df_viz.columns:
                state_counts = df_viz[state_col].value_counts().reset_index()
                state_counts.columns = ["State", "Count"]
                state_counts = state_counts[state_counts["State"] != "-"]
                
                if not state_counts.empty:
                    with st.expander(f"🗺️ Student Distribution by State ({subject})", expanded=True):
                        import altair as alt
                        max_y = len(df_viz)
                        if max_y < 5: max_y = 5
                        
                        base = alt.Chart(state_counts).encode(
                            x=alt.X('State', sort='-y', axis=alt.Axis(labelAngle=-45)),
                            y=alt.Y('Count', 
                                    axis=alt.Axis(tickMinStep=1, title='Number of Students', format='d'),
                                    scale=alt.Scale(domain=[0, max_y])
                                   ),
                            tooltip=['State', 'Count']
                        )
                        bars = base.mark_bar()
                        text = base.mark_text(align='center', dy=-5).encode(text='Count')
                        c = (bars + text).properties(title=f"Distribution for {subject}")
                        st.altair_chart(c, use_container_width=True)
            
            st.markdown("---")
            
            # 3. Charts - Grade Distribution Only
            import altair as alt
            
            st.subheader("📈 Grade Distribution")
            # Define bins
            def get_grade_bin(m):
                if m >= 80: return "A"
                elif m >= 75: return "A-"
                elif m >= 70: return "B+"
                elif m >= 65: return "B"
                elif m >= 60: return "B-"
                elif m >= 55: return "C+"
                elif m >= 50: return "C"
                elif m >= 47: return "C-"
                elif m >= 44: return "D+"
                elif m >= 40: return "D"
                else: return "E"

            all_grades = ["A", "A-", "B+", "B", "B-", "C+", "C", "C-", "D+", "D", "E"]

            if not graded_df.empty:
                grade_counts = graded_df[mark_col].apply(get_grade_bin).value_counts()
            else:
                grade_counts = pd.Series(dtype=int)
            
            # Reindex to include missing grades as 0
            grade_counts = grade_counts.reindex(all_grades, fill_value=0).reset_index()
            grade_counts.columns = ["Grade Range", "Count"]

            # Fixed Y-Scale based on total students
            y_max = total_students if total_students > 0 else 5
            if y_max < 5: y_max = 5 # Ensure at least some height

            base_g = alt.Chart(grade_counts).encode(
                x=alt.X('Grade Range', sort=all_grades, axis=alt.Axis(labelAngle=0)),
                y=alt.Y('Count', 
                        title='Students', 
                        axis=alt.Axis(tickMinStep=1, format='d'),
                        scale=alt.Scale(domain=[0, y_max])
                       ), 
                tooltip=['Grade Range', 'Count']
            )
            bars_g = base_g.mark_bar(color='teal')
            text_g = base_g.mark_text(align='center', dy=-5, fontSize=14).encode(
                text=alt.Text('Count', format='.0f')
            )
            
            st.altair_chart((bars_g + text_g), use_container_width=True)
            st.divider()

    def render_editor(df_view, subject_cols, spec_id):
        # CLEANUP: Ensure mark columns are valid numbers for the editor (remove "-" placeholders)
        # We work on a copy to avoid SettingWithCopy warnings on the original filtered_df
        df_view = df_view.copy() 
        mark_cols = ["FYP 1 Marks", "FYP 2 Marks", "LI Marks"]
        for mc in mark_cols:
            if mc in df_view.columns:
                df_view[mc] = df_view[mc].replace("-", None)
                df_view[mc] = pd.to_numeric(df_view[mc], errors='coerce')

        config = {
            "No.": st.column_config.Column(disabled=True, width="small"),
            "Status": st.column_config.Column(disabled=True, width="small"),
            "Student_Name": st.column_config.Column(disabled=True, width="medium"),
            "Matrix_No": st.column_config.Column(disabled=True, width="small"),
            "Email": st.column_config.Column(width="medium"),
            "Password": st.column_config.Column(width="small"),
            "Program": st.column_config.Column(disabled=True, width="small"),
            "Cohort": st.column_config.Column(disabled=True, width="small"),
            "FYP_State": st.column_config.Column(disabled=True, width="small"),
            "LI_State": st.column_config.Column(disabled=True, width="small"),
            "FYP_Address": st.column_config.Column(disabled=True, width="medium"),
            "LI_Address": st.column_config.Column(disabled=True, width="medium"),
            "Lapor Diri": st.column_config.Column(disabled=True, width="small"),
            "Aku Janji": st.column_config.Column(disabled=True, width="small"),
            "FYP 1 Marks": st.column_config.NumberColumn("FYP 1 Marks", min_value=0, max_value=100, format="%.2f"),
            "FYP 2 Marks": st.column_config.NumberColumn("FYP 2 Marks", min_value=0, max_value=100, format="%.2f"),
            "LI Marks": st.column_config.NumberColumn("LI Marks", min_value=0, max_value=100, format="%.2f"),
            "FYP Title": st.column_config.TextColumn("FYP Title", width="large"),
        }
        if "FYP_Company" in df_view.columns:
            config["FYP_Company"] = st.column_config.SelectboxColumn("FYP Company", options=company_options, width="medium")
        if "LI_Company" in df_view.columns:
            config["LI_Company"] = st.column_config.SelectboxColumn("LI Company", options=company_options, width="medium")
            
        for col in subject_cols:
            config[col] = st.column_config.SelectboxColumn(col, options=staff_labels, width="medium")

        edited_df = st.data_editor(df_view, column_config=config, hide_index=True, use_container_width=True, key=f"editor_{spec_id}")

        if f"editor_{spec_id}" in st.session_state:
            edits = st.session_state[f"editor_{spec_id}"].get("edited_rows", {})
            if edits:
                st.warning(f"💡 Unsaved changes in {spec_id.replace('_', ' ')}.")
                if st.button(f"Save {spec_id.replace('_', ' ')} Updates"):
                    success_count = 0
                    for row_idx, changes in edits.items():
                        # Use .loc with the original index to ensure we find the Matrix_No even if hidden from current view
                        matrix_no = filtered_df.loc[df_view.index[int(row_idx)]]["Matrix_No"]
                        for field, val in changes.items():
                            val = None if val == "-" else val
                            if field in ["FYP_Company", "LI_Company"]:
                                cid = companies_map.get(val) if val else None
                                # DEBUG: Show what we are trying to save
                                st.toast(f"Saving: {matrix_no} -> {val} (ID: {cid})")
                                
                                success, err_msg = db.update_student_company(matrix_no, cid, field.split('_')[0].lower(), changed_by="Admin")
                                if success: 
                                    success_count += 1
                                else:
                                    st.error(f"Failed {matrix_no}: {err_msg}")
                            else:
                                # Handles Staff selection and generic text fields like Email
                                val_to_save = staff_options_map.get(val) if (field in subject_cols and val != "-") else val
                                success, _ = db.update_student_field(matrix_no, field, val_to_save, changed_by="Admin")
                                if success: success_count += 1
                    if success_count > 0:
                        st.toast(f"✅ Updated {success_count} fields successfully!", icon="💾")
                        import time
                        time.sleep(1.0) # Short pause to let user see toast before refresh
                        st.rerun()

    tab_f1, tab_f2, tab_li = st.tabs(["📘 FYP 1", "📗 FYP 2", "🏢 Industrial Training"])

    with tab_f1:
        c_sync1, c_sync2 = st.columns([1, 1])
        with c_sync1:
            # Existing "Sync Selected" Button
            if st.button("🔄 Sync Selected to FYP 2 & LI", type="primary"):
                if ticked_matrices:
                    success_count = 0
                    for matrix in ticked_matrices:
                        success, _ = db.sync_student_data(matrix)
                        if success: success_count += 1
                    st.toast(f"✅ Successfully synced {success_count} students!", icon="🔄")
                    import time
                    time.sleep(1.0)
                    st.rerun()
                else:
                    st.warning("Please tick students first.")
                    
        with c_sync2:
            # NEW: Sync ALL Button
            if st.button("⚡ Sync ALL Listed Students", type="secondary"):
                if not filtered_df.empty:
                    success_count = 0
                    # Iterate over ALL valid matrices in the current view
                    all_matrices = filtered_df["Matrix_No"].unique().tolist()
                    for matrix in all_matrices:
                        success, _ = db.sync_student_data(matrix)
                        if success: success_count += 1
                    
                    st.toast(f"✅ Successfully synced ALL {success_count} students!", icon="⚡")
                    import time
                    time.sleep(1.0)
                    st.rerun()
                else:
                    st.warning("No students to sync.")

        # Analytics
        render_subject_analytics(filtered_df, "FYP 1")

        tab_cols = render_tab_config("FYP_1")
        # Safety filter to ensure columns exist in DF (Prevent KeyError)
        tab_cols = [c for c in tab_cols if c in filtered_df.columns]
        
        if tab_cols:
            render_editor(filtered_df[tab_cols], [c for c in ["FYP 1 SV", "FYP 1 Panel"] if c in tab_cols], "FYP_1")
        else:
            st.warning("All columns hidden. Please enable some in 'Configure Table Columns'.")
        
    with tab_f2:
        # Analytics
        render_subject_analytics(filtered_df, "FYP 2")

        tab_cols = render_tab_config("FYP_2")
        tab_cols = [c for c in tab_cols if c in filtered_df.columns]
        
        if tab_cols:
            render_editor(filtered_df[tab_cols], [c for c in ["FYP 2 SV", "FYP 2 Panel"] if c in tab_cols], "FYP_2")
        else:
            st.warning("All columns hidden.")
        
    with tab_li:
        # Analytics
        render_subject_analytics(filtered_df, "Li") # typo fix: LI

        tab_cols = render_tab_config("LI")
        tab_cols = [c for c in tab_cols if c in filtered_df.columns]
        
        if tab_cols:
            render_editor(filtered_df[tab_cols], [c for c in ["LI Industry SV", "LI Uni SV"] if c in tab_cols], "LI")
        else:
            st.warning("All columns hidden.")


    # Document Download Section
    if rows_to_download:
        st.markdown("---")
        st.subheader("📂 Document Actions")
        st.write(f"Selected {len(rows_to_download)} student(s).")
        import os
        
        for s in rows_to_download:
            n = s['Student_Name']
            m = s['Matrix_No']
            path_l = s['Lapor Diri']
            path_a = s['Aku Janji']
            
            c1, c2, c3 = st.columns([2, 1, 1])
            c1.write(f"**{n}** ({m})")
            
            with c2:
                if path_l and path_l != "":
                    if os.path.exists(os.path.join("uploads", path_l)):
                        with open(os.path.join("uploads", path_l), "rb") as f:
                            st.download_button(f"📥 Lapor Diri", f, file_name=path_l, key=f"dl_l_{m}")
                    else: st.error("File missing")
                else: st.write("No Lapor Diri")
                
            with c3:
                if path_a and path_a != "":
                    if os.path.exists(os.path.join("uploads", path_a)):
                        with open(os.path.join("uploads", path_a), "rb") as f:
                            st.download_button(f"📥 Aku Janji", f, file_name=path_a, key=f"dl_a_{m}")
                    else: st.error("File missing")
                else: st.write("No Aku Janji")
            st.divider()

def show_add_student():
    st.header("👨‍🎓 Add New Student")
    companies = db.get_company_labels()
    staff_options_map = db.get_staff_options()
    staff_labels = ["Unassigned"] + list(staff_options_map.keys())

    # Auto-Population Checkbox
    sync_all = st.checkbox("🔗 Use same Supervisor, Panel, and Company for all subjects", value=True)
    
    # We use a container instead of a form to allow real-time reactivity if needed, 
    # but we'll stick to a submit button for the final write.
    st.subheader("Basic Information")
    c1, c2 = st.columns(2)
    with c1:
        name = st.text_input("Student Name")
        matrix = st.text_input("Matrix Number")
    with c2:
        email = st.text_input("Email Address")
        c2a, c2b = st.columns(2)
        with c2a: program = st.text_input("Program (e.g. BEB)")
        with c2b: cohort = st.text_input("Cohort (e.g. 2024/2025)")

    # Section 1: FYP 1 (Source for Sync)
    with st.expander("📘 FYP 1 Details", expanded=True):
        f1_c1, f1_c2 = st.columns(2)
        with f1_c1:
            fyp1_comp = st.selectbox("Assign FYP Company", ["Unassigned"] + list(companies.keys()), key="f1_comp")
            f1sv = st.selectbox("FYP 1 Supervisor", staff_labels, key="f1_sv")
        with f1_c2:
            st.write("")
            st.write("")
            f1p = st.selectbox("FYP 1 Panel", staff_labels, key="f1_p")
            
            fyp_title = st.text_area("FYP Project Title", height=68)

    # Section 2 & 3: FYP 2 & LI (Dependent on Sync)
    with st.expander("📗 FYP 2 Details", expanded=not sync_all):
        f2_c1, f2_c2 = st.columns(2)
        with f2_c1:
            # If sync is on, we use FYP 1's values as defaults
            f2sv_val = f1sv if sync_all else staff_labels[0]
            f2sv = st.selectbox("FYP 2 Supervisor", staff_labels, index=staff_labels.index(f2sv_val), key="f2_sv")
        with f2_c2:
            f2p_val = f1p if sync_all else staff_labels[0]
            f2p = st.selectbox("FYP 2 Panel", staff_labels, index=staff_labels.index(f2p_val), key="f2_p")

    with st.expander("🏢 Industrial Training (LI) Details", expanded=not sync_all):
        li_c1, li_c2 = st.columns(2)
        with li_c1:
            li_comp_val = fyp1_comp if sync_all else "Unassigned"
            li_comp = st.selectbox("Assign LI Company", ["Unassigned"] + list(companies.keys()), index=(["Unassigned"] + list(companies.keys())).index(li_comp_val), key="li_comp")
            
            li_i_sv = st.selectbox("Industry Supervisor", staff_labels, key="li_i_sv")
        with li_c2:
            li_u_sv_val = f1sv if sync_all else staff_labels[0]
            li_u_sv = st.selectbox("University Supervisor", staff_labels, index=staff_labels.index(li_u_sv_val), key="li_u_sv")

    if st.button("Submit Student Data", type="primary", use_container_width=True):
        if name and matrix:
            def get_id(mapping, label):
                return mapping.get(label) if label not in ["Unassigned", "-"] else None

            success, msg = db.add_student(
                name=name, matrix=matrix, email=email, program=program, cohort=cohort,
                fyp_cid=get_id(companies, fyp1_comp),
                li_cid=get_id(companies, li_comp),
                f1s_id=get_id(staff_options_map, f1sv),
                f1p_id=get_id(staff_options_map, f1p),
                f2s_id=get_id(staff_options_map, f2sv),
                f2p_id=get_id(staff_options_map, f2p),
                li_i_sv_id=get_id(staff_options_map, li_i_sv),
                li_u_sv_id=get_id(staff_options_map, li_u_sv),
                fyp_title=fyp_title
            )
            if success: 
                st.success(f"✅ {msg}")
                st.balloons()
            else: st.error(msg)
        else: st.warning("Name and Matrix Number are required.")

def show_manage_staff():
    st.header("👨‍🏫 Manage Staff")
    tab1, tab2 = st.tabs(["Staff List", "Add Staff"])
    with tab1:
        df = db.get_all_staff()
        if not df.empty:
            df.insert(0, 'No.', range(1, len(df) + 1))
            edited_staff = st.data_editor(
                df, 
                use_container_width=True, 
                hide_index=True,
                column_config={
                    "No.": st.column_config.Column(disabled=True),
                    "ID Number": st.column_config.Column(disabled=True)
                },
                key="staff_editor"
            )
            
            if "staff_editor" in st.session_state:
                edits = st.session_state["staff_editor"].get("edited_rows", {})
                if edits:
                    st.warning("💡 Unsaved changes in Staff List.")
                    if st.button("Save Staff Updates"):
                        s_count = 0
                        for row_idx, changes in edits.items():
                            sid_num = df.iloc[int(row_idx)]["ID Number"]
                            for field, val in changes.items():
                                success, _ = db.update_staff_field(sid_num, field, val)
                                if success: s_count += 1
                        if s_count > 0:
                            st.success(f"Updated {s_count} fields!")
                            st.rerun()
        else: st.info("No staff recorded.")
    with tab2:
        with st.form("staff_form"):
            sname = st.text_input("Staff Name")
            sid = st.text_input("Staff ID Number")
            semail = st.text_input("Email Address")
            
            # Fetch existing programs to suggest as Department
            stud_df = db.get_all_students_data()
            if not stud_df.empty:
                prog_opts = sorted(stud_df['Program'].dropna().unique().tolist())
            else:
                prog_opts = []
                
            sdept = st.selectbox("Department / Program", ["-"] + prog_opts)
            if sdept == "-": sdept = None

            if st.form_submit_button("Register Staff"):
                if sname and sid:
                    success, msg = db.add_staff(sname, sid, semail, department=sdept)
                    if success: st.success(msg); st.rerun()
                    else: st.error(msg)

def show_register_company():
    st.header("🏢 Register Company")
    tab1, tab2, tab3 = st.tabs(["Manual", "Bulk", "📁 Company Directory"])
    
    with tab1:
        with st.form("comp_form"):
            cname = st.text_input("Company Name")
            addr = st.text_area("Address")
            state = st.selectbox("State", ["Johor", "Kedah", "Kelantan", "Melaka", "Negeri Sembilan", "Pahang", "Pulau Pinang", "Perak", "Perlis", "Sabah" , "Sarawak", "Selangor", "Terengganu", "Kuala Lumpur", "Labuan", "Putrajaya"])
            if st.form_submit_button("Register"):
                if cname:
                    success, msg = db.add_company(cname, addr, state)
                    if success: st.success(msg); st.rerun()
                    else: st.error(msg)
    with tab2:
        up = st.file_uploader("Upload Company Excel", type="xlsx")
        if up:
            df = pd.read_excel(up)
            if st.button("Process Bulk Upload"):
                with st.spinner("Processing Bulk Upload..."):
                    count, errs = db.bulk_add_companies(df)
                    st.success(f"✅ Added {count} companies successfully!")
                    if errs: st.warning(f"Issues: {errs}")
                    import time
                    time.sleep(1)
                    st.rerun()

    with tab3:
        st.subheader("Registered Companies")
        comp_df = db.get_all_companies_full()
        if not comp_df.empty:
            search = st.text_input("🔍 Search Company Name", "")
            if search:
                comp_df = comp_df[comp_df['Company Name'].str.contains(search, case=False, na=False)]
            
            comp_df.insert(0, 'No.', range(1, len(comp_df) + 1))
            st.dataframe(comp_df, use_container_width=True, hide_index=True)
        else:
            st.info("No companies registered yet.")

def show_manage_data():
    st.header("⚙️ Manage Data")
    
    t1, t2, t3, t4, t5, t6 = st.tabs(["📋 Student List", "🗑️ Delete Student", "⚠️ Danger Zone", "📂 Archive Data", "📜 Audit Logs", "📝 Bulk Update Titles"])
    
    with t1:
        st.subheader("All Students")
        students = db.get_all_students_data(include_archived=True)
        if not students.empty:
            # Display subset of info for management view (Hidden Password)
            view_cols = ["Student_Name", "Matrix_No", "Email", "Program", "Cohort", "Status", "is_archived"]
            
            search = st.text_input("🔍 Search Student List", "")
            # Ensure cols exist
            view_cols = [c for c in view_cols if c in students.columns]
            df_display = students[view_cols]
            
            if search:
                df_display = df_display[
                    (df_display['Student_Name'].str.contains(search, case=False, na=False)) |
                    (df_display['Matrix_No'].str.contains(search, case=False, na=False))
                ]
            
            df_display.insert(0, 'No.', range(1, len(df_display) + 1))
            st.dataframe(df_display, use_container_width=True, hide_index=True)
        else:
            st.info("No students found in the database.")

    with t2:
        st.subheader("Deactivate Student")
        students = db.get_all_students_data()
        if not students.empty:
            student_list = [f"{row['Student_Name']} ({row['Matrix_No']})" for _, row in students.iterrows()]
            selected = st.selectbox("Select Student to Deactivate", ["-"] + student_list, key="del_student_select")
            
            if selected != "-":
                matrix = selected.split("(")[-1].strip(")")
                if st.button("Deactivate Student", type="primary", key="del_student_btn"):
                    success, msg = db.delete_student(matrix, changed_by="Admin")
                    if success:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)
        else:
            st.info("No students found.")

    with t3:
        st.subheader("Reset Database")
        st.warning("🚨 This will permanently delete ALL students, companies, and staff data.")
        if st.button("RESET ENTIRE DATABASE", type="primary"):
            success, msg = db.clear_all_data()
            if success: st.success(msg); st.rerun()

    with t4:
        st.subheader("Archive by Cohort")
        students = db.get_all_students_data(include_archived=False) # Get active only
        if not students.empty:
            cohorts = sorted(students['Cohort'].dropna().unique().tolist())
            c_to_archive = st.selectbox("Select Cohort to Archive", ["-"] + cohorts)
            if c_to_archive != "-":
                st.warning(f"⚠️ This will archive ALL students in cohort {c_to_archive}.")
                if st.button("Archive Cohort", type="primary"):
                    success, msg = db.archive_students_by_cohort(c_to_archive, changed_by="Admin")
                    if success: st.success(msg); st.rerun()
                    else: st.error(msg)
        else: st.info("No active students to archive.")

        st.divider()
        st.subheader("Unarchive by Cohort")
        # Fetch only archived students
        all_s = db.get_all_students_data(include_archived=True)
        if not all_s.empty:
            archived_df = all_s[all_s['is_archived'] == 1]
            if not archived_df.empty:
                cohorts_arch = sorted(archived_df['Cohort'].dropna().unique().tolist())
                c_unarch = st.selectbox("Select Cohort to Restore", ["-"] + cohorts_arch)
                if c_unarch != "-":
                    st.warning(f"⚠️ This will restore ALL students in cohort {c_unarch} to the active dashboard.")
                    if st.button("Unarchive Cohort", type="primary"):
                        success, msg = db.unarchive_students_by_cohort(c_unarch, changed_by="Admin")
                        if success: st.success(msg); st.rerun()
                        else: st.error(msg)
            else: st.info("No archived data found.")
        else: st.info("Database is empty.")

    with t5:
        st.subheader("System Audit Logs")
        logs = db.get_audit_logs()
        if not logs.empty:
            st.dataframe(logs, use_container_width=True)
        else:
            st.info("No logs found.")

    with t6:
        st.subheader("Bulk Update FYP Titles")
        st.info("Upload an Excel file with columns: 'Matrix Number' and 'FYP Title'.")
        
        up_file = st.file_uploader("Upload Excel", type=["xlsx"], key="bulk_title_up")
        if up_file:
            try:
                df_titles = pd.read_excel(up_file)
                if 'Matrix Number' in df_titles.columns and 'FYP Title' in df_titles.columns:
                    st.write("### Preview Data")
                    st.dataframe(df_titles[['Matrix Number', 'FYP Title']].head(), use_container_width=True)
                    
                    if st.button("Confirm & Update Titles", type="primary"):
                        with st.spinner("Updating Titles..."):
                            count, errs = db.bulk_update_titles(df_titles)
                            if count > 0:
                                st.success(f"✅ Successfully updated {count} titles!")
                            if errs:
                                with st.expander("View Errors"):
                                    for e in errs: st.write(e)
                            if count > 0:
                                import time
                                time.sleep(1)
                                st.rerun()
                else:
                    st.error("Excel file must contain 'Matrix Number' and 'FYP Title' columns.")
            except Exception as e:
                st.error(f"Error processing file: {e}")



def show_rubric_manager():
    st.header("📑 Rubric Manager (Cloud Storage)")
    
    conn, msg = sb.test_connection()
    if conn: st.caption(f"🟢 Storage: {msg}")
    else: st.error(f"🔴 Storage Error: {msg}")
    
    tab1, tab2 = st.tabs(["📤 Upload Rubric", "🗑️ Manage Rubrics"])
    
    with tab1:
        st.subheader("Upload New Rubric")
        st.info("Files are stored securely in Supabase Storage.")
        with st.form("rubric_upload"):
            c1, c2 = st.columns(2)
            with c1:
                subj = st.selectbox("Subject", ["FYP 1", "FYP 2", "LI"])
                item = st.text_input("Item Name (e.g. Presentation Rubric)")
            with c2:
                # Suggest cohorts from students if available, else text
                # We'll valid year range or free text
                cohort = st.text_input("Cohort (e.g. 2024/2025)")
                
            # Dynamic key to reset uploader after success
            if "rubric_uploader_id" not in st.session_state: st.session_state["rubric_uploader_id"] = 0
            uploaded = st.file_uploader("Upload PDF", type=["pdf"], key=f"rub_pdf_{st.session_state['rubric_uploader_id']}")
            
            if st.form_submit_button("Upload Rubric", type="primary"):
                if subj and item and cohort and uploaded:
                    # Sanitize filename
                    safe_item = "".join([c if c.isalnum() else "_" for c in item])
                    safe_cohort = "".join([c if c.isalnum() else "_" for c in cohort])
                    fname = f"{subj.replace(' ', '_')}_{safe_cohort}_{safe_item}.pdf"
                    
                    with st.spinner("Uploading to Cloud..."):
                        # Upload to Supabase 'rubrics' bucket
                        success, res_msg = sb.upload_to_bucket("rubrics", fname, uploaded.getvalue())
                        
                        if success:
                            # Save to DB
                            db_success, db_msg = db.add_rubric(subj, cohort, item, fname)
                            if db_success:
                                st.success(f"✅ Saved: {db_msg}")
                                st.session_state["rubric_uploader_id"] += 1
                                import time
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error(f"DB Error: {db_msg}")
                        else:
                            st.error(f"Upload Error: {res_msg}")
                else:
                    st.warning("All fields are required.")

    with tab2:
        st.subheader("Existing Rubrics")
        if not hasattr(db, "get_rubrics"):
            st.error("⚠️ The `database.py` file on this server is outdated and missing Rubric functions. Please update `database.py`.")
            df = pd.DataFrame() # Empty DF fallback
        else:
            df = db.get_rubrics()
        
        if not df.empty:
            # Filters
            fc1, fc2 = st.columns(2)
            with fc1:
                sub_filter = st.selectbox("Filter by Subject", ["All", "FYP 1", "FYP 2", "LI"], key="rub_sub_filter")
            with fc2:
                cohorts = ["All"] + sorted(df['cohort'].unique().tolist())
                coh_filter = st.selectbox("Filter by Cohort", cohorts, key="rub_coh_filter")
            
            # Apply Filters
            df_display = df.copy()
            if sub_filter != "All":
                df_display = df_display[df_display['subject'] == sub_filter]
            if coh_filter != "All":
                df_display = df_display[df_display['cohort'] == coh_filter]

            if df_display.empty:
                st.info("No rubrics match the filters.")
            else:
                # Group by Subject for cleaner view
                subjects = ["FYP 1", "FYP 2", "LI"]
                for sub in subjects:
                    sub_df = df_display[df_display['subject'] == sub]
                    if not sub_df.empty:
                        st.markdown(f"#### {sub}")
                        for _, row in sub_df.iterrows():
                            with st.container():
                                c1, c2, c3, c4 = st.columns([3, 1.5, 1, 1])
                                with c1:
                                    st.write(f"**{row['item_name']}** (Cohort: {row['cohort']})")
                                    st.caption(f"File: {row['filename']}")
                                
                                # Try Signed URL first (More reliable for View)
                                public_url = sb.get_signed_url("rubrics", row['filename'])
                                if not public_url:
                                     # Fallback to Public URL
                                     public_url = sb.get_public_url("rubrics", row['filename'])

                                with c2:
                                    if public_url:
                                        st.link_button("📥 Open/Download", public_url)
                                    else:
                                        st.error("Link Error")

                                with c3:
                                    if public_url:
                                        if st.button("👁️ View", key=f"view_admin_{row['rubric_id']}"):
                                            if st.session_state.get("viewing_pdf") == row['rubric_id']:
                                                st.session_state["viewing_pdf"] = None # Toggle Close
                                            else:
                                                st.session_state["viewing_pdf"] = row['rubric_id']
                                                
                                with c4:
                                    if st.button("✏️ Edit", key=f"edit_btn_{row['rubric_id']}"):
                                        if st.session_state.get("edit_rubric_id") == row['rubric_id']:
                                            st.session_state["edit_rubric_id"] = None
                                        else:
                                            st.session_state["edit_rubric_id"] = row['rubric_id']
                                            
                                    if st.button("🗑️ Delete", key=f"del_admin_{row['rubric_id']}"):
                                        sb.delete_from_bucket("rubrics", row['filename'])
                                        db.delete_rubric(row['rubric_id'])
                                        st.rerun()
                                
                                # Edit Form Section
                                if st.session_state.get("edit_rubric_id") == row['rubric_id']:
                                    with st.container():
                                        st.info("📝 Editing Rubric Details")
                                        ec1, ec2 = st.columns(2)
                                        with ec1:
                                            n_subj = st.selectbox("Subject", ["FYP 1", "FYP 2", "LI"], index=["FYP 1", "FYP 2", "LI"].index(row['subject']), key=f"es_{row['rubric_id']}")
                                            n_item = st.text_input("Item Name", value=row['item_name'], key=f"ei_{row['rubric_id']}")
                                        with ec2:
                                            n_cohort = st.text_input("Cohort", value=row['cohort'], key=f"ec_{row['rubric_id']}")
                                            n_file = st.file_uploader("Replace PDF (Optional)", type=["pdf"], key=f"ef_{row['rubric_id']}")
                                        
                                        if st.button("💾 Save Changes", key=f"save_{row['rubric_id']}", type="primary"):
                                            final_fname = None
                                            if n_file:
                                                # Save new file
                                                save_dir = os.path.join("uploads", "rubrics")
                                                safe_item = "".join([c if c.isalnum() else "_" for c in n_item])
                                                safe_cohort = "".join([c if c.isalnum() else "_" for c in n_cohort])
                                                final_fname = f"{n_subj.replace(' ', '_')}_{safe_cohort}_{safe_item}.pdf"
                                                
                                                # Remove old file if name changed or just clean up? 
                                                # If we overwrite, ok. If name changes, we should clean old.
                                                # For simplicity, let's just save new.
                                                with st.spinner("Uploading new file..."):
                                                    sb.upload_to_bucket("rubrics", final_fname, n_file.getvalue())
                                            
                                            with st.spinner("Updating..."):
                                                s, m = db.update_rubric(row['rubric_id'], n_subj, n_cohort, n_item, final_fname)
                                                if s: 
                                                    st.success("Updated!"); st.session_state["edit_rubric_id"] = None; st.rerun()
                                                else: st.error(m)
                                        st.divider()

                                # PDF Viewer Section
                                if st.session_state.get("viewing_pdf") == row['rubric_id'] and public_url:
                                    st.markdown(f"**Viewing: {row['item_name']}**")
                                    pdf_display = f'<iframe src="{public_url}" width="100%" height="800"></iframe>'
                                    st.markdown(pdf_display, unsafe_allow_html=True)
                                    if st.button("Close Viewer", key=f"close_{row['rubric_id']}"):
                                        st.session_state["viewing_pdf"] = None
                                        st.rerun()
                                    st.divider()
                                elif st.session_state.get("edit_rubric_id") != row['rubric_id']:
                                    st.divider()
        else:
            st.info("No rubrics uploaded.")

if __name__ == "__main__":
    main()
