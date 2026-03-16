from apps.authentication import blueprint

@blueprint.route('/login')
def login():
    return 'Login Page'