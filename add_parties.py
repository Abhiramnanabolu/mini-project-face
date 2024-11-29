import psycopg2

DB_HOST = "localhost"
DB_NAME = "evm_face"
DB_USER = "postgres"
DB_PASSWORD = "12345678"

parties = [
    (1, "Party A"),
    (2, "Party B"),
    (3, "Party C"),
]

try:
    connection = psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
    )
    cursor = connection.cursor()

    for party_id, party_name in parties:
        cursor.execute(
            "INSERT INTO party (id, party_name) VALUES (%s, %s) ON CONFLICT (id) DO NOTHING",
            (party_id, party_name),
        )

    connection.commit()
    print("Parties added successfully.")

except Exception as e:
    print("Error:", e)

finally:
    if connection:
        cursor.close()
        connection.close()
