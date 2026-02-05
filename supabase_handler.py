import streamlit as st
try:
    from supabase import create_client, Client
except ImportError:
    pass # Handle case where module isn't installed yet

def get_supabase_client():
    try:
        # Try nested [supabase] section first (Standard)
        if "supabase" in st.secrets:
            url = st.secrets["supabase"]["url"]
            key = st.secrets["supabase"]["key"]
        # Fallback: Try flat keys (Common mistake fix)
        elif "supabase_url" in st.secrets and "supabase_key" in st.secrets:
            url = st.secrets["supabase_url"]
            key = st.secrets["supabase_key"]
        # Fallback: Try just 'url' and 'key' if user pasted JUST the contents
        elif "url" in st.secrets and "key" in st.secrets:
            url = st.secrets["url"]
            key = st.secrets["key"]
        else:
            st.error("❌ Missing Secrets! Please add [supabase] section with url and key.")
            return None
            
        return create_client(url, key)
    except Exception as e:
        st.error(f"Supabase Init Error: {e}")
        return None

def test_connection():
    """Checks if Supabase is reachable."""
    client = get_supabase_client()
    if not client: return False, "Secrets not found"
    try:
        # Try a simple operation
        client.storage.list_buckets()
        return True, "Connected"
    except Exception as e:
        return False, str(e)

def upload_to_bucket(bucket_name, file_path, file_bytes, content_type="application/pdf"):
    """
    Uploads bytes to Supabase Storage.
    file_path: 'folder/filename.pdf'
    """
    client = get_supabase_client()
    if not client: return False, "Supabase credentials missing."
    
    try:
        client.storage.from_(bucket_name).upload(
            path=file_path,
            file=file_bytes,
            file_options={"content-type": content_type, "upsert": "true"}
        )
        return True, "Uploaded"
    except Exception as e:
        return False, str(e)

def get_public_url(bucket_name, file_path):
    client = get_supabase_client()
    if not client: return None
    return client.storage.from_(bucket_name).get_public_url(file_path)

def get_signed_url(bucket_name, file_path, expires_in=3600):
    client = get_supabase_client()
    if not client: return None
    try:
        data = client.storage.from_(bucket_name).create_signed_url(file_path, expires_in)
        # Supabase-py v2 returns a dict with 'signedURL' or a string? 
        # Usually it returns specific object. Let's try handling it.
        # If creates_signed_url returns JSON-like response:
        if isinstance(data, dict) and "signedURL" in data:
            return data["signedURL"]
        return data # If it returns the string directly
    except: return None

def delete_from_bucket(bucket_name, file_path):
    client = get_supabase_client()
    if client:
        try:
            client.storage.from_(bucket_name).remove([file_path])
            return True
        except: return False
    return False
