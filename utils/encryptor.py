from cryptography.fernet import Fernet
import os
print(Fernet.generate_key().decode())

def get_fernet():
    key = os.getenv("ENCRYPTION_KEY")
    return Fernet(key.encode())

def encrypt_password(password: str) -> str:
    return get_fernet().encrypt(password.encode()).decode()

def decrypt_password(encrypted: str) -> str:
    return get_fernet().decrypt(encrypted.encode()).decode()
