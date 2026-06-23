import pandas as pd
import requests
import os
from sshtunnel import SSHTunnelForwarder
import pymysql
from dotenv import load_dotenv

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

# Function to establish an SSH tunnel and connect to MySQL
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
        print("Connection to MySQL successful!")
        return conn, tunnel
    except Exception as e:
        print(f"Error while connecting to MySQL: {e}")
        return None, None

# Function to execute SQL queries
def execute_query(conn, query, params=None):
    try:
        with conn.cursor() as cursor:
            print("Executing query...")
            cursor.execute(query, params)
            print("Query executed successfully")
    except pymysql.MySQLError as e:
        print(f"MySQL error during query execution: {e}")
    except Exception as e:
        print(f"General error during query execution: {e}")

# Function to construct the URL based on the user's input
def construct_url(base_url, wikiproject_name):
    file_name = f"{wikiproject_name}.csv"
    return f"{base_url}{file_name}"

# Function to download the CSV file
def download_csv(url, local_file_name):
    try:
        # Disable SSL verification
        response = requests.get(url)
        response.raise_for_status()  # Raise an error for bad status
        with open(local_file_name, 'wb') as file:
            file.write(response.content)
        print(f"Downloaded {local_file_name}")
    except Exception as e:
        print(f"Error downloading the file from {url}: {e}")
        return False
    return True

def transform_data(df_revisions, df_pages, wikiproject_name):
    # Convert the timestamp format to 'YYYY-MM-DD HH:MM:SS'
    df_revisions['revision_timestamp'] = pd.to_datetime(df_revisions['revision_timestamp']).dt.strftime('%Y-%m-%d %H:%M:%S')
    
    df_merged = df_revisions.merge(df_pages, on='page_id')
    sorted_df = df_merged.sort_values(by=['page_title', 'revision_timestamp'], ascending=[True, False])
    latest_revisions_df = sorted_df.groupby('page_title').first().reset_index()
    latest_revisions_df['wikiproject'] = wikiproject_name
    return latest_revisions_df

# Function to insert the transformed data into the MySQL database
def save_to_mysql(df, conn):
    try:
        with conn.cursor() as cursor:
            # Insert data into the wikiprojects_data_latest_rev table
            insert_query = """
            INSERT INTO wikiprojects_data_latest_rev (
                page_id,
                item_id,
                revision_id,
                revision_timestamp,
                page_length,
                num_refs,
                num_wikilinks,
                num_categories,
                num_media,
                num_headings,
                pred_qual,
                page_title,
                quality_class,
                importance_class,
                wikiproject
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                revision_id = VALUES(revision_id),
                revision_timestamp = VALUES(revision_timestamp),
                page_length = VALUES(page_length),
                num_refs = VALUES(num_refs),
                num_wikilinks = VALUES(num_wikilinks),
                num_categories = VALUES(num_categories),
                num_media = VALUES(num_media),
                num_headings = VALUES(num_headings),
                pred_qual = VALUES(pred_qual),
                quality_class = VALUES(quality_class),
                importance_class = VALUES(importance_class)
            """
            for _, row in df.iterrows():
                cursor.execute(insert_query, (
                    row['page_id'],
                    row['item_id'],
                    row['revision_id'],
                    row['revision_timestamp'],
                    row['page_length'],
                    row['num_refs'],
                    row['num_wikilinks'],
                    row['num_categories'],
                    row['num_media'],
                    row['num_headings'],
                    row['pred_qual'],
                    row['page_title'],
                    row['quality_class'],
                    row['importance_class'],
                    row['wikiproject']
                ))

            conn.commit()
            print("Data inserted into MySQL successfully.")
    except pymysql.MySQLError as e:
        print(f"MySQL error during data insertion: {e}")
    except Exception as e:
        print(f"General error during data insertion: {e}")

# Main function to execute the script
def main():
    # Base URLs
    revisions_base_url = "https://analytics.wikimedia.org/published/datasets/outreachy-round-28/revisions/"
    assessments_base_url = "https://analytics.wikimedia.org/published/datasets/outreachy-round-28/assessments/"
    
    conn, tunnel = connect_to_db_via_ssh()
    
    if conn and tunnel:
        while True:
            # Prompt the user for the Wikiproject name
            wikiproject_name = input("Enter the Wikiproject name (or type 'exit' to finish): ")
            
            if wikiproject_name.lower() == 'exit':
                break
            
            # Remove the ".csv" extension from the input if provided
            if wikiproject_name.endswith(".csv"):
                wikiproject_name = wikiproject_name[:-4]
            
            # Construct the URLs and local file names
            revisions_url = construct_url(revisions_base_url, wikiproject_name)
            assessments_url = construct_url(assessments_base_url, wikiproject_name)
            revisions_file_name = f"{wikiproject_name}_revisions.csv"
            assessments_file_name = f"{wikiproject_name}_assessments.csv"
            
            # Download the CSV files
            if not download_csv(revisions_url, revisions_file_name):
                continue
            if not download_csv(assessments_url, assessments_file_name):
                continue
            
            # Read the CSV files
            try:
                df_revisions = pd.read_csv(revisions_file_name)
                df_pages = pd.read_csv(assessments_file_name)
            except Exception as e:
                print(f"Error reading the CSV files: {e}")
                continue
            
            # Perform the data transformations
            transformed_df = transform_data(df_revisions, df_pages, wikiproject_name)
            
            # Save the transformed data to a CSV file
            merged_file_name = f"{wikiproject_name}_merged.csv"
            transformed_df.to_csv(merged_file_name, index=False)
            print(f"Saved merged data to {merged_file_name}")

            # Save the transformed data to the MySQL database
            print("Inserting data into MySQL...")
            save_to_mysql(transformed_df, conn)
            
            # Delete the downloaded and merged CSV files
            try:
                os.remove(revisions_file_name)
                os.remove(assessments_file_name)
                os.remove(merged_file_name)
                print(f"Deleted {revisions_file_name}, {assessments_file_name}, and {merged_file_name}")
            except Exception as e:
                print(f"Error deleting the files: {e}")
        
        # Close the MySQL connection and stop the SSH tunnel
        conn.close()
        tunnel.stop()
        print("MySQL connection and SSH tunnel are closed.")

if __name__ == "__main__":
    main()
