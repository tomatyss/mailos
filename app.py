from pywebio.input import *
from pywebio.output import *
from pywebio.pin import *
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

    # Create the edit form
    with use_scope('edit_checker_form', clear=True):
        put_markdown(f"### Edit Email Checker {index + 1}")
        
        # Basic fields that are always shown
        put_input('monitor_email', type='text', label='Email to monitor',
                 value=checker['monitor_email'])
        put_input('password', type='password', label='Email password',
                 value=checker['password'])
        put_input('imap_server', type='text', label='IMAP Server',
                 value=checker['imap_server'])
        put_input('imap_port', type='number', label='IMAP Port',
                 value=checker['imap_port'])
        put_checkbox('features', options=['Enable monitoring', 'Auto-reply to emails'],
                    value=current_features)
        put_select('llm_provider', options=llm_providers, label='LLM Provider',
                  value=checker.get('llm_provider', llm_providers[0]))
        put_input('model', type='text', label='Model Name',
                 value=checker.get('model', ''),
                 placeholder='e.g. gpt-4-turbo-preview or claude-3-sonnet')
        
        def on_provider_change(provider):
            with use_scope('provider_credentials', clear=True):
                if provider == 'bedrock-anthropic':
                    put_input('aws_access_key', type='password', label='AWS Access Key')
                    put_input('aws_secret_key', type='password', label='AWS Secret Key')
                    put_input('aws_session_token', type='password', label='AWS Session Token (Optional)')
                    put_input('aws_region', type='text', label='AWS Region', value='us-east-1')
                    put_input('model', type='text', label='Model Name',
                             value='anthropic.claude-3-sonnet-20240229-v1:0',
                             placeholder='e.g., anthropic.claude-3-sonnet-20240229-v1:0')
                else:
                    put_input('api_key', type='password', label='API Key')
                    put_input('model', type='text', label='Model Name',
                             placeholder='e.g. gpt-4-turbo-preview or claude-3-sonnet')
        
        # Initial credentials fields based on current provider
        on_provider_change(checker.get('llm_provider', llm_providers[0]))
        
        put_textarea('system_prompt', label='System Prompt',
                    value=checker.get('system_prompt', ''),
                    placeholder='Enter the system prompt for the AI assistant...')
        
        put_button('Save', onclick=lambda: save_edited_checker(index))
        
    # Register provider change event handler
    pin_on_change('llm_provider', onchange=on_provider_change)

