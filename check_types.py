import sys
sys.path.append('.')
from supabase_handler import get_supabase_client

sb = get_supabase_client()
res = sb.rpc("get_schema", {}).execute()
print(res)
# fallback: just query pg_attribute if we can, or just print types from a direct REST call if possible.
