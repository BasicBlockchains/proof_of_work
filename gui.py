'''
Main File for GUI
'''
import _tkinter
import logging
import os.path
import threading
import time
from pathlib import Path
from tkinter import Tk

import PySimpleGUI as sg

from api import run_app
from blockchain import Blockchain
from decoder import Decoder
from formatter import Formatter
from node import Node
from timestamp import utc_to_seconds, seconds_to_utc
from wallet import Wallet

# --- CONSTANTS --- #
DEFAULT_THEME = 'SystemDefault'
DEFAULT_WINDOW_SIZE = (800, 600)
buffer = ''


# --- ABOUT WINDOW --- #
def create_about_window(theme=DEFAULT_THEME):
    sg.theme(theme)
    sg.set_global_icon('./images/logo_icon.png')
    sg.set_options(font='Ubuntu 12', )

    main_layout = [
        [
            sg.Push(),
            sg.Text("The BB POW is a proof-of-work blockchain, written entirely in python.\n"
                    "For more information please visit http://www.basicblockchains.com/\n\n"
                    f"Current version: {Formatter.VERSION}\n"
                    f"Contact: basicblockchains@gmail.com\n"
                    f""),
            sg.Push()
        ]
    ]

    return sg.Window('ABOUT', main_layout, resizable=False, finalize=True)




# --- PORT WINDOW --- #
def create_port_window(theme=DEFAULT_THEME):
    sg.theme(theme)
    sg.set_global_icon('./images/logo_icon.png')
    sg.set_options(font='Ubuntu 12')

    main_layout = [
        [
            sg.Push(),
            sg.Text('Enter Port Number. Must be between 41000 and 42000. Default = 41000.'),
            sg.Push()
        ],
        [
            sg.Push(),
            sg.InputText(key='-enter_port-', size=(6, 1), background_color='#ffffff'),
            sg.Push()
        ],
        [
            sg.Push(),
            sg.Button('Select Port', key='-select_port-'),
            sg.Button('Default Port', key='-default_port-'),
            sg.Push()
        ]
    ]

    return sg.Window('SELECT PORT', main_layout, resizable=False, finalize=True)


# --- DOWNLOAD WINDOW --- #
def create_download_window(theme=DEFAULT_THEME):
    sg.theme(theme)
    sg.set_global_icon('./images/logo_icon.png')
    sg.set_options(font='Ubuntu 12', )

    main_layout = [
        [
            sg.Push(),
            sg.Text('DOWNLOADING BLOCKS', justification='center'),
            sg.Push()
        ],
        [
            sg.Push(),
            sg.Text('Block', justification='right'),
            sg.InputText(key='-current_height-', disabled=True, use_readonly_for_disable=True, size=(6, 1),
                         border_width=0, justification='left'),
            sg.Text(' of Block', justification='right'),
            sg.InputText(key='-network_height-', disabled=True, use_readonly_for_disable=True, size=(6, 1),
                         border_width=0, justification='left'),
            sg.Push()
        ],
        [
            sg.Push(),
            sg.ProgressBar(100, orientation='h', size=(40, 2), key='-pct_complete-', bar_color=("#ac92ec", "#000000"),
                           border_width=5),
            sg.Push()
        ]
    ]

    return sg.Window('LOADING', main_layout, resizable=False, finalize=True, )


