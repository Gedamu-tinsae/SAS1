""" from app import create_app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True)  # Enable debug mode for development
 """

from app import create_app
import sys

app = create_app()

if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
    app.run(debug=True, port=port)
