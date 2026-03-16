from flask import Blueprint

blueprint = Blueprint(
    'dashboard',
    __name__,
    url_prefix='/dashboard'
)