# --- MAIN GUI WINDOW --- #
def create_window(theme=DEFAULT_THEME):
    sg.theme(theme)
    sg.set_global_icon('./images/logo_icon.png')
    sg.set_options(font='Ubuntu 12')

    # -- Right Click Menu --- #
    right_click_menu = [
        ['Right', ['Clear', 'Copy', 'Paste']]
    ]

    # --- Main Menu --- #
    menu_layout = [
        ['&File',
         ['&Open Blockchain', 'Open &Wallet', '---', '&Save Blockchain', 'Save Wallet', '---', 'E&xit']],
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
        ['&Help', ['Abo&ut BB POW']]
    ]

    # --- Status Tab --- #

    status_tab_layout = [
        [
            sg.Push(),
            sg.Text("Welcome to the BB POW!", justification='center', auto_size_text=False, size=(48, 1),
                    font="Ubuntu 18"),
            sg.Push()
        ],

        [sg.Push(), sg.Image('./images/logo_icon.png', enable_events=True, key='-logo-'), sg.Push()],
        [sg.HorizontalSeparator(pad=10, color='#000000')],
        [sg.Push(),
         sg.Text('CURRENT HEIGHT:', justification='right', auto_size_text=False, size=(18, 1)),
         sg.InputText(key='-height-', disabled=True, use_readonly_for_disable=True, border_width=0, size=(12, 1)),
         sg.Text('BLOCK ID:', justification='right', auto_size_text=False, size=(12, 1)),
         sg.InputText(key='-prev_id-', disabled=True, use_readonly_for_disable=True, border_width=0, size=(64, 1)),
         sg.Push(), ],
        [sg.HorizontalSeparator(pad=10, color='#000000')],
        [
            sg.Multiline(key='-logs-', pad=10, expand_x=True, expand_y=True, disabled=True, background_color='#FFFFFF',
                         right_click_menu=right_click_menu[0], autoscroll=True, enable_events=True)
        ],
        [
            sg.Push(),
            sg.Button('Save Logs', size=(10,2), key='-save_logs-'),
            sg.Button('Clear Logs', size=(10,2), key='-clear_logs-'),
            sg.Push()
        ]
    ]

    # --- Node Tab --- #

    node_column = [
        [
            sg.Text('Web Server:', justification='left', auto_size_text=False, size=(10, 1)),
            sg.InputText(key='-webserver-', justification='center', disabled=True, use_readonly_for_disable=True,
                         size=(24, 1), enable_events=True, border_width=0, right_click_menu=right_click_menu[0])
        ],
        [sg.HorizontalSeparator(pad=5, color='#000000')],
        [sg.Text('NODE IP:', justification='right', auto_size_text=False, size=(16, 1)),
         sg.InputText(key='-node_ip-', justification='left', size=(16, 1), disabled=True,
                      use_readonly_for_disable=True, enable_events=True, border_width=0,
                      right_click_menu=right_click_menu[0])],
        [sg.Text('NODE PORT:', justification='right', auto_size_text=False, size=(16, 1)),
         sg.InputText(key='-node_port-', justification='left', size=(16, 1), disabled=True,
                      use_readonly_for_disable=True, enable_events=True, border_width=0,
                      right_click_menu=right_click_menu[0])],
        [sg.HorizontalSeparator(pad=5, color='#000000')],
        [sg.Text('SELECTED IP:', justification='right', auto_size_text=False, size=(16, 1)),
         sg.InputText(justification='left', size=(16, 1), background_color='#FFFFFF', key='-selected_ip-',
                      right_click_menu=right_click_menu[0])],
        [sg.Text('SELECTED PORT:', justification='right', auto_size_text=False, size=(16, 1)),
         sg.InputText(justification='left', size=(16, 1), background_color='#FFFFFF', key='-selected_port-',
                      right_click_menu=right_click_menu[0])],
        [sg.Push(), sg.Button('PING', size=(10, 2), key='-ping-', tooltip='Ping selected node'), sg.Button('CLEAR', size=(10, 2), key='-clear-'),
         sg.Push()],
        [sg.HorizontalSeparator(pad=5, color='#000000')],

    ]
    node_table_headings = ['IP ADDRESS', 'PORT', 'PING (ms)', 'LAST CONTACT']
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
         sg.Button('DISCONNECT', button_color='#FF0000', size=(10, 2), key='-disconnect-', tooltip='Disconnect from network'), sg.Push()],
    ]
    node_tab_layout = [
        [sg.Column(node_column, vertical_alignment='center', pad=50, expand_y=True),
         sg.Column(node_table_column, expand_x=True, expand_y=True)
         ]
    ]

    # --- Mining Tab --- #

    mining_info_labels = [
        [sg.Text('Block Target:', justification='right', auto_size_text=False, size=(18, 1))],
        [sg.Text('Mining Reward:', justification='right', auto_size_text=False, size=(18, 1))],
        [sg.Text('Mine Amount Left:', justification='right', auto_size_text=False, size=(18, 1))]
    ]
    mining_info_values = [
        [sg.InputText(key='-miner_target-', disabled=True, use_readonly_for_disable=True, size=(64, 1),
                      justification='left', border_width=0)],
        [sg.InputText(key='-miner_reward-', disabled=True, use_readonly_for_disable=True, size=(64, 1),
                      justification='left', border_width=0)],
        [sg.InputText(key='-total_mining_amount-', disabled=True, use_readonly_for_disable=True, size=(64, 1),
                      justification='left', border_width=0)]

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
    # Metadata for buttons used for tracking button presses
    # Metadata for target = currently_encoded and currently_hex
    # Metadata for bb2b = currently_bbs, currently_basic
    mining_tab_layout = [
        [
            sg.Push(),
            sg.Column(mining_info_labels),
            sg.Column(mining_info_values),
            sg.Button("Hex Target", size=(10, 3), key='-target_button-', metadata='currently_encoded'),
            sg.Button("BBs to Basic", size=(10, 3), key='-bb2b_button-', metadata='currently_bbs'),
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
         sg.InputText('0', disabled=True, use_readonly_for_disable=True, justification='right', size=(20, 1),
                      key='-wallet_available-', right_click_menu=right_click_menu[0])],
        [sg.Text('Locked:', justification='right', auto_size_text=False, size=(10, 1)),
         sg.InputText('0', disabled=True, use_readonly_for_disable=True, justification='right', size=(20, 1),
                      key='-wallet_locked-', right_click_menu=right_click_menu[0])],
        [sg.Text('Balance:', justification='right', auto_size_text=False, size=(10, 1)),
         sg.InputText('0', disabled=True, use_readonly_for_disable=True, justification='right', size=(20, 1),
                      key='-wallet_balance-', right_click_menu=right_click_menu[0])],

    ]
    send_column = [
        [sg.Text('Send to:', justification='right', auto_size_text=False, size=(12, 1)),
         sg.InputText(size=(40, 1), justification='right', key='-wallet_sendto-',
                      right_click_menu=right_click_menu[0])],
        [sg.Text('Amount:', justification='right', auto_size_text=False, size=(12, 1)),
         sg.InputText(size=(40, 1), justification='right', key='-wallet_amount-',
                      right_click_menu=right_click_menu[0])],
        [sg.Text('Fees:', justification='right', auto_size_text=False, size=(12, 1)),
         sg.InputText(size=(40, 1), justification='right', key='-wallet_fees-', right_click_menu=right_click_menu[0])],
        [sg.Text('Block Height:', justification='right', auto_size_text=False, size=(12, 1)),
         sg.InputText(size=(40, 1), justification='right', key='-wallet_block_height-',
                      right_click_menu=right_click_menu[0])]

    ]
    button_column = [
        [sg.Button('Send Funds', key='-wallet_send_funds-', size=(20, 3), button_color='#00AA00'), ],
        [sg.Button('Cancel', key='-wallet_cancel-', size=(20, 1), button_color='#FF0000'), ]
    ]
    wallet_utxo_table_headers = ['tx_id', 'tx_index', 'amount', 'block_height']
    wallet_utxo_column_widths = [len(header) + 2 for header in wallet_utxo_table_headers]
    wallet_tab_layout = [
        [
            sg.Push(),
            sg.Text('ADDRESS:'),
            sg.InputText(key='-wallet_address-', disabled=True, use_readonly_for_disable=True, size=(44, 1),
                         justification='center', border_width=0, right_click_menu=right_click_menu[0]),
            sg.Push()
        ],
        [
            sg.Push(),
            sg.Column(funds_column), sg.Column(send_column), sg.Column(button_column),
            sg.Push()
        ],
        # [sg.Push(), sg.Button('Send Funds', key='-wallet_send_funds-'), sg.Push()],
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
            sg.Push(),
            sg.Text('SERVER:', justification='right', auto_size_text=False, size=(12, 1), tooltip='Server Status.'),
            sg.Image('./images/red_circle_small.png', key='-server_icon-'),
            sg.Text('NETWORK:', justification='right', auto_size_text=False, size=(12, 1), tooltip='Network Status'),
            sg.Image('./images/red_circle_small.png', key='-network_icon-'),
            sg.Text('MINING:', justification='right', auto_size_text=False, size=(12, 1), tooltip='Mining Status'),
            sg.Image('./images/red_circle_small.png', key='-mining_icon-'),
            sg.Push(),
            sg.Button('START MINER', auto_size_button=False, size=(12, 2), key='-start_miner-', button_color='#00AA00'),
            sg.Button('STOP MINER', auto_size_button=False, size=(12, 2), key='-stop_miner-', button_color='#FF0000',
                      disabled=True),
            sg.Push()
        ],
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


# --- HANDLER FOR LOGGING WINDOW --- #
class Handler(logging.StreamHandler):
    '''
    Following advice here: https://github.com/PySimpleGUI/PySimpleGUI/issues/2968
    '''

    def __init__(self):
        logging.StreamHandler.__init__(self)
        self.formatter = logging.Formatter(Formatter.LOGGING_FORMAT, Formatter.DATE_FORMAT)

    def emit(self, record):
        global buffer
        record = self.formatter.format(record)
        buffer = f'{buffer}\n{record}'.strip()


def run_node_gui():
    # Get port first
    desired_port = 0
    port_found = False
    port_window = create_port_window()

    #Bind enter key in port_window
    port_window.bind("<Return>", "_Enter")
    port_window.bind("<KP_Enter>", "_Enter")

    while not port_found:
        port_event, port_values = port_window.read(timeout=10)

        if port_window.is_closed():
            port_window = create_port_window()
            port_window.bind("<Return>", "_Enter")
            port_window.bind("<KP_Enter>", "_Enter")

        if port_event:

            if port_event in '-select_port-':
                if port_values['-enter_port-'].isnumeric():
                    temp_desired_port = int(port_values['-enter_port-'])
                    if Node.DEFAULT_PORT <= temp_desired_port <= Node.DEFAULT_PORT + Node.PORT_RANGE:
                        desired_port = temp_desired_port
                        port_found = True

            if port_event in '-default_port-':
                desired_port = Node.DEFAULT_PORT
                port_found = True

            if port_event == '_Enter':
                if port_values['-enter_port-'].isnumeric():
                    temp_desired_port = int(port_values['-enter_port-'])
                    if Node.DEFAULT_PORT <= temp_desired_port <= Node.DEFAULT_PORT + Node.PORT_RANGE:
                        desired_port = temp_desired_port
                        port_found = True
                else:
                    desired_port = Node.DEFAULT_PORT
                    port_found = True



    port_window.close()

    # Setup Window
    window = create_window()
    window.set_min_size((1200, 800))

    # # Logger
    gui_logger = logging.getLogger('GUI')
    gui_logger.setLevel('INFO')
    gui_logger.addHandler(Handler())
    gui_logger.propagate = False
    global buffer

    # Start Node
    gui_logger.info('Starting Node. May take a few minutes')
    node = Node(port=desired_port, logger=gui_logger)

    # Formatter/Decoder
    # f = Formatter()
    d = Decoder()

    # Run app with waitress
    app_thread = threading.Thread(target=run_app, daemon=True, args=(node,))
    app_thread.start()

    # Connect to network
    gui_logger.info('Connecting to network.')
    connecting_thread = threading.Thread(target=node.connect_to_network)
    # node.connect_to_network()
    connecting_thread.start()
    download_window = create_download_window()
    download_window['-current_height-'].update(str(node.height))
    download_window['-network_height-'].update(str(node.network_height))

    # Update node wallet
    node.wallet.get_latest_height(node.node)
    node.wallet.update_utxo_df(node.wallet.get_utxos_from_node(node.node))

    # Set fixed variables
    ip = node.ip
    port = node.assigned_port
    url = f'http://{ip}:{port}/'

    window['-node_ip-'].update(ip)
    window['-node_port-'].update(port)
    window['-webserver-'].update(url)
    window['-wallet_address-'].update(node.wallet.address)

    # Verify webserver is running
    if app_thread.is_alive():
        window['-server_icon-'].update('./images/green_circle_small.png')

    # Verify connection to network
    if node.is_connected:
        window['-network_icon-'].update('./images/green_circle_small.png')

    # Bind Keys
    window['-node_list_table-'].bind("<Return>", "_Enter")
    window['-node_list_table-'].bind("<KP_Enter>", "_Enter")
    window['-wallet_amount-'].bind("<Return>", "_Enter")
    window['-wallet_amount-'].bind("<KP_Enter>", "_Enter")
    window['-wallet_sendto-'].bind("<Return>", "_Enter")
    window['-wallet_sendto-'].bind("<KP_Enter>", "_Enter")
    window['-wallet_fees-'].bind("<Return>", "_Enter")
    window['-wallet_fees-'].bind("<KP_Enter>", "_Enter")

    # Bind Mouse Clicks
    window.bind("<Button-1>", "-left_click-")
    window.bind("<Button-3>", "-right_click-")

    # GUI keys which allow paste function
    needs_paste_keys = [
        '-selected_ip',
        '-selected_port',
        '-wallet_sendto-',
        '-wallet_amount-',
        '-wallet_fees-',
        '-wallet_block_height-',

    ]

    # Set variables for loop
    height = -1
    prev_id = 'prev_id'
    mining = node.is_mining
    connected = node.is_connected
    node_list = []
    ping_list = []
    contact_dict = {}
    target = ''
    reward = -1
    total_mine_amount = -1
    validated_tx_list = None
    block_tx_list = None
    orphaned_tx_list = None

    # Wallet
    available_funds = -1
    block_locked = -1
    balance = -1
    utxo_list = []

    # Download
    current_height = -1
    network_height = -1
    percent_complete = -1

    # Logstring for log window
    log_string = ''

    # Download blocks
    while connecting_thread.is_alive():

        dl_event, dl_values = download_window.read(timeout=100)
        if download_window.is_closed():
            download_window = create_download_window()
            network_height = -1

        if current_height != node.height:
            current_height = node.height
            download_window['-current_height-'].update(str(current_height))

        if network_height != node.network_height:
            network_height = node.network_height
            download_window['-network_height-'].update(str(network_height))

        if percent_complete != node.percent_complete:
            percent_complete = node.percent_complete
            download_window['-pct_complete-'].update(percent_complete)

        # Update logs
        if log_string != buffer:
            log_string = buffer
            window['-logs-'].update(buffer)

    download_window.close()

    # GUI LOOP
    while True:
        event, values = window.read(timeout=10)

        # Exit conditions
        if event in [sg.WIN_CLOSED, 'Exit']:
            break

        # Update logs
        if log_string != buffer:
            log_string = buffer
            window['-logs-'].update(buffer)

        #Save logs
        if event == '-save_logs-':
            file_path = sg.popup_get_file('Save Logs', no_window=True, default_extension='.txt', save_as=True, initial_folder=node.dir_path,
                              file_types=(('Text Files', '*.txt'), ('All Files', '*.*')))
            if file_path:
                dir_path, file_name = os.path.split(file_path)
                if file_name.endswith('.txt'):
                    with open(file_path, 'w') as f:
                        f.write(buffer)
                else:
                    gui_logger.warning('Logs must have .txt extension.')


        #Clear Logs
        if event == '-clear_logs-':
            buffer = ''

        # Tab Groups
        if event == '-tab_group-' and values[event] == '-status_tab-':
            window['-height-'].Widget.select_clear()
        if event == '-tab_group-' and values[event] == '-node_tab-':
            window['-webserver-'].Widget.select_clear()
        if event == '-tab_group-' and values[event] == '-miner_tab-':
            window['-miner_target-'].Widget.select_clear()
        if event == '-tab_group-' and values[event] == '-wallet_tab-':
            window['-wallet_address-'].Widget.select_clear()

        # --- SAVE/LOAD --- #
        # Load Blockchain
        if event == 'Open Blockchain':
            file_path = sg.popup_get_file('Load Blockchain', no_window=True,
                                          default_extension='.db',
                                          initial_folder=f'{node.dir_path}',
                                          file_types=(('Database Files', '*.db'), ('All Files', '*.*')))
            if file_path:
                dir_path, file_name = os.path.split(file_path)
                if '.db' in file_name:
                    try:
                        node.blockchain = Blockchain(dir_path, file_name)
                        node.dir_path = dir_path
                        node.db_file = file_name
                    except Exception as e:
                        # Logging
                        gui_logger.error(f'Failed to load Blockchain. Error: {e}')
                else:
                    # Logging
                    gui_logger.warning('Select a database file')

        # Load Wallet
        if event == 'Open Wallet':
            file_path = sg.popup_get_file('Load Wallet', no_window=True,
                                          default_extension='.dat',
                                          initial_folder=node.dir_path,
                                          file_types=(('Wallet Files', '*.dat'), ('All Files', '*.*')))
            if file_path:
                dir_path, file_name = os.path.split(file_path)
                if '.dat' in file_name:
                    try:
                        node.wallet = Wallet(dir_path=dir_path, file_name=file_name, logger=gui_logger)
                        window['-wallet_address-'].update(node.wallet.address)
                        # Update node wallet
                        node.wallet.get_latest_height(node.node)
                        node.wallet.update_utxo_df(node.wallet.get_utxos_from_node(node.node))
                    except Exception as e:
                        # Logging
                        gui_logger.error(f'Unable to load wallet. Error: {e}')
                else:
                    # Logging
                    gui_logger.warning('Select a wallet file')

        # Save Blockchain
        if event == 'Save Blockchain':
            file_path = sg.popup_get_file('Save Blockchain', no_window=True, save_as=True,
                                          default_extension='.db',
                                          initial_folder=node.dir_path,
                                          default_path='chain.db',
                                          file_types=(('Database Files', '*.db'), ('All Files', '*.*')))
            if file_path:
                dir_path, file_name = os.path.split(file_path)
                if file_name.endswith('.db'):
                    try:
                        db = node.blockchain.chain_db

                        # Delete file if it already exists - will overwrite
                        Path(dir_path, file_name).unlink(missing_ok=True)

                        new_chain = Blockchain(dir_path, file_name)
                        for x in range(1, node.height + 1):
                            new_chain.add_block(d.raw_block(
                                db.get_raw_block(x)['raw_block']
                            ))
                        node.blockchain = new_chain
                        node.dir_path = dir_path
                        node.db_file = file_name
                    except Exception as e:
                        # Logging
                        gui_logger.error(f'Failed to load Blockchain. Error: {e}')
                else:
                    # Logging
                    gui_logger.warning('Database file must have .db extension.')

        # Save Wallet
        if event == 'Save Wallet':
            file_path = sg.popup_get_file('Save Wallet', no_window=True, save_as=True,
                                          default_extension='.dat',
                                          initial_folder=node.wallet.dir_path,
                                          default_path='wallet.dat',
                                          file_types=(('Wallet Files', '*.dat'), ('All Files', '*.*')))
            if file_path:
                dir_path, file_name = os.path.split(file_path)
                if file_name.endswith('.dat'):
                    wallet_seed = node.wallet.load_wallet(node.dir_path, node.wallet_file)
                    new_wallet = Wallet(seed=wallet_seed, dir_path=dir_path, file_name=file_name, logger=gui_logger)
                    node.wallet = new_wallet
                    # Update Wallet
                    node.wallet.get_latest_height(node.node)
                    node.wallet.update_utxo_df(node.wallet.get_utxos_from_node(node.node))
                else:
                    # Logging
                    gui_logger.warning('Wallet file must have .dat extension.')

        # --- INFO BAR --- #
        # Mining Icon
        if mining != node.is_mining:
            mining = node.is_mining
            if mining:
                window['-mining_icon-'].update('./images/green_circle_small.png')
                window['-start_miner-'].update(disabled=True)
                window['-stop_miner-'].update(disabled=False)
            else:
                window['-mining_icon-'].update('./images/red_circle_small.png')
                window['-start_miner-'].update(disabled=False)
                window['-stop_miner-'].update(disabled=True)

        # If Server fails
        if not app_thread.is_alive():
            window['-server_icon-'].update('./images/red_circle_small.png')

        # Height
        if height != node.height:
            height = node.height
            window['-height-'].update(str(height))
            # Also update wallet
            node.wallet.get_latest_height(node.node)
            node.wallet.update_utxo_df(node.wallet.get_utxos_from_node(node.node))
            node.wallet.update_utxos_from_pending_transactions()

        # Prev_id
        if prev_id != node.last_block.id:
            prev_id = node.last_block.id
            window['-prev_id-'].update(prev_id)

        # --- NODE TAB --- #
        # Connect
        if event == '-connect-' and not connected:
            # Get ip and port values
            temp_ip = values['-selected_ip-']
            temp_port = values['-selected_port-']

            # Create node for connecting
            if temp_ip and temp_port and temp_port.isnumeric():
                temp_node = (temp_ip, int(temp_port))
            else:
                temp_node = node.LEGACY_NODE

            # Create connecting thread
            download_window = create_download_window()
            connecting_thread = threading.Thread(target=node.connect_to_network, args=(temp_node,))
            connecting_thread.start()

            # Download blocks
            while connecting_thread.is_alive():

                dl_event, dl_values = download_window.read(timeout=100)
                if download_window.is_closed():
                    download_window = create_download_window()
                    network_height = -1

                if current_height != node.height:
                    current_height = node.height
                    download_window['-current_height-'].update(str(current_height))

                if network_height != node.network_height:
                    network_height = node.network_height
                    download_window['-network_height-'].update(str(network_height))

                if percent_complete != node.percent_complete:
                    percent_complete = node.percent_complete
                    download_window['-pct_complete-'].update(percent_complete)

                # Update logs
                if log_string != buffer:
                    log_string = buffer
                    window['-logs-'].update(buffer)

            download_window.close()

        # Disconnect
        if event == '-disconnect-' and connected:
            node.disconnect_from_network()
            window['-node_list_table-'].update(values=[])
            ping_list = []

        # Connected Icon
        if connected != node.is_connected:
            connected = node.is_connected
            if connected:
                window['-network_icon-'].update('./images/green_circle_small.png')
            else:
                window['-network_icon-'].update('./images/red_circle_small.png')

        # Node List Table
        if node_list != node.node_list:
            # Remove Stale Pings
            ping_list_index = ping_list.copy()
            for t in ping_list_index:
                t_ip, t_port, _, _ = t
                if (t_ip, t_port) not in node.node_list:
                    ping_list.remove(t)

            # Ping new nodes if connected
            if connected:
                new_nodes = [n for n in node.node_list if n not in node_list]
                for n in new_nodes:
                    start_time = time.time()
                    pinged = node.ping_node(n)
                    if pinged:
                        ping_time = int((time.time() - start_time) * 1000)
                        contact_dict.update({n: utc_to_seconds()})
                        ping_list.append(n + (str(ping_time), seconds_to_utc(contact_dict[n])))

            node_list = node.node_list.copy()
            window['-node_list_table-'].update(values=ping_list)

        if event == '-node_list_table-' or event == '-node_list_table-' + '_Enter':
            try:
                selected_index = values['-node_list_table-'][0]
                temp_ip, temp_port = node.node_list[selected_index]
                window['-selected_ip-'].update(temp_ip)
                window['-selected_port-'].update(str(temp_port))
            except IndexError:
                pass

        if event == '-ping-':
            ip = values['-selected_ip-']
            port = values['-selected_port-']
            if ip and port and port.isnumeric():
                port = int(port)
                try:
                    pt = [pt for pt in ping_list if pt[0] == ip and pt[1] == port][0]
                    start_time = time.time()
                    pinged = node.ping_node((ip, port))
                    if pinged:
                        ping_time = int((time.time() - start_time) * 1000)
                        contact_dict.update({(ip, port): utc_to_seconds()})
                        ping_list.remove(pt)
                        ping_list.append((ip, port, str(ping_time), seconds_to_utc(contact_dict[(ip, port)])))
                        window['-node_list_table-'].update(ping_list)
                except IndexError:
                    # Logging
                    gui_logger.error(f'No node in list with ip {ip} and port {port}')

        if event == '-clear-':
            window['-selected_ip-'].update('')
            window['-selected_port-'].update('')

        if event == 'Copy':
            window_key = window.FindElementWithFocus().Key
            copy_text = None
            try:
                copy_text = window[window_key].Widget.selection_get()
            except _tkinter.TclError:
                pass
            if copy_text:
                cb = Tk()
                cb.clipboard_clear()
                cb.clipboard_append(copy_text)
                cb.update()
                cb.destroy()

        if event == 'Paste':
            window_key = window.FindElementWithFocus().Key
            if window_key in needs_paste_keys:
                cb = Tk()
                paste_text = cb.clipboard_get()
                cb.update()
                cb.destroy()
                try:
                    window[window_key].update(paste_text)
                except Exception as e:
                    # Logging
                    gui_logger.error(f'Encountered exception when copying: {e}')

        if event == 'Clear':
            window_key = window.FindElementWithFocus().Key
            selected_text = None
            try:
                selected_text = window[window_key].Widget.selection_get()
            except _tkinter.TclError:
                pass
            if selected_text:
                window[window_key].Widget.selection_clear()
                if window_key in [
                    '-selected_ip-', '-selected_port-',
                    '-wallet_sendto-', '-wallet_amount-', '-wallet_fees-'
                ]:
                    temp_text = values[window_key]
                    updated_text = temp_text.replace(selected_text, '')
                    window[window_key].update(updated_text)

        # --- MINER TAB --- #

        # Stop/Start Miner
        if event == '-start_miner-':
            node.start_miner()
        if event == '-stop_miner-':
            node.stop_miner()

        # Miner values
        if event == '-target_button-':
            if window['-target_button-'].metadata == 'currently_encoded':
                window['-target_button-'].update("Encode Target")
                window['-target_button-'].metadata = 'currently_hex'
            else:
                window['-target_button-'].update("Hex Target")
                window['-target_button-'].metadata = 'currently_encoded'
        if event == '-bb2b_button-':
            if window['-bb2b_button-'].metadata == 'currently_bbs':
                window['-bb2b_button-'].update("Basic to BBs")
                window['-bb2b_button-'].metadata = 'currently_basic'
            else:
                window['-bb2b_button-'].update("BBs to Basic")
                window['-bb2b_button-'].metadata = 'currently_bbs'

        if target != node.f.target_from_int(node.target) and window['-target_button-'].metadata == 'currently_encoded':
            target = node.f.target_from_int(node.target)
            window['-miner_target-'].update(target)
        if target != hex(node.target) and window['-target_button-'].metadata == 'currently_hex':
            target = hex(node.target)
            window['-miner_target-'].update(target)
        if reward != node.mining_reward and window['-bb2b_button-'].metadata == 'currently_bbs':
            reward = node.mining_reward
            window['-miner_reward-'].update(str(reward) + " BBs")
        if reward != node.mining_reward // node.f.BASIC_TO_BBS and window[
            '-bb2b_button-'].metadata == 'currently_basic':
            reward = node.mining_reward // node.f.BASIC_TO_BBS
            window['-miner_reward-'].update(str(reward) + " BasiCoins")
        if total_mine_amount != node.total_mining_amount and window['-bb2b_button-'].metadata == 'currently_bbs':
            total_mine_amount = node.total_mining_amount
            window['-total_mining_amount-'].update(str(total_mine_amount) + " BBs")
        if total_mine_amount != node.total_mining_amount // node.f.BASIC_TO_BBS and window[
            '-bb2b_button-'].metadata == 'currently_basic':
            total_mine_amount = node.total_mining_amount // node.f.BASIC_TO_BBS
            window['-total_mining_amount-'].update(str(total_mine_amount) + " BasiCoins")

        # TX tables
        if validated_tx_list != node.validated_transactions:
            validated_tx_list = node.validated_transactions.copy()
            temp_list = []
            temp_fees = 0
            for tx in validated_tx_list:
                temp_fees += node.get_fees(tx)
                temp_list.append(tx.id)
            window['-validated_tx_table-'].update(values=temp_list)
            window['-current_fees-'].update(str(temp_fees))
        if block_tx_list != node.block_transactions:
            block_tx_list = node.block_transactions.copy()
            temp_list = []
            temp_fees = 0
            for tx in block_tx_list:
                temp_fees += node.get_fees(tx)
                temp_list.append(tx.id)
            window['-block_tx_table-'].update(values=temp_list)
            window['-block_fees-'].update(str(temp_fees))
        if orphaned_tx_list != node.orphaned_transactions:
            orphaned_tx_list = node.orphaned_transactions.copy()
            temp_list = []
            for tx in orphaned_tx_list:
                temp_list.append(tx.id)
            window['-orphaned_tx_table-'].update(values=temp_list)

        # --- WALLET TAB --- #
        # Update Wallet Balance
        if available_funds != node.wallet.spendable:
            available_funds = node.wallet.spendable
            window['-wallet_available-'].update(str(available_funds))
        if block_locked != node.wallet.block_locked:
            block_locked = node.wallet.block_locked
            window['-wallet_locked-'].update(str(block_locked))
        if balance != node.wallet.balance:
            balance = node.wallet.balance
            window['-wallet_balance-'].update(str(balance))
        if utxo_list != node.wallet.utxo_list:
            utxo_list = node.wallet.utxo_list
            window['-utxo_table-'].update(values=utxo_list)

        # Send Funds
        if event == '-wallet_sendto-' + '_Enter':
            window['-wallet_amount-'].Widget.focus_force()
        if event == '-wallet_amount-' + '_Enter':
            window['-wallet_fees-'].Widget.focus_force()
        if event in ['-wallet_send_funds-', '-wallet_fees' + '_Enter']:
            # Get Values
            sendto_address = values['-wallet_sendto-']
            string_amount = values['-wallet_amount-']
            string_fees = values['-wallet_fees-']
            string_block_height = values['-wallet_block_height-']

            # Verify numeric values
            if string_amount.isnumeric() and string_fees.isnumeric():
                amount = int(string_amount)
                fees = int(string_fees)
                if string_block_height.isnumeric():
                    block_height = int(string_block_height)
                else:
                    block_height = 0

                if not d.verify_address(sendto_address):
                    # Logging
                    gui_logger.warning(f'Address {sendto_address} is invalid.\n')
                elif amount > node.wallet.spendable:
                    # Logging
                    gui_logger.warning(f'Insufficient balance. Available funds: {node.wallet.spendable}.\n')
                elif fees <= 0:
                    # Logging
                    gui_logger.warning('Cannot have zero fee amount.\n')
                else:
                    new_tx = node.wallet.create_transaction(sendto_address, amount, fees, block_height)
                    # Logging
                    gui_logger.info(f'New transaction created with id {new_tx.id}.')
                    if new_tx:
                        tx_sent = node.send_tx_to_node(new_tx, node.node)  # Triggers gossip protocol
                        # Logging
                        gui_logger.info(f'Transaction with id {new_tx.id} sent to network. Received: {tx_sent}.')
                        node.wallet.update_utxos_from_pending_transactions()
                    else:
                        # Logging
                        gui_logger.error('Error creating transaction.')
                    window['-wallet_sendto-'].update('')
                    window['-wallet_amount-'].update('')
                    window['-wallet_fees-'].update('')
                    window['-wallet_block_height-'].update('')
            else:
                # Logging
                gui_logger.warning('Enter a valid amount and/or fees.')
        if event == '-wallet_cancel-':
            window['-wallet_sendto-'].update('')
            window['-wallet_amount-'].update('')
            window['-wallet_fees-'].update('')
            window['-wallet_block_height-'].update('')

        # About
        if event == 'About BB POW':
            create_about_window()

    # Cleanup
    if node.is_mining:
        node.stop_miner()
    node.disconnect_from_network()
    window.close()


if __name__ == '__main__':
    run_node_gui()
