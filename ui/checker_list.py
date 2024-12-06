from pywebio.output import put_markdown, put_buttons, use_scope, put_grid, span
from pywebio.pin import put_select, pin_on_change
from functools import partial

def display_checker_controls(on_control, on_filter=None):
    """Display the top control buttons"""
    with use_scope('controls', clear=True):
        put_grid([
            [
                put_buttons([
                    {'label': '▶️ Start All', 'value': 'start', 'color': 'success'},
                    {'label': '⏸️ Pause All', 'value': 'pause', 'color': 'warning'},
                    {'label': ' Check Now', 'value': 'check', 'color': 'primary'}
                ], onclick=on_control),
                put_select('status_filter', [
                    {'label': 'All Checkers', 'value': 'all'},
                    {'label': 'Active Only', 'value': 'active'},
                    {'label': 'Inactive Only', 'value': 'inactive'}
                ], value='all', help_text='Filter checkers by status')
            ]
        ])
        if on_filter:
            pin_on_change('status_filter', onchange=on_filter)

def display_checker(index, checker, on_action, status_filter='all'):
    """Display a single checker"""
    # Apply filter
    if status_filter == 'active' and not checker['enabled']:
        return
    if status_filter == 'inactive' and checker['enabled']:
        return
        
    last_run = checker.get('last_run', 'Never')
    put_markdown(f'''
#### Checker {index + 1}:
- Status: {'✅ Enabled' if checker['enabled'] else '❌ Disabled'}
- Email: {checker['monitor_email']}
- IMAP Server: {checker['imap_server']}:{checker['imap_port']}
- Auto-reply: {'✅ Enabled' if checker.get('auto_reply', False) else '❌ Disabled'}
- LLM Provider: {checker.get('llm_provider', 'Not configured')}
- Model: {checker.get('model', 'Not configured')}
- Last Run: {last_run}
    ''')
    
    put_buttons([
        {'label': '🗑️ Delete', 'value': f'delete_{index}', 'color': 'danger'},
        {'label': '✏️ Edit', 'value': f'edit_{index}', 'color': 'primary'},
        {'label': '▶️' if not checker['enabled'] else '⏸️', 
         'value': f'toggle_{index}', 
         'color': 'success' if not checker['enabled'] else 'warning'}
    ], onclick=lambda action: on_action(index, action))