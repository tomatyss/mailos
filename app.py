from pywebio.input import *
from pywebio.output import *
from pywebio import start_server
import re
import json
import os
from datetime import datetime
import subprocess
from utils.config_utils import load_config, save_config
from check_emails import init_scheduler
from functools import partial
from utils.logger_utils import setup_logger

scheduler = None
logger = setup_logger('web_app')

def validate_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, email):
        return 'Invalid email format'

def display_checkers(config):
    if not config['checkers']:
        put_markdown('### No email checkers configured yet')
        return

    put_markdown('### Configured Email Checkers')
    
    # Add control buttons at the top
    with use_scope('controls'):
        put_buttons([
            {'label': '▶️ Start All', 'value': 'start', 'color': 'success'},
            {'label': '⏸️ Pause All', 'value': 'pause', 'color': 'warning'},
            {'label': '🔄 Check Now', 'value': 'check', 'color': 'primary'}
        ], onclick=handle_control)
    
    for i, checker in enumerate(config['checkers']):
        last_run = checker.get('last_run', 'Never')
        put_markdown(f'''
#### Checker {i + 1}:
- Status: {'✅ Enabled' if checker['enabled'] else '❌ Disabled'}
- Email: {checker['monitor_email']}
- IMAP Server: {checker['imap_server']}:{checker['imap_port']}
- Last Run: {last_run}
        ''')
        put_buttons([
            {'label': '🗑️ Delete', 'value': f'delete_{i}', 'color': 'danger'},
            {'label': '▶️' if not checker['enabled'] else '⏸️', 
             'value': f'toggle_{i}', 
             'color': 'success' if not checker['enabled'] else 'warning'}
        ], onclick=partial(handle_checker_action, i))
    put_markdown('---')

def handle_control(action):
    if action == 'check':
        logger.info("Manual check triggered")
        from check_emails import main
        main()
        toast("Manual check completed")
        refresh_display()
    elif action == 'pause':
        config = load_config()
        for checker in config['checkers']:
            checker['enabled'] = False
        save_config(config)
        toast("All checkers paused")
        refresh_display()
    elif action == 'start':
        config = load_config()
        for checker in config['checkers']:
            checker['enabled'] = True
        save_config(config)
        toast("All checkers started")
        refresh_display()

def handle_checker_action(index, action):
    config = load_config()
    if action.startswith('delete_'):
        config['checkers'].pop(index)
        toast("Checker deleted")
    elif action.startswith('toggle_'):
        config['checkers'][index]['enabled'] = not config['checkers'][index]['enabled']
        status = "enabled" if config['checkers'][index]['enabled'] else "disabled"
        toast(f"Checker {status}")
    
    save_config(config)
    refresh_display()

def refresh_display():
    config = load_config()
    clear('checkers')
    with use_scope('checkers'):
        display_checkers(config)

def check_email_app():
    global scheduler
    if not scheduler:
        logger.info("Initializing scheduler...")
        scheduler = init_scheduler()
    
    put_markdown('# MailOS')
    put_markdown('Configure multiple email accounts to monitor')
    
    config = load_config()
    
    with use_scope('checkers'):
        display_checkers(config)
    
    def add_new_checker():
        # Get configuration for new checker
        checker_config = input_group("New Email Checker Configuration", [
            input("Email to monitor", name="monitor_email", type=TEXT, 
                  validate=validate_email, required=True),
            input("Email password", name="password", type=PASSWORD, required=True),
            input("IMAP Server", name="imap_server", type=TEXT, 
                  value="imap.gmail.com", required=True),
            input("IMAP Port", name="imap_port", type=NUMBER, 
                  value=993, required=True),
            checkbox("Enable monitoring", name="enabled", 
                    options=['Yes'], value=['Yes'])
        ])
        
        checker_config['enabled'] = 'Yes' in checker_config['enabled']
        checker_config['last_run'] = 'Never'
        
        # Add new checker to config
        config['checkers'].append(checker_config)
        
        # Save configuration
        try:
            save_config(config)
            clear('checkers')
            with use_scope('checkers'):
                display_checkers(config)
            put_markdown('## ✅ Configuration Saved')
            
            # Run checker immediately using the existing scheduler
            from check_emails import main
            main()
            toast("Initial check completed")
            
        except Exception as e:
            put_error(f'Failed to save configuration: {str(e)}')

    put_button('Add New Checker', onclick=add_new_checker)

if __name__ == '__main__':
    start_server(check_email_app, port=8080, debug=True) 