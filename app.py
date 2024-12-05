from pywebio.input import *
from pywebio.output import *
from pywebio import start_server
import re
from utils.config_utils import load_config, save_config
from check_emails import init_scheduler
from functools import partial
from utils.logger_utils import setup_logger
from vendors.factory import LLMFactory

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
- Auto-reply: {'✅ Enabled' if checker.get('auto_reply', False) else '❌ Disabled'}
- LLM Provider: {checker.get('llm_provider', 'Not configured')}
- Model: {checker.get('model', 'Not configured')}
- Last Run: {last_run}
        ''')
        put_buttons([
            {'label': '🗑️ Delete', 'value': f'delete_{i}', 'color': 'danger'},
            {'label': '✏️ Edit', 'value': f'edit_{i}', 'color': 'primary'},
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
    elif action.startswith('edit_'):
        edit_checker(index)
        return  # Return early as edit_checker handles its own save
    
    save_config(config)
    refresh_display()

def edit_checker(index):
    config = load_config()
    checker = config['checkers'][index]
    llm_providers = list(LLMFactory._providers.keys())
    
    # Pre-select the current features
    current_features = []
    if checker['enabled']:
        current_features.append('Enable monitoring')
    if checker.get('auto_reply', False):
        current_features.append('Auto-reply to emails')

    try:
        updated_config = input_group(f"Edit Email Checker {index + 1}", [
            input("Email to monitor", name="monitor_email", type=TEXT, 
                  validate=validate_email, required=True, value=checker['monitor_email']),
            input("Email password", name="password", type=PASSWORD, required=True,
                  value=checker['password']),
            input("IMAP Server", name="imap_server", type=TEXT, 
                  value=checker['imap_server'], required=True),
            input("IMAP Port", name="imap_port", type=NUMBER, 
                  value=checker['imap_port'], required=True),
            checkbox("Options", name="features", 
                    options=['Enable monitoring', 'Auto-reply to emails'],
                    value=current_features),
            select('LLM Provider', name='llm_provider', options=llm_providers,
                  value=checker.get('llm_provider', llm_providers[0])),
            input("Model Name", name="model", type=TEXT, 
                  value=checker.get('model', ''),
                  placeholder="e.g. gpt-4-turbo-preview or claude-3-sonnet", required=True),
            input("API Key", name="api_key", type=PASSWORD, 
                  value=checker.get('api_key', ''), required=True),
            textarea("System Prompt", name="system_prompt", 
                    value=checker.get('system_prompt', ''),
                    placeholder="Enter the system prompt for the AI assistant...", 
                    required=True)
        ])
        
        # Transform the configuration
        updated_config['enabled'] = 'Enable monitoring' in updated_config['features']
        updated_config['auto_reply'] = 'Auto-reply to emails' in updated_config['features']
        del updated_config['features']
        updated_config['last_run'] = checker['last_run']  # Preserve the last run time
        
        # Update the checker in the config
        config['checkers'][index] = updated_config
        save_config(config)
        toast("Checker updated successfully")
        refresh_display()
        
    except Exception as e:
        toast(f"Failed to update checker: {str(e)}", color='error')
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
        # Get available LLM providers
        llm_providers = list(LLMFactory._providers.keys())
        
        # Get configuration for new checker
        checker_config = input_group("New Email Checker Configuration", [
            input("Email to monitor", name="monitor_email", type=TEXT, 
                  validate=validate_email, required=True),
            input("Email password", name="password", type=PASSWORD, required=True),
            input("IMAP Server", name="imap_server", type=TEXT, 
                  value="imap.gmail.com", required=True),
            input("IMAP Port", name="imap_port", type=NUMBER, 
                  value=993, required=True),
            checkbox("Options", name="features", 
                    options=['Enable monitoring', 'Auto-reply to emails'], 
                    value=['Enable monitoring']),
            select('LLM Provider', name='llm_provider', options=llm_providers),
            input("Model Name", name="model", type=TEXT, 
                  placeholder="e.g. gpt-4-turbo-preview or claude-3-sonnet", required=True),
            input("API Key", name="api_key", type=PASSWORD, required=True),
            textarea("System Prompt", name="system_prompt", 
                    placeholder="Enter the system prompt for the AI assistant...", 
                    required=True)
        ])
        
        # Transform the configuration
        checker_config['enabled'] = 'Enable monitoring' in checker_config['features']
        checker_config['auto_reply'] = 'Auto-reply to emails' in checker_config['features']
        del checker_config['features']  # Remove the temporary features field
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
    # Initialize scheduler before starting the server
    scheduler = init_scheduler()
    start_server(check_email_app, port=8080, debug=True) 