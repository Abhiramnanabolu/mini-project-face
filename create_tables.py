import psycopg2
from psycopg2 import sql
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

def create_database():
    try:
        conn = psycopg2.connect(
            dbname="postgres",
            user="postgres",
            password="12345678",
            host="localhost"
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()

        cur.execute(sql.SQL("CREATE DATABASE {}").format(
            sql.Identifier('evm_face')
        ))

        cur.close()
        conn.close()
        print("Database 'evm_face' created successfully.")
    except psycopg2.Error as e:
        print(f"Error creating database: {e}")

def create_tables():
    try:
        conn = psycopg2.connect(
            dbname="evm_face",
            user="postgres",
            password="12345678",
            host="localhost"
        )
        cur = conn.cursor()

        cur.execute("""
            CREATE TABLE voters (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                image BYTEA NOT NULL,
                vote_status BOOLEAN DEFAULT FALSE
            )
        """)

        cur.execute("""
            CREATE TABLE party (
                id SERIAL PRIMARY KEY,
                party_name VARCHAR(100) NOT NULL,
                votes INTEGER DEFAULT 0
            )
        """)

        conn.commit()
        cur.close()
        conn.close()
        print("Tables created successfully.")
    except psycopg2.Error as e:
        print(f"Error creating tables: {e}")

if __name__ == "__main__":
    create_database()
    create_tables()