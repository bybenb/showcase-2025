import sqlite3


conn = sqlite3.connect('alunos.db')
cursor = conn.cursor()


with open('popular_db.sql', 'r', encoding='utf-8') as sql_file:
    sql_script = sql_file.read()

cursor.executescript(sql_script)
conn.commit()
conn.close()

print("Script SQL executado com sucesso!")