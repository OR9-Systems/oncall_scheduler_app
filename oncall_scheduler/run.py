from oncallapp import app, db
from flask_migrate import Migrate, upgrade
import os
import logging


def setup_database():
     # Push an application context to ensure the app's context is available
    with app.app_context():
        # Initialize the migrations folder if it doesn't exist
        if not os.path.exists('migrations'):
            os.system('flask db init')

        # Generate the migration scripts
        os.system('flask db migrate -m "Initial migration."')

        # Apply the migrations to the database
        upgrade()



if __name__ == "__main__":
    # Set up the database before running the app
    setup_database()

    # Run the Flask app
    logging.basicConfig(level=logging.DEBUG)
    app.run(debug=True, port=os.environ.get('PORT', 5000))