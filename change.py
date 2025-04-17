import sqlite3
from werkzeug.security import generate_password_hash

# Connect to your DB
conn = sqlite3.connect('users.db')
cursor = conn.cursor()

# Generate hash
new_hash = generate_password_hash('12345', method='pbkdf2:sha256', salt_length=16)

# IDs of users you want to update
user_ids = (1, 2, 3, 4, 6, 7)

# Update each
for uid in user_ids:
    cursor.execute("UPDATE user SET password_hash = ? WHERE id = ?", (new_hash, uid))

conn.commit()
conn.close()

print("Passwords updated to 12345 for selected users.")
