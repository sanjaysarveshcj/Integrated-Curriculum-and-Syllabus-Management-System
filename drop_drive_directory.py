from app import app, db

with app.app_context():
    # Drop the drive_directory table manually
    db.engine.execute('DROP TABLE IF EXISTS drive_directory')
    db.session.commit()
