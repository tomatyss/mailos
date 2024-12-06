from pywebio.output import toast
from utils.config_utils import load_config, save_config
import check_emails

def handle_global_control(action, refresh_callback):
    """Handle global control actions (start/pause/check all)"""
    if action == 'check':
        check_emails.main()
        toast("Manual check completed")
        refresh_callback()
    elif action in ['pause', 'start']:
        config = load_config()
        for checker in config['checkers']:
            checker['enabled'] = (action == 'start')
        save_config(config)
        toast(f"All checkers {'started' if action == 'start' else 'paused'}")
        refresh_callback()

def handle_checker_action(index, action, edit_callback=None, refresh_callback=None):
    """Handle individual checker actions (delete/edit/toggle/copy)"""
    config = load_config()
    
    if action.startswith('delete_'):
        config['checkers'].pop(index)
        toast("Checker deleted")
        save_config(config)
        refresh_callback()
        return True
    elif action.startswith('toggle_'):
        config['checkers'][index]['enabled'] = not config['checkers'][index]['enabled']
        status = "enabled" if config['checkers'][index]['enabled'] else "disabled"
        toast(f"Checker {status}")
        save_config(config)
        refresh_callback()
        return True
    elif action.startswith('edit_'):
        if edit_callback:
            edit_callback(index)
        return False
    elif action.startswith('copy_'):
        # Create a copy of the checker
        new_checker = config['checkers'][index].copy()
        new_checker['name'] = f"{new_checker.get('name', '')} (Copy)"
        new_checker['enabled'] = False  # Start disabled by default
        new_checker['last_run'] = 'Never'
        config['checkers'].append(new_checker)
        save_config(config)
        toast("Checker copied")
        refresh_callback()
        return True
    return True 