from app import app, get_db_connection
from werkzeug.security import generate_password_hash
import sqlite3

def criar_usuario_admin():
    with app.app_context():
        conn = get_db_connection()
        try:
            conn.execute(
                'INSERT INTO usuarios (username, password_hash, is_admin) VALUES (?, ?, ?)',
                ('bybenb', generate_password_hash('raizoku'), 1)
            )
            conn.commit()
            print("Usuário admin criado com sucesso!")
            print("Usuário: bybenb")
            print("Senha: raizoku")
        except sqlite3.IntegrityError:
            print("⚠️ O usuário admin já existe!")
        finally:
            conn.close()

if __name__ == '__main__':
    criar_usuario_admin()