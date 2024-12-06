from pywebio.output import put_markdown, clear, use_scope
from utils.config_utils import load_config
from ui.checker_list import display_checker_controls, display_checker
from ui.checker_form import create_checker_form
from ui.actions import handle_checker_action, handle_global_control

def display_checkers(config, save_checker=None):
    if not config['checkers']:
        put_markdown('### No email checkers configured yet')
        return

    put_markdown('### Configured Email Checkers')
    
    def on_filter_change(value):
        clear('checker_list')
        with use_scope('checker_list'):
            for i, checker in enumerate(config['checkers']):
                display_checker(i, checker, 
                              lambda idx, action: handle_checker_action(idx, action, 
                                                                     edit_callback=lambda x: create_checker_form(x, save_checker),
                                                                     refresh_callback=lambda: refresh_display(save_checker)),
                              status_filter=value)
    
    # Add handler for global controls and filter
    display_checker_controls(
        lambda action: handle_global_control(action, lambda: refresh_display(save_checker)),
        on_filter=on_filter_change
    )
    
    # Initial display
    with use_scope('checker_list'):
        for i, checker in enumerate(config['checkers']):
            display_checker(i, checker, 
                          lambda idx, action: handle_checker_action(idx, action, 
                                                                 edit_callback=lambda x: create_checker_form(x, save_checker),
                                                                 refresh_callback=lambda: refresh_display(save_checker)))
    put_markdown('---')

def refresh_display(save_checker=None):
    config = load_config()
    clear('checkers')
    with use_scope('checkers'):
        display_checkers(config, save_checker) 