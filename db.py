import mysql.connector.pooling
from mysql.connector import Error

db_name = 'users_database'
mysql_password = 'hatbot3401350'

def create_db_connection(pool_name, pool_size, host_name, user_name, user_password, auth_plug, db_name):
    connection_pool = mysql.connector.pooling.MySQLConnectionPool(
        pool_name = pool_name,
        pool_size = pool_size,
        host = host_name,
        user = user_name,
        password = user_password,
        auth_plugin = auth_plug,
        database = db_name
    )
    return connection_pool

connection_pool = create_db_connection('my_pool', 5, '35.232.202.42', 'root', mysql_password, 'mysql_native_password', db_name) #connecting to mysql "users_database"

def fetch_one_for_query(cursor, query, *args):
    cursor.execute(query, tuple(args))
    return cursor.fetchone()[0]
    
def fetch_row_for_query(cursor, query, *args):
    cursor.execute(query, tuple(args))
    return cursor.fetchone()
    

def fetch_all_for_query(cursor, query, *args):
    cursor.execute(query, tuple(args))
    return cursor.fetchall()

def update(cursor, query, *args):
    cursor.execute(query, tuple(args))