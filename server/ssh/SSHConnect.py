from sshtunnel import SSHTunnelForwarder
import pymysql
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '.env'))

# Database configuration from environment variables
SSH_HOST = os.getenv('SSH_HOST')
SSH_USER = os.getenv('SSH_USER')
SSH_KEY_FILE = os.getenv('SSH_KEY_FILE')
MYSQL_HOST = os.getenv('MYSQL_HOST')
MYSQL_PORT = int(os.getenv('MYSQL_PORT'))
MYSQL_USER = os.getenv('MYSQL_USER')
MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD')
MYSQL_DATABASE = os.getenv('MYSQL_DATABASE')

def connect_to_db_via_ssh():
    try:
        tunnel = SSHTunnelForwarder(
            (SSH_HOST, 22),
            ssh_username=SSH_USER,
            ssh_private_key=SSH_KEY_FILE,
            remote_bind_address=(MYSQL_HOST, MYSQL_PORT)
        )
        tunnel.start()
        print("SSH Tunnel established")
        conn = pymysql.connect(
            host='127.0.0.1',
            port=tunnel.local_bind_port,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DATABASE,
            connect_timeout=30,
            read_timeout=30,
            autocommit=True  # Enable autocommit
        )
        print("Connection successful!")
        return conn, tunnel
    except Exception as e:
        print(f"Error while connecting to MySQL: {e}")
        return None, None

def execute_query(query):
    conn, tunnel = connect_to_db_via_ssh()
    if conn and tunnel:
        try:
            with conn.cursor() as cursor:
                print("Executing query...")
                cursor.execute(query)
                result = cursor.fetchall()
                print("Query executed successfully")
                return result
        except pymysql.MySQLError as e:
            print(f"MySQL error during query execution: {e}")
        except Exception as e:
            print(f"General error during query execution: {e}")
        finally:
            conn.close()
            tunnel.stop()
            print("MySQL connection and SSH tunnel are closed")
    else:
        print("Failed to connect to MySQL using SSH tunnel.")
        return None

if __name__ == "__main__":
    query = "SHOW DATABASES;"
    result = execute_query(query)
    if result:
        for row in result:
            print(row)
    else:
        print("No data retrieved.")
