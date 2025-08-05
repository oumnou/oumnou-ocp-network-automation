from flask import Flask
from routes import init_routes

app = Flask(__name__, static_folder='static', template_folder='templates')
init_routes(app)

if __name__ == '__main__':
    app.run(debug=True)
