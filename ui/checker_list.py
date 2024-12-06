from pywebio.output import put_markdown, put_buttons, use_scope, put_grid, span, put_row, put_column, put_text
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

def display_checker(index, checker, action_callback, status_filter=None):
    """Display a single checker with its controls"""
    if status_filter and status_filter != 'all':
        if (status_filter == 'active' and not checker['enabled']) or \
           (status_filter == 'paused' and checker['enabled']):
            return

    checker_name = checker.get('name', '') or checker['monitor_email']
    last_run = checker.get('last_run', 'Never')
    
    put_markdown(f'''
#### {checker_name}
- Status: {'✅ Active' if checker['enabled'] else '❌ Paused'}
- Email: {checker['monitor_email']}
- IMAP Server: {checker['imap_server']}:{checker['imap_port']}
- Auto-reply: {'✅ Enabled' if checker.get('auto_reply', False) else '❌ Disabled'}
- LLM Provider: {checker.get('llm_provider', 'Not configured')}
- Model: {checker.get('model', 'Not configured')}
- Last Run: {last_run}
    ''')
    
    put_buttons([
        {'label': '✏️ Edit', 'value': f'edit_{index}', 'color': 'info'},
        {'label': ' Copy', 'value': f'copy_{index}', 'color': 'secondary'},
        {'label': '🗑️ Delete', 'value': f'delete_{index}', 'color': 'danger'},
        {'label': '⏹️ Stop' if checker['enabled'] else '▶️ Run', 
         'value': f'toggle_{index}', 
         'color': 'warning' if checker['enabled'] else 'success'}
    ], onclick=lambda val: action_callback(index, val))
    
    put_markdown('---')