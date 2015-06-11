# -*- coding: utf-8 -*-

def init_app(app):
    from . import index
    app.register_blueprint(index.mod)
    from . import moteur
    app.register_blueprint(moteur.mod)
    from . import operateur
    app.register_blueprint(operateur.mod)
