import duckdb

if __name__ == "__main__":
    conn = duckdb.connect('../fc-gen-resources/friend_codes.db')

    conn.execute("""
        CREATE TEMP MACRO get_x(c) AS 
            CASE c WHEN '1' THEN 0 WHEN '4' THEN 0 WHEN '7' THEN 0 
                   WHEN '2' THEN 1 WHEN '5' THEN 1 WHEN '8' THEN 1 WHEN '0' THEN 1 
                   WHEN '3' THEN 2 WHEN '6' THEN 2 WHEN '9' THEN 2 END;

        CREATE TEMP MACRO get_y(c) AS 
            CASE c WHEN '1' THEN 0 WHEN '2' THEN 0 WHEN '3' THEN 0 
                   WHEN '4' THEN 1 WHEN '5' THEN 1 WHEN '6' THEN 1 
                   WHEN '7' THEN 2 WHEN '8' THEN 2 WHEN '9' THEN 2 
                   WHEN '0' THEN 3 END;

        CREATE TEMP MACRO dist(c1, c2) AS 
            abs(get_x(c1) - get_x(c2)) + abs(get_y(c1) - get_y(c2));

        CREATE TEMP MACRO total_moves(fc) AS 
            dist('1', substr(fc, 1, 1)) +
            dist(substr(fc, 1, 1), substr(fc, 2, 1)) +
            dist(substr(fc, 2, 1), substr(fc, 3, 1)) +
            dist(substr(fc, 3, 1), substr(fc, 4, 1)) +
            dist(substr(fc, 4, 1), substr(fc, 5, 1)) +
            dist(substr(fc, 5, 1), substr(fc, 6, 1)) +
            dist(substr(fc, 6, 1), substr(fc, 7, 1)) +
            dist(substr(fc, 7, 1), substr(fc, 8, 1)) +
            dist(substr(fc, 8, 1), substr(fc, 9, 1)) +
            dist(substr(fc, 9, 1), substr(fc, 10, 1)) +
            dist(substr(fc, 10, 1), substr(fc, 11, 1)) +
            dist(substr(fc, 11, 1), substr(fc, 12, 1));
    """)

    lazy_fcs = conn.execute("""
                            SELECT fc, total_moves(fc) as moves
                            FROM fcs
                            ORDER BY moves DESC LIMIT 5
                            """).fetchall()

    for fc, moves in lazy_fcs:
        formatted_fc = f"{fc[0:4]}-{fc[4:8]}-{fc[8:12]}"
        print(f"fc: {formatted_fc} | Stick Moves: {moves}")
    conn.close()