def save_edited_checker(index):
    try:
        config = load_config()
        
        # Collect all form data
        updated_config = {
            'monitor_email': pin.monitor_email,
            'password': pin.password,
            'imap_server': pin.imap_server,
            'imap_port': pin.imap_port,
            'features': pin.features,
            'llm_provider': pin.llm_provider,
            'model': pin.model,
            'system_prompt': pin.system_prompt,
        }
        
        # Add provider-specific credentials
        if pin.llm_provider == 'bedrock-anthropic':
            updated_config.update({
                'aws_access_key': pin.aws_access_key,
                'aws_secret_key': pin.aws_secret_key,
                'aws_region': pin.aws_region,
            })
            if hasattr(pin, 'aws_session_token') and pin.aws_session_token:
                updated_config['aws_session_token'] = pin.aws_session_token
        else:
            updated_config['api_key'] = pin.api_key
        
        # Transform the configuration
        updated_config['enabled'] = 'Enable monitoring' in updated_config['features']
        updated_config['auto_reply'] = 'Auto-reply to emails' in updated_config['features']
        del updated_config['features']
        
        # Preserve the last run time
        updated_config['last_run'] = config['checkers'][index].get('last_run', 'Never')
        
        # Update the checker in the config
        config['checkers'][index] = updated_config
        save_config(config)
        
        # Clear the form and refresh display
        clear('edit_checker_form')
        refresh_display()
        toast("Checker updated successfully")
        
    except Exception as e:
        toast(f"Failed to update checker: {str(e)}", color='error')

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
        llm_providers = list(LLMFactory._providers.keys())
        
        # Create the base form
        with use_scope('new_checker_form', clear=True):
            put_markdown("### New Email Checker Configuration")
            
            # Basic fields that are always shown
            put_input('monitor_email', type='text', label='Email to monitor')
            put_input('password', type='password', label='Email password')
            put_input('imap_server', type='text', label='IMAP Server', value='imap.gmail.com')
            put_input('imap_port', type='number', label='IMAP Port', value=993)
            put_checkbox('features', options=['Enable monitoring', 'Auto-reply to emails'])
            put_select('llm_provider', options=llm_providers, label='LLM Provider')
            put_input('model', type='text', label='Model Name',
                     placeholder='e.g. gpt-4-turbo-preview or claude-3-sonnet')
            
            def on_provider_change(provider):
                with use_scope('provider_credentials', clear=True):
                    if provider == 'bedrock-anthropic':
                        put_input('aws_access_key', type='password', label='AWS Access Key')
                        put_input('aws_secret_key', type='password', label='AWS Secret Key')
                        put_input('aws_session_token', type='password', label='AWS Session Token (Optional)')
                        put_input('aws_region', type='text', label='AWS Region', value='us-east-1')
                        put_input('model', type='text', label='Model Name',
                                 value='anthropic.claude-3-sonnet-20240229-v1:0',
                                 placeholder='e.g., anthropic.claude-3-sonnet-20240229-v1:0')
                    else:
                        put_input('api_key', type='password', label='API Key')
                        put_input('model', type='text', label='Model Name',
                                 placeholder='e.g. gpt-4-turbo-preview or claude-3-sonnet')
            
            # Initial credentials fields based on default provider
            on_provider_change(llm_providers[0])
            
            put_textarea('system_prompt', label='System Prompt',
                        placeholder='Enter the system prompt for the AI assistant...')
            
            put_button('Save', onclick=lambda: save_new_checker())
            
        # Register provider change event handler
        pin_on_change('llm_provider', onchange=on_provider_change)

    def save_new_checker():
        try:
            # Collect all form data
            checker_config = {
                'monitor_email': pin.monitor_email,
                'password': pin.password,
                'imap_server': pin.imap_server,
                'imap_port': pin.imap_port,
                'features': pin.features,
                'llm_provider': pin.llm_provider,
                'model': pin.model,
                'system_prompt': pin.system_prompt,
            }
            
            # Add provider-specific credentials
            if pin.llm_provider == 'bedrock-anthropic':
                checker_config.update({
                    'aws_access_key': pin.aws_access_key,
                    'aws_secret_key': pin.aws_secret_key,
                    'aws_region': pin.aws_region,
                })
                if hasattr(pin, 'aws_session_token') and pin.aws_session_token:
                    checker_config['aws_session_token'] = pin.aws_session_token
            else:
                checker_config['api_key'] = pin.api_key
            
            # Transform the configuration
            checker_config['enabled'] = 'Enable monitoring' in checker_config['features']
            checker_config['auto_reply'] = 'Auto-reply to emails' in checker_config['features']
            del checker_config['features']
            checker_config['last_run'] = 'Never'
            
            # Add new checker to config
            config = load_config()
            config['checkers'].append(checker_config)
            save_config(config)
            
            # Clear the form and refresh display
            clear('new_checker_form')
            refresh_display()
            toast("New checker added successfully")
            
            # Run checker immediately
            from check_emails import main
            main()
            toast("Initial check completed")
            
        except Exception as e:
            toast(f"Failed to save configuration: {str(e)}", color='error')

    put_button('Add New Checker', onclick=add_new_checker)

if __name__ == '__main__':
    # Initialize scheduler before starting the server
    scheduler = init_scheduler()
    start_server(check_email_app, port=8080, debug=True) 