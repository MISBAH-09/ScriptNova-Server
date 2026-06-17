import MySQLdb

# Connect to MySQL
connection = MySQLdb.connect(
    host='localhost',
    user='root',
    passwd='root123'
)

cursor = connection.cursor()
cursor.execute("CREATE DATABASE IF NOT EXISTS ScriptNova")
cursor.close()
connection.commit()
connection.close()

print("Database ScriptNova created successfully!")
