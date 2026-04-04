import duckdb
import os

DB_DIR = '../fc-gen-resources'
DB_FILE = os.path.join(DB_DIR, 'friend_codes.db')
print(os.path.abspath(DB_FILE))
TEMP_DB = os.path.join(DB_DIR, 'friend_codes_optimized.db')
TMP_STORAGE = os.path.join(DB_DIR, 'duckdb_tmp')

def optimize_database():
    if not os.path.exists(DB_FILE):
        return
    if not os.path.exists(TMP_STORAGE):
        os.makedirs(TMP_STORAGE)

    try:
        if os.path.exists(TEMP_DB):
            os.remove(TEMP_DB)

        conn = duckdb.connect(TEMP_DB, config={
            'temp_directory': TMP_STORAGE,
            'preserve_insertion_order': False
        })
        conn.execute(f"ATTACH '{DB_FILE}' AS old_db")
        conn.execute("SET enable_progress_bar = true")
        conn.execute("CREATE TABLE main.fcs AS SELECT * FROM old_db.fcs ORDER BY bitmask")
        conn.close()

        os.remove(DB_FILE)
        os.rename(TEMP_DB, DB_FILE)

        import shutil
        shutil.rmtree(TMP_STORAGE)

    except Exception as e:
        if 'conn' in locals(): conn.close()
        if os.path.exists(TEMP_DB): os.remove(TEMP_DB)

optimize_database()