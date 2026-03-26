import duckdb
import os

db = 'fc-gen-resources/friend_codes.db'
chunks = 'fc-gen-resources/temp_chunks'

def test_duckdb_merge():
    if os.path.exists(db): os.remove(db)

    duckdb_tmp = os.path.abspath(os.path.join(chunks, 'duckdb_tmp'))
    print(duckdb_tmp)
    if not os.path.exists(duckdb_tmp):
        os.makedirs(duckdb_tmp)
    conn = duckdb.connect(db)
    conn.execute(f"PRAGMA threads={os.cpu_count()}")
    conn.execute("PRAGMA memory_limit='67GB'")
    conn.execute(f"PRAGMA temp_directory='{duckdb_tmp}'"); conn.execute("PRAGMA preserve_insertion_order=false")
    conn.execute("PRAGMA enable_progress_bar")
    conn.execute(f"CREATE TABLE fcs AS SELECT fc, bitmask FROM read_parquet('{chunks}/*.parquet')")
    conn.close()

if __name__ == '__main__':
    test_duckdb_merge()