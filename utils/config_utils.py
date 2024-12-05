import json
import os

CONFIG_FILE = 'email_config.json'

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {'checkers': []}

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f) 