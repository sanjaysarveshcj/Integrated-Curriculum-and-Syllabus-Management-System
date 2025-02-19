from app import app, db
from models import DocumentApproval

with app.app_context():
    # Add the new column
    with db.engine.connect() as conn:
        conn.execute('ALTER TABLE document_approval ADD COLUMN document_name VARCHAR(255)')
        db.session.commit()
