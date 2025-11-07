from werkzeug.security import generate_password_hash

hash_password = generate_password_hash("admin123")
print(hash_password)
