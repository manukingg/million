import mysql.connector
from mysql.connector import Error

db_name = 'users_database'
mysql_password = 'hatbot3401350'
start_counter = 0

def create_db_connection(host_name, user_name, user_password, auth_plug, db_name):
    connection = None
    try:
        connection = mysql.connector.connect(
            host = host_name,
            user = user_name,
            password = user_password,
            auth_plugin = auth_plug,
            database = db_name
        )
        print('MySQL database connection successful')
    except Error as err:
        print(f"Error: '{err}'")
    return connection

connection = create_db_connection('localhost', 'root', mysql_password, 'mysql_native_password', db_name) #connecting to mysql "users_database"

def fetch_one_for_query(cursor, query, *args):
    cursor.execute(query, tuple(args))
    return cursor.fetchone()[0]

def update(cursor, query, *args):
    cursor.execute(query, tuple(args))
    connection.commit()
