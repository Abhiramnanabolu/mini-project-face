import psycopg2

DB_HOST = "localhost"
DB_NAME = "evm_face"
DB_USER = "postgres"
DB_PASSWORD = "12345678"

try:
    connection = psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
    )
    cursor = connection.cursor()

    cursor.execute("UPDATE voters SET vote_status = FALSE")

    connection.commit()
    print("Vote status reset to FALSE for all voters.")

except Exception as e:
    print("Error:", e)

finally:
    if connection:
        cursor.close()
        connection.close()
