import json
import bcrypt

VAULT_FILE = "vault.json"

def load_vault():
    try:
        with open(VAULT_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}

def save_vault(vault):
    with open(VAULT_FILE, "w") as f:
        json.dump(vault, f, indent=2)


def get_master_pass(user_id):
    vault = load_vault()
    user = str(user_id)
    return vault.get(user, {}).get("master_pass")

def set_master_pass(user_id, plain_pass):
    vault = load_vault()
    user = str(user_id)
    hashed = bcrypt.hashpw(plain_pass.encode(), bcrypt.gensalt()).decode()
    if user not in vault:
        vault[user] = {}
    vault[user]["master_pass"] = hashed
    save_vault(vault)

def verify_master_pass(user_id, plain_pass):
    hashed = get_master_pass(user_id)
    if not hashed:
        return False
    return bcrypt.checkpw(plain_pass.encode(), hashed.encode())


def store_password(user_id, service, encrypted):
    vault = load_vault()
    user = str(user_id)
    if user not in vault:
        vault[user] = {}
    vault[user][service] = encrypted
    save_vault(vault)

def get_password(user_id, service=None, full_dump=False):
    vault = load_vault()
    user = str(user_id)
    if user not in vault:
        return None
    if full_dump:

        return {k: v for k, v in vault[user].items() if k != "master_pass"}
    if service:
        return vault[user].get(service)
    return None

def delete_password(user_id, service):
    vault = load_vault()
    user = str(user_id)
    if user not in vault or service not in vault[user]:
        return False
    del vault[user][service]
    save_vault(vault)
    return True

def get_all_services(user_id):
    vault = load_vault()
    user = str(user_id)
    if user not in vault:
        return []
    return [k for k in vault[user].keys() if k != "master_pass"]