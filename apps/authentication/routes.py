"""
Module      : apps.authentication.routes
Author      : Keyfin Suratman
Description : Blueprint untuk fitur autentikasi (login, register, logout)
"""

from flask                      import render_template, request, session, jsonify, url_for, redirect
from flask_login                import login_user, logout_user, current_user, login_required

from apps.authentication        import blueprint
from apps.authentication.models import Users


# ==========================
# ROUTE: Login
# ==========================
@blueprint.route('/login', methods=['GET', 'POST'])
def login():
    # Kalau sudah login, langsung ke dashboard
    if current_user.is_authenticated:
        return redirect(url_for('dashboard_blueprint.dashboard'))

    # Handle POST (login)
    if request.method == 'POST':
        user_input = request.form.get('email')
        password = request.form.get('password')

        # Validasi input
        if not user_input or not password:
            return jsonify({
                "success": False,
                "message": "Email/Username dan password wajib diisi"
            })

        success, user = Users.login_check(user_input, password)

        if not success:
            return jsonify({
                "success": False,
                "message": user
            })

        # Buat object user untuk Flask-Login
        user_obj = Users(
            id=user["id"],
            username=user["username"],
            email=user["email"]
        )

        login_user(user_obj)

        return jsonify({
            "success": True,
            "message": "Login berhasil"
        })

    # Handle GET (tampilkan halaman login)
    return render_template('authentication/login.html')




# ==========================
# ROUTE: Register
# ==========================
@blueprint.route('/register', methods=['POST'])
def register():
    """
    Menangani pendaftaran user baru.

    Request Form (POST):
        email    : str -> Email user
        password : str -> Password user (minimal 6 karakter)

    Response (JSON):
        success : bool
        message : str
    """
    username = request.form.get('username')
    email = request.form.get('email')
    password = request.form.get('password')

    # Validasi input
    if not username or not email or not password:
        return jsonify({"success": False, "message": "Semua field harus diisi"})

    if len(password) < 6:
        return jsonify({"success": False, "message": "Password minimal 6 karakter"})

    # Panggil fungsi register dari model
    success, message = Users.register_user(username, email, password)

    return jsonify({"success": success, "message": message})


# ==========================
# ROUTE: Logout
# ==========================
@blueprint.route('/logout')
@login_required
def logout():
    """
    Logout user menggunakan Flask-Login.
    """
    logout_user()
    return redirect(url_for('authentication_blueprint.login'))