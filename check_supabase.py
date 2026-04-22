import sys
sys.path.append('.')
from supabase_handler import get_supabase_client

sb = get_supabase_client()
res = sb.table("students").select("*").limit(1).execute()
if res.data:
    print(res.data[0].keys())
