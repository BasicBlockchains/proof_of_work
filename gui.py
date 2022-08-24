'''
Main File for GUI
'''
import threading

import PySimpleGUI as sg

from api import run_app
from node import Node

# --- CONSTANTS --- #
DEFAULT_THEME = 'SystemDefault'
DEFAULT_WINDOW_SIZE = (800, 600)


# --- MAIN GUI WINDOW --- #
def create_window(theme=DEFAULT_THEME):
    sg.theme(theme)
    sg.set_global_icon('./images/logo_icon.png')
    sg.set_options(font='Ubuntu 12')

    # --- Main Menu --- #
    menu_layout = [
        ['&File',
         ['&Open Blockchain', 'Open &Wallet', '---', '&Save Blockchain', 'Save Blockchain &As', '---', 'E&xit']],
        ['&Endpoints',
         ['height', 'node_list', 'transaction', 'block',
          ['<height>', 'ids', 'headers',
           ['<height>']
           ], 'raw_block',
          ['<height>'], 'utxo',
          ['<tx_id>',
           ['<index>']
           ]
          ]
         ],
        ['&Help', ['Abo&ut BB POW', '&Contact']]
    ]

    # --- Status Tab --- #
    icon_column = [
        [sg.Text('SERVER:', justification='right', auto_size_text=False, size=(12, 1)),
         sg.Image('./images/red_circle_small.png', key='-server_icon-')],
        [sg.Text('NETWORK:', justification='right', auto_size_text=False, size=(12, 1)),
         sg.Image('./images/red_circle_small.png', key='-network_icon-')],
        [sg.Text('MINING:', justification='right', auto_size_text=False, size=(12, 1)),
         sg.Image('./images/red_circle_small.png', key='-mining_icon-')]
    ]

    status_tab_layout = [
        [
            sg.Push(),
            sg.Text("Welcome to the BB POW!", justification='center', auto_size_text=False, size=(48, 1),
                    font="Ubuntu 18"),
            sg.Push()
        ],

        [sg.Push(), sg.Image('./images/logo_icon.png', enable_events=True, key='-logo-'), sg.Push()],
        [
            sg.Push(),
            sg.Text('SERVER:', justification='right', auto_size_text=False, size=(12, 1)),
            sg.Image('./images/red_circle_small.png', key='-server_icon-'),
            sg.Text('NETWORK:', justification='right', auto_size_text=False, size=(12, 1)),
            sg.Image('./images/red_circle_small.png', key='-network_icon-'),
            sg.Text('MINING:', justification='right', auto_size_text=False, size=(12, 1)),
            sg.Image('./images/red_circle_small.png', key='-mining_icon-'),
            sg.Push()
        ],
        [sg.HorizontalSeparator(pad=10, color='#000000')],
        [
            sg.InputText(key='-logs-', expand_x=True, expand_y=True, disabled=True, use_readonly_for_disable=True,
                         disabled_readonly_background_color='#ffffff', border_width=10)
        ]
    ]

    # --- Node Tab --- #

    node_column = [
        [
            sg.Text('Web Server:', justification='left', auto_size_text=False, size=(10, 1)),
            sg.Text(key='-webserver-', justification='left', auto_size_text=False, size=(24, 1))
        ],
        [sg.HorizontalSeparator(pad=5, color='#000000')],
        [sg.Text('NODE IP:', justification='right', auto_size_text=False, size=(16, 1)),
         sg.Text(key='-node_ip-', justification='left', auto_size_text=False, size=(16, 1))],
        [sg.Text('NODE PORT:', justification='right', auto_size_text=False, size=(16, 1)),
         sg.Text(key='-node_port-', justification='left', auto_size_text=False, size=(16, 1))],
        [sg.HorizontalSeparator(pad=5, color='#000000')],
        [sg.Text('SELECTED IP:', justification='right', auto_size_text=False, size=(16, 1)),
         sg.InputText(justification='left', size=(16, 1), background_color='#FFFFFF', key='-selected_ip-')],
        [sg.Text('SELECTED PORT:', justification='right', auto_size_text=False, size=(16, 1)),
         sg.InputText(justification='left', size=(16, 1), background_color='#FFFFFF', key='-selected_port-')],
        [sg.Push(), sg.Button('PING', size=(10, 2), key='-ping-'),
         sg.Push()],
        [sg.HorizontalSeparator(pad=5, color='#000000')],

    ]

    node_table_headings = ['IP ADDRESS', 'PORT', 'PING (ms)', 'LAST CONTACT (s)']
    node_table_column_widths = [len(node_heading) + 2 for node_heading in node_table_headings]

    node_table_column = [
        [
            sg.Push(),
            sg.Text('Node List'),
            sg.Push()
        ],
        [sg.Table(values=[], headings=node_table_headings, expand_y=True, expand_x=True, auto_size_columns=False,
                  col_widths=node_table_column_widths, key='-node_list_table-', bind_return_key=True)],
        [sg.Push(),
         sg.Button('CONNECT', button_color='#00AA00', size=(10, 2), tooltip='Connect to network', key='-connect-'),
         sg.Button('DISCONNECT', button_color='#FF0000', size=(10, 2), key='-disconnect-'), sg.Push()],
    ]

    node_tab_layout = [
        [sg.Column(node_column, vertical_alignment='center', pad=50, expand_y=True),
         sg.Column(node_table_column, expand_x=True, expand_y=True)
         ]
    ]

    # --- Mining Tab --- #

    mining_info_labels = [
        [sg.Text('Block Target:')],
        [sg.Text('Mining Reward:')],
        [sg.Text('Mine Amount Left:')]
    ]
    mining_info_values = [
        [sg.InputText(key='-miner_target-', disabled=True, use_readonly_for_disable=True, size=(24, 1),
                      justification='center')],
        [sg.InputText(key='-miner_reward-', disabled=True, use_readonly_for_disable=True, size=(24, 1),
                      justification='center')],
        [sg.InputText(key='-total_mining_amount-', disabled=True, use_readonly_for_disable=True, size=(24, 1),
                      justification='center')]

    ]
    mining_tx_headers = ['Transaction ID']
    mining_tx_column_widths = [48]
    validated_tx_column = [
        [
            sg.Push(),
            sg.Text('Validated Transactions'),
            sg.Push()
        ],
        [
            sg.Table(key='-validated_tx_table-', headings=mining_tx_headers, auto_size_columns=False,
                     col_widths=mining_tx_column_widths, values=[], expand_y=True, expand_x=True)
        ],
        [
            sg.Push(),
            sg.Text('Current Fees:'),
            sg.InputText(key='-current_fees-', disabled=True, use_readonly_for_disable=True, size=(24, 1)),
            sg.Push()
        ],
        [sg.HorizontalSeparator(color='#000000')],
        [
            sg.Push(),
            sg.Text('Orphaned Transactions'),
            sg.Push()
        ],
        [
            sg.Table(key='-orphaned_tx_table-', headings=mining_tx_headers, auto_size_columns=False,
                     col_widths=mining_tx_column_widths, values=[], expand_y=True, expand_x=True)
        ]
    ]
    block_tx_column = [
        [
            sg.Push(),
            sg.Text('Transactions being Mined'),
            sg.Push()
        ],
        [
            sg.Table(key='-block_tx_table-', headings=mining_tx_headers, auto_size_columns=False,
                     col_widths=mining_tx_column_widths, values=[], expand_x=True, expand_y=True)
        ],
        [
            sg.Push(),
            sg.Text('Block Fees:'),
            sg.InputText(key='-block_fees-', disabled=True, use_readonly_for_disable=True, size=(24, 1)),
            sg.Push()
        ]
    ]

    mining_tab_layout = [
        [
            sg.Push(),
            sg.Column(mining_info_labels),
            sg.Column(mining_info_values),
            sg.Push(),
            sg.Button('START MINER', auto_size_button=False, size=(12, 2), key='-start_miner-', button_color='#00AA00'),
            sg.Button('STOP MINER', auto_size_button=False, size=(12, 2), key='-stop_miner-', button_color='#FF0000'),
            sg.Push()
        ],
        [sg.HorizontalSeparator(color='#000000')],
        [
            sg.Column(validated_tx_column, expand_y=True, expand_x=True),
            sg.VerticalSeparator(color='#000000'),
            sg.Column(block_tx_column, expand_y=True, expand_x=True),
        ]
    ]

    # --- Wallet Tab --- #

    funds_column = [
        [sg.Text('Available:', justification='right', auto_size_text=False, size=(10, 1)),
         sg.InputText('0', disabled=True, use_readonly_for_disable=True, justification='right', size=(16, 1),
                      key='-wallet_available-')],
        [sg.Text('Locked:', justification='right', auto_size_text=False, size=(10, 1)),
         sg.InputText('0', disabled=True, use_readonly_for_disable=True, justification='right', size=(16, 1),
                      key='-wallet_locked-')],
        [sg.Text('Balance:', justification='right', auto_size_text=False, size=(10, 1)),
         sg.InputText('0', disabled=True, use_readonly_for_disable=True, justification='right', size=(16, 1),
                      key='-wallet_balance-')],

    ]

    send_column = [
        [sg.Text('Send to:', justification='right', auto_size_text=False, size=(10, 1)),
         sg.InputText(size=(40, 1), justification='right', key='-wallet_sendto-')],
        [sg.Text('Amount:', justification='right', auto_size_text=False, size=(10, 1)),
         sg.InputText(size=(40, 1), justification='right', key='-wallet_amount-')],
        [sg.Text('Fees:', justification='right', auto_size_text=False, size=(10, 1)),
         sg.InputText(size=(40, 1), justification='right', key='-wallet_fees-')]

    ]

    wallet_utxo_table_headers = ['tx_id', 'tx_index', 'amount', 'block_height']
    wallet_utxo_column_widths = [len(header) + 2 for header in wallet_utxo_table_headers]

    wallet_tab_layout = [
        [
            sg.Push(),
            sg.Text('ADDRESS:'),
            sg.InputText(key='-wallet_address-', disabled=True, use_readonly_for_disable=True, size=(44, 1),
                         justification='center'),
            sg.Push()
        ],
        [
            sg.Push(),
            sg.Column(funds_column), sg.Column(send_column),
            sg.Push()
        ],
        [sg.Push(), sg.Button('Send Funds', key='-wallet_send_funds-'), sg.Push()],
        [sg.HorizontalSeparator(color='#000000')],
        [
            sg.Table(values=[], headings=wallet_utxo_table_headers, auto_size_columns=False,
                     col_widths=wallet_utxo_column_widths, expand_y=True, expand_x=True, pad=10, key='-utxo_table-'),

        ]

    ]

    # --- Tab Group --- #
    tab_group = [
        [
            sg.TabGroup(
                [[sg.Tab('Status', status_tab_layout, key='-status_tab-'),
                  sg.Tab('Node', node_tab_layout, key='-node_tab-'),
                  sg.Tab('Miner', mining_tab_layout, key='-miner_tab-'),
                  sg.Tab('Wallet', wallet_tab_layout, key='-wallet_tab-')
                  ]],
                tab_location='topleft', border_width=5, expand_x=True, expand_y=True, key='-tab_group-',
                enable_events=True
            ),
        ]
    ]

    # --- Main Layout --- #

    layout = [
        [sg.Menu(menu_layout)],
        [
            tab_group
        ],
        [
            sg.Push(),
            sg.Text('\xa9 Basic Blockchains 2022', font='Ubuntu 8'),
            sg.Push(),
        ]
    ]

    return sg.Window('BB POW', layout, size=DEFAULT_WINDOW_SIZE, resizable=True, finalize=True)


def run_node_gui():
    # Setup Window
    window = create_window()
    window.set_min_size((1200, 800))

    # Start Node
    node = Node()

    # Run app with waitress
    app_thread = threading.Thread(target=run_app, daemon=True, args=(node,))
    app_thread.start()

    # Set starting variables
    ip = node.ip
    port = node.assigned_port
    url = f'http://{ip}:{port}/'

    window['-node_ip-'].update(ip)
    window['-node_port-'].update(port)
    window['-webserver-'].update(url)

    # Verify webserver is running
    if app_thread.is_alive():
        window['-server_icon-'].update('./images/green_circle_small.png')

    # GUI LOOP
    while True:
        event, values = window.read(timeout=10)

        if event in [sg.WIN_CLOSED, 'Exit']:
            break

        if event == '-start_miner-':
            node.start_miner()

        if event == '-stop_miner-':
            node.stop_miner()

        if event == '-logo-':
            print(f'Webserver running at http://{node.ip}:{node.assigned_port}')

        if not app_thread.is_alive():
            window['-server_icon-'].update('./images/red_circle_small.png')

    # Cleanup
    if node.is_mining:
        node.stop_miner()
    window.close()


if __name__ == '__main__':
    run_node_gui()
