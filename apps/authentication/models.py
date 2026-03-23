import sqlite3
from flask_login import UserMixin
from apps import login_manager
from apps.models import connect_db
from apps.authentication.util import hash_password, verify_password

class Users(UserMixin):
    """
    Model untuk pengguna, menggunakan Flask-Login.
    """

    def __init__(self, id, username, email):
        self.id = id
        self.username = username
        self.email = email

    def get_id(self):
        return str(self.id)

    @staticmethod
    def register_user(username: str, email: str, password: str) -> tuple:
        """
        Mendaftarkan user baru ke database.

        Args:
            username (str): Nama pengguna
            email (str): Email pengguna
            password (str): Password dalam bentuk plain text

        Returns:
            tuple(bool, str): (True, "Register berhasil") jika sukses,
                              (False, "pesan error") jika gagal
        """
        conn = connect_db()
        cursor = conn.cursor()
        try:
            hashed = hash_password(password)
            cursor.execute(
                "INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
                (username, email, hashed)
            )
            conn.commit()
            return True, "Register berhasil"
        except sqlite3.IntegrityError:
            # UNIQUE constraint violation (username atau email sudah ada)
            return False, "Username atau email sudah digunakan"
        except Exception as e:
            # Log error untuk debugging
            print(f"Error register_user: {e}")
            return False, "Terjadi kesalahan, silakan coba lagi"
        finally:
            conn.close()

    @staticmethod
    def login_check(user_input: str, password: str) -> tuple:
        """
        Memeriksa kredensial login.

        Args:
            user_input (str): Username atau email
            password (str): Password plain text

        Returns:
            tuple(bool, any): (True, user_dict) jika sukses,
                              (False, pesan_error) jika gagal
        """
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM users WHERE username = ? OR email = ?",
            (user_input, user_input)
        )
        user = cursor.fetchone()
        conn.close()

        if not user:
            return False, "Username/Email atau password salah"

        if verify_password(password, user["password"]):
            # user adalah sqlite3.Row, konversi ke dict jika perlu
            return True, dict(user)

        return False, "Username/Email atau password salah"


@login_manager.user_loader
def load_user(user_id):
    """
    Memuat user berdasarkan ID untuk Flask-Login.
    """
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()

    if user:
        return Users(
            id=user["id"],
            username=user["username"],
            email=user["email"]
        )
    return None