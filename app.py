from pywebio.input import *
from pywebio.output import *
from pywebio.pin import *
from pywebio import start_server
from utils.config_utils import load_config, save_config
from check_emails import init_scheduler
from utils.logger_utils import setup_logger
from ui.checker_form import create_checker_form
from ui.checker_list import display_checker_controls, display_checker
from ui.actions import handle_global_control, handle_checker_action
from ui.display import display_checkers, refresh_display

scheduler = None
logger = setup_logger('web_app')

def save_checker(index=None):
    try:
        config = load_config()
        
        # Collect form data
        checker_config = {
            'name': pin.checker_name,
            'monitor_email': pin.monitor_email,
            'password': pin.password,
            'imap_server': pin.imap_server,
            'imap_port': pin.imap_port,
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
        
        # Transform configuration
        checker_config['enabled'] = 'Enable monitoring' in pin.features
        checker_config['auto_reply'] = 'Auto-reply to emails' in pin.features
        
        if index is not None:
            # Preserve last run time for existing checker
            checker_config['last_run'] = config['checkers'][index].get('last_run', 'Never')
            config['checkers'][index] = checker_config
        else:
            checker_config['last_run'] = 'Never'
            config['checkers'].append(checker_config)
        
        save_config(config)
        clear('edit_checker_form' if index is not None else 'new_checker_form')
        refresh_display()
        toast(f"Checker {'updated' if index is not None else 'added'} successfully")
        
        if index is None:  # Run new checker immediately
            from check_emails import main
            main()
            toast("Initial check completed")
            
    except Exception as e:
        toast(f"Failed to save configuration: {str(e)}", color='error')

def check_email_app():
    global scheduler
    if not scheduler:
        logger.info("Initializing scheduler...")
        scheduler = init_scheduler()
    
    put_markdown('# MailOS')
    put_markdown('Configure multiple email accounts to monitor')
    
    config = load_config()
    
    with use_scope('checkers'):
        display_checkers(config, save_checker)
    
    put_button('Add New Checker', onclick=lambda: create_checker_form(on_save=save_checker))

if __name__ == '__main__':
    scheduler = init_scheduler()
    start_server(check_email_app, port=8080, debug=True) 