from apps.dashboard import blueprint

@blueprint.route('/')
def dashboard():   
    return 'Dashboard Page'