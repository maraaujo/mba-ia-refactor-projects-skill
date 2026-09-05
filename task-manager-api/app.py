import datetime

from flask import Flask
from flask_cors import CORS

from config import Config
from database import db
from errors import register_error_handlers
from routes.report_routes import report_bp
from routes.task_routes import task_bp
from routes.user_routes import user_bp


def create_app():
    flask_app = Flask(__name__)
    flask_app.config.from_object(Config)

    CORS(flask_app)
    db.init_app(flask_app)

    flask_app.register_blueprint(task_bp)
    flask_app.register_blueprint(user_bp)
    flask_app.register_blueprint(report_bp)

    register_error_handlers(flask_app)

    @flask_app.route('/health')
    def health():
        return {'status': 'ok', 'timestamp': str(datetime.datetime.now())}

    @flask_app.route('/')
    def index():
        return {'message': 'Task Manager API', 'version': '1.0'}

    with flask_app.app_context():
        db.create_all()

    return flask_app


app = create_app()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
