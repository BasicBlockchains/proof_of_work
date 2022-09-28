'''
Main File for GUI
'''
import _tkinter
import logging
import os
import os.path
import threading
import time
from pathlib import Path
from tkinter import Tk
import json
import multiprocessing
import webbrowser
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
DEFAULT_WINDOW_SIZE = (1200, 500)

IMAGE_DIR = './images'
LOGO_FILE = 'logo_icon.png'
RED_CIRCLE_FILE = 'red_circle_small.png'
GREEN_CIRCLE_FILE = 'green_circle_small.png'
LOGO_PATH = Path(IMAGE_DIR, LOGO_FILE)
RED_CIRCLE_PATH = Path(IMAGE_DIR, RED_CIRCLE_FILE)
GREEN_CIRCLE_PATH = Path(IMAGE_DIR, GREEN_CIRCLE_FILE)

buffer = ''


# --- ABOUT WINDOW --- #
def create_about_window(theme=DEFAULT_THEME):
    sg.theme(theme)
    sg.set_global_icon(LOGO_PATH.absolute().as_posix())
    sg.set_options(font='Ubuntu 12', )

    main_layout = [
        [
            sg.Push(),
            sg.Text("The BB POW is a proof-of-work blockchain, written entirely in python.\n\n"
                    f"Current version: {Formatter.MAJOR_VERSION}.{Formatter.MINOR_VERSION}.{Formatter.PATCH_VERSION}\n"
                    f"Contact: basicblockchains@gmail.com\n\n"
                    f"Currency conversion: 1,000,000,000 BBs = 1 Coin\n"
                    f""),
            sg.Push()
        ]
    ]

    return sg.Window('ABOUT', main_layout, resizable=False, finalize=True)


# --- CONFIG WINDOW --- #
def create_config_window(theme=DEFAULT_THEME):
    sg.theme(theme)
    sg.set_global_icon(LOGO_PATH.absolute().as_posix())
    sg.set_options(font='Ubuntu 12')

    main_layout = [
        [
            sg.Push(),
            sg.Text('Enter Port Number. Must be between 41000 and 42000. Default = 41000.'),
            sg.Push()
        ],
        [
            sg.Push(),
            sg.InputText(key='-enter_port-', size=(6, 1), background_color='#ffffff',
                         tooltip='Blank field will use default value'),
            sg.Push()
        ],
        [sg.HorizontalSeparator(pad=10, color='#000000')],
        [
            sg.Push(),
            sg.Text('Choose minimum app size. Default = 1200 x 500'),
            sg.Push(),
        ],
        [
            sg.Push(),
            sg.InputText(key='-minimum_width-', size=(6, 1), background_color='#ffffff'),
            sg.InputText(key='-minimum_height-', size=(6, 1), background_color='#ffffff'),
            sg.Push()
        ],
        [
            sg.Push(),
            sg.Text('Press Enter to accept defaults or confirm choices. Invalid options will force defaults.'),
            sg.Push()
        ],
        [
            sg.Push(),
            sg.Button('Confirm config', key='-confirm_config-'),
            sg.Button('Accept defaults', key='-accept_defaults-'),
            sg.Button('Cancel', key='-cancel_gui-', button_color='#FF0000'),
            sg.Push()
        ]

    ]

    return sg.Window('APP CONFIG', main_layout, resizable=False, finalize=True)


# --- DOWNLOAD WINDOW --- #
def create_download_window(theme=DEFAULT_THEME):
    sg.theme(theme)
    sg.set_global_icon(LOGO_PATH.absolute().as_posix())
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

    return sg.Window('LOADING', main_layout, resizable=False, finalize=True, no_titlebar=True, grab_anywhere=True)


# --- MAIN GUI WINDOW --- #
def create_window(theme=DEFAULT_THEME, size=DEFAULT_WINDOW_SIZE):
    sg.theme(theme)
    sg.set_global_icon(LOGO_PATH.absolute().as_posix())
    sg.set_options(font='Ubuntu 12')

    # -- Right Click Menu --- #
    right_click_menu = [
        ['Right', ['Copy', 'Paste', '---', 'Clear']]
    ]

    # --- Main Menu --- #
    menu_layout = [
        ['&File',
         ['&Open Blockchain', 'Open &Wallet', '---', '&Save Blockchain', 'Sa&ve Wallet', '---', 'E&xit']],
        ['&Help', ['Abo&ut BB POW']]
    ]

    # --- BLOCKCHAIN TAB --- #

    blockchain_column_1 = [
        [
            sg.Push(),
            sg.Text('Blockchain Stats'),
            sg.Push()
        ],
        [
            sg.Push(),
            sg.Text('Height :', justification='right', size=(12, 1)),
            sg.InputText(key='-height-', disabled=True, use_readonly_for_disable=True, size=(23, 1),
                         justification='left', border_width=0, right_click_menu=right_click_menu[0]),
            sg.Push()
        ],
        [
            sg.Push(),
            sg.Text('Target :', justification='right', size=(12, 1)),
            sg.InputText(key='-target-', disabled=True, use_readonly_for_disable=True, size=(23, 1),
                         justification='left', border_width=0, right_click_menu=right_click_menu[0]),
            sg.Push()
        ],
        [
            sg.Push(),
            sg.Text('Reward :', justification='right', size=(12, 1)),
            sg.InputText(key='-reward-', disabled=True, use_readonly_for_disable=True, size=(23, 1),
                         justification='left', border_width=0, right_click_menu=right_click_menu[0]),
            sg.Push()
        ],
        [
            sg.Push(),
            sg.Text('Mine Amount :', justification='right', size=(12, 1)),
            sg.InputText(key='-mine_amount-', disabled=True, use_readonly_for_disable=True, size=(23, 1),
                         justification='left', border_width=0, right_click_menu=right_click_menu[0]),
            sg.Push()
        ]
    ]
    blockchain_column_2 = [
        [
            sg.Push(),
            sg.Text('LOGS'),
            sg.Push()
        ],
        [
            sg.Multiline(key='-logs-', pad=10, expand_x=True, expand_y=True, disabled=True, background_color='#FFFFFF',
                         right_click_menu=right_click_menu[0], autoscroll=True, enable_events=True)
        ],
        [
            sg.Push(),
            sg.Button('Disable Logging', key='-toggle_logging-'),
            sg.Button('Clear Logs', key='-clear_logs-'),
            sg.Button('Save Logs', key='-save_logs-'),
            sg.Push()
        ]
    ]

    blockchain_tab_layout = [
        [
            sg.Push(),
            sg.Text("Welcome to the BB POW!", justification='center', auto_size_text=False, size=(48, 1),
                    font="Ubuntu 18"),
            sg.Push()
        ],

        [sg.Push(), sg.Image(LOGO_PATH.absolute().as_posix(), enable_events=True, key='-logo-'), sg.Push()],
        [sg.HorizontalSeparator(pad=10, color='#000000')],
        [
            sg.Column(blockchain_column_1, vertical_alignment='top'),
            sg.Column(blockchain_column_2, expand_x=True, expand_y=True)
        ]

    ]

    # --- WALLET TAB --- #
    wallet_column_1 = [
        [
            sg.Push(),
            sg.Text('Wallet Info'),
            sg.Push()
        ],
        [sg.Text('Available :', justification='right', auto_size_text=False, size=(12, 1)),
         sg.InputText('0', key='-available-', size=(40, 1), disabled=True, use_readonly_for_disable=True,
                      border_width=0, right_click_menu=right_click_menu[0])],
        [sg.Text('Locked :', justification='right', auto_size_text=False, size=(12, 1)),
         sg.InputText('0', key='-locked-', size=(40, 1), disabled=True, use_readonly_for_disable=True,
                      border_width=0, right_click_menu=right_click_menu[0])],
        [sg.Text('Balance :', justification='right', auto_size_text=False, size=(12, 1)),
         sg.InputText('0', key='-balance-', size=(40, 1), disabled=True, use_readonly_for_disable=True,
                      border_width=0, right_click_menu=right_click_menu[0])],

    ]
    wallet_column_2 = [
        [
            sg.Push(),
            sg.Text('Send Funds'),
            sg.Push()
        ],
        [sg.Text('Send to:', justification='right', auto_size_text=False, size=(12, 1)),
         sg.InputText(size=(40, 1), justification='right', key='-wallet_sendto-',
                      right_click_menu=right_click_menu[0])],
        [sg.Text('Amount:', justification='right', auto_size_text=False, size=(12, 1)),
         sg.InputText(size=(40, 1), justification='right', key='-wallet_amount-',
                      right_click_menu=right_click_menu[0])],
        [sg.Text('Fees:', justification='right', auto_size_text=False, size=(12, 1)),
         sg.InputText('0', size=(40, 1), justification='right', key='-wallet_fees-',
                      right_click_menu=right_click_menu[0])],
        [sg.Text('Block Height:', justification='right', auto_size_text=False, size=(12, 1)),
         sg.InputText('0', size=(40, 1), justification='right', key='-wallet_block_height-',
                      right_click_menu=right_click_menu[0])]
    ]

    wallet_tab_layout = [
        [
            sg.Push(),
            sg.Text('ADDRESS :', font='Ubuntu 18', justification='right'),
            sg.InputText(key='-address-', disabled=True, use_readonly_for_disable=True, size=(40, 2), font='Ubuntu 18',
                         border_width=0, justification='left', right_click_menu=right_click_menu[0]),
            sg.Push()
        ],
        [sg.HorizontalSeparator(color='#000000')],
        [
            sg.Push(),
            sg.Column(wallet_column_1, vertical_alignment='top'),
            sg.Column(wallet_column_2, vertical_alignment='top'),
            sg.Push()
        ],
        [
            sg.Push(),
            sg.Button('Send Funds', key='-wallet_send_funds-', size=(20, 3), button_color='#00AA00', pad=20),
            sg.Button('Cancel', key='-wallet_cancel-', size=(20, 3), button_color='#FF0000', pad=20),
            sg.Push()
        ]
    ]

    # --- NETWORK TAB --- #

    network_column_1 = [
        [sg.Text('NODE IP:', justification='right', auto_size_text=False, size=(16, 1)),
         sg.InputText(key='-node_ip-', justification='left', size=(16, 1), disabled=True,
                      use_readonly_for_disable=True, enable_events=True, border_width=0,
                      right_click_menu=right_click_menu[0])],
        [sg.Text('NODE PORT:', justification='right', auto_size_text=False, size=(16, 1)),
         sg.InputText(key='-node_port-', justification='left', size=(16, 1), disabled=True,
                      use_readonly_for_disable=True, enable_events=True, border_width=0,
                      right_click_menu=right_click_menu[0])],
        [sg.HorizontalSeparator(pad=10, color='#000000')],
        [
            sg.Push(),
            sg.Text('MANUAL CONNECTION'),
            sg.Push()
        ],
        [sg.Text('SELECTED IP:', justification='right', auto_size_text=False, size=(16, 1)),
         sg.InputText(justification='left', size=(16, 1), background_color='#FFFFFF', key='-selected_ip-',
                      right_click_menu=right_click_menu[0])],
        [sg.Text('SELECTED PORT:', justification='right', auto_size_text=False, size=(16, 1)),
         sg.InputText(justification='left', size=(16, 1), background_color='#FFFFFF', key='-selected_port-',
                      right_click_menu=right_click_menu[0])],
        [sg.HorizontalSeparator(pad=10, color='#000000')],
        [
            sg.Push(),
            sg.Button('CONNECT TO NETWORK', size=(16, 2), button_color='#00AA00', tooltip='Connect to selected node.',
                      key='-connect-'),
            sg.Button('DISCONNECT FROM NETWORK', size=(16, 2), button_color='#FF0000', key='-disconnect-'),
            sg.Push()
        ],

    ]

    node_table_headings = ['IP ADDRESS', 'PORT', 'LAST CONTACT', 'LATENCY']
    network_column_2 = [
        [
            sg.Push(),
            sg.Text('NODE LIST'),
            sg.Push()
        ],
        [
            sg.Table(values=[], key='-node_list_table-', expand_y=True, expand_x=True, headings=node_table_headings,
                     enable_events=True, enable_click_events=True, bind_return_key=True)
        ],
        [
            sg.Push(),
            sg.Button('PING NODE', size=(16, 2), button_color='#564976', key='-ping_node-'),
            sg.Button('VALIDATE NODE', size=(16, 2), button_color='#564976', key='-validate_node-'),
            sg.Push()
        ]
    ]

    network_tab_layout = [
        [sg.Column(network_column_1, vertical_alignment='center', pad=50, expand_y=True),
         sg.Column(network_column_2, expand_x=True, expand_y=True)
         ]
    ]

    # --- TAB GROUP --- #
    tab_group = [
        [
            sg.TabGroup(
                [[sg.Tab('Blockchain', blockchain_tab_layout, key='-blockchain_tab-'),
                  sg.Tab('Wallet', wallet_tab_layout, key='-wallet_tab-'),
                  sg.Tab('Network', network_tab_layout, key='-node_tab-')
                  ]],
                tab_location='topleft', border_width=5, expand_x=True, expand_y=True, key='-tab_group-',
                enable_events=True
            ),
        ]
    ]

    # --- MAIN LAYOUT --- #

    main_layout = [
        [sg.Menu(menu_layout)],
        [
            sg.Push(),
            sg.Text('SERVER:', justification='right', auto_size_text=False, size=(12, 1), tooltip='Server Status.'),
            sg.Image(RED_CIRCLE_PATH.absolute().as_posix(), key='-server_icon-'),
            sg.Text('NETWORK:', justification='right', auto_size_text=False, size=(12, 1), tooltip='Network Status'),
            sg.Image(RED_CIRCLE_PATH.absolute().as_posix(), key='-network_icon-'),
            sg.Text('MINING:', justification='right', auto_size_text=False, size=(12, 1), tooltip='Mining Status'),
            sg.Image(RED_CIRCLE_PATH.absolute().as_posix(), key='-mining_icon-'),
            sg.Push(),
            sg.Button('START MINER', auto_size_button=False, size=(12, 2), key='-start_miner-', button_color='#00AA00'),
            sg.Button('STOP MINER', auto_size_button=False, size=(12, 2), key='-stop_miner-', button_color='#FF0000'),
            sg.Button('OPEN WEBSERVER', auto_size_button=False, size=(12, 2), key='-open_browser-',
                      button_color='#564976'),
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

    return sg.Window('BB POW', size=size, layout=main_layout, resizable=True, finalize=True)


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
    '''
    The GUI will run in stages.

    Stage 1: Open Config Window
    Stage 2: Create Main Window
    Stage 3: Initialize Node and API
    Stage 4: Update initial variables
    Stage 5: Connect to Network
    Stage 6: Run GUI
    '''

    # Decoder/Formatter
    d = Decoder()
    f = Formatter()

    # Timeout Constants
    PING_TIMEOUT = 300

    # --- STAGE 0: Configure Logger for GUI use --- #
    gui_logger = logging.getLogger('GUI')
    gui_logger.setLevel('INFO')
    gui_logger.addHandler(Handler())
    gui_logger.propagate = False
    global buffer

    # Log variables for GUI
    log_string = ''
    logs_enabled = True

    # --- STAGE 1: Open Config Window --- #
    # Config window variables
    desired_port = Node.DEFAULT_PORT
    desired_width = 1200
    desired_height = 500
    port_confirmed = False
    size_confirmed = False
    gui_confirmed = True
    config_window = create_config_window()

    # Bind enter key in port_window
    config_window.bind("<Return>", "_Enter")
    config_window.bind("<KP_Enter>", "_Enter")

    while not port_confirmed and not size_confirmed and gui_confirmed:
        config_event, config_values = config_window.read(timeout=10)

        if config_event in ['-cancel_gui-', sg.WIN_CLOSED]: gui_confirmed = False
        if config_event == '-confirm_config-':
            if config_values['-enter_port-'].isnumeric():
                temp_desired_port = int(config_values['-enter_port-'])
                if Node.DEFAULT_PORT <= temp_desired_port <= Node.DEFAULT_PORT + Node.PORT_RANGE:
                    desired_port = temp_desired_port
                    port_confirmed = True

            if config_values['-minimum_width-'].isnumeric() and config_values['-minimum_height-'].isnumeric():
                temp_width = int(config_values['-minimum_width-'])
                temp_height = int(config_values['-minimum_height-'])
                if 200 <= temp_width <= 1200:
                    desired_width = temp_width
                if 200 <= temp_height <= 800:
                    desired_height = temp_height
                size_confirmed = True
        if config_event == '-accept_defaults-':
            port_confirmed = True
            size_confirmed = True
        if config_event == '_Enter':
            if config_values['-enter_port-'].isnumeric():
                temp_desired_port = int(config_values['-enter_port-'])
                if Node.DEFAULT_PORT <= temp_desired_port <= Node.DEFAULT_PORT + Node.PORT_RANGE:
                    desired_port = temp_desired_port
                    port_confirmed = True
            else:
                desired_port = Node.DEFAULT_PORT
                port_confirmed = True

            if config_values['-minimum_width-'].isnumeric() and config_values['-minimum_height-'].isnumeric():
                temp_width = int(config_values['-minimum_width-'])
                temp_height = int(config_values['-minimum_height-'])
                if 200 <= temp_width <= 1200:
                    desired_width = temp_width
                if 200 <= temp_height <= 800:
                    desired_height = temp_height
            size_confirmed = True

    config_window.close()

    # --- PROCEED IF GUI CONFIRMED --- #
    if gui_confirmed:

        # --- STAGE 2:  Create Main Window--- #
        window = create_window()
        window.set_min_size((desired_width, desired_height))

        # --- STAGE 3:  Initialize Node and API--- #
        node = Node(port=desired_port, logger=gui_logger)
        app_thread = threading.Thread(target=run_app, daemon=True, args=(node,))
        app_thread.start()

        # --- STAGE 4: Update initial variables and logs --- #
        # Verify webserver is running
        if app_thread.is_alive(): window['-server_icon-'].update(GREEN_CIRCLE_PATH.absolute().as_posix())

        # Create initial values
        # Blockchain
        window['-height-'].update(str(node.height))
        window['-target-'].update(f.target_from_int(node.blockchain.target))
        window['-reward-'].update(str(node.blockchain.mining_reward))
        window['-mine_amount-'].update(str(node.blockchain.total_mining_amount))

        # Wallet
        window['-address-'].update(node.wallet.address)

        # Node
        window['-node_ip-'].update(node.ip)
        window['-node_port-'].update(str(node.assigned_port))

        # --- STAGE 5: Connect to Network --- #
        # Download variables
        current_height = -1
        network_height = -1
        percent_complete = -1

        # Icon variables
        mining = node.is_mining
        connected = False

        # Create connecting thread
        connecting_thread = threading.Thread(target=node.connect_to_network)
        connecting_thread.start()

        # Open Download Window
        download_window = create_download_window()
        download_window['-current_height-'].update(str(node.height))
        download_window['-network_height-'].update(str(node.network_height))

        # Download blocks
        while connecting_thread.is_alive():
            # Network Icon
            if connected != node.is_connected:
                connected = node.is_connected
                if connected:
                    window['-network_icon-'].update(GREEN_CIRCLE_PATH.absolute().as_posix())
                else:
                    window['-network_icon-'].update(RED_CIRCLE_PATH.absolute().as_posix())

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

        # --- STAGE 6: Run GUI --- #

        # Bind Keys
        window.bind("<Button-1>", "-left_click-")
        window.bind("<Double-Button-1>", "-double_click-")
        window.bind("<Button-3>", "-right_click-")
        window['-wallet_amount-'].bind("<Return>", "_Enter")
        window['-wallet_amount-'].bind("<KP_Enter>", "_Enter")
        window['-wallet_sendto-'].bind("<Return>", "_Enter")
        window['-wallet_sendto-'].bind("<KP_Enter>", "_Enter")
        window['-wallet_fees-'].bind("<Return>", "_Enter")
        window['-wallet_fees-'].bind("<KP_Enter>", "_Enter")
        window['-wallet_block_height-'].bind("<Return>", "_Enter")
        window['-wallet_block_height-'].bind("<KP_Enter>", "_Enter")

        # Blockchain tab variables
        height = -1
        target = ''
        reward = -1
        total_mine_amount = -1

        # Wallet tab variables
        available_funds = -1
        block_locked = -1
        balance = -1

        # Network tab variables
        node_list = []
        ping_list = []
        contact_dict = {}

        # Tables that allow pasting for right click menu
        allow_paste_keys = [
            '-selected_ip',
            '-selected_port',
            '-wallet_sendto-',
            '-wallet_amount-',
            '-wallet_fees-',
            '-wallet_block_height-',
        ]

        while True:
            event, values = window.read(timeout=10)

            # --- EXIT CONDITIONS --- #
            if event in [sg.WIN_CLOSED, 'Exit']:
                break

            # --- DELECT ELEMENTS WHEN OPENING NEW TAB --- #
            if event == '-tab_group-' and values[event] == '-blockchain_tab-': window['-height-'].Widget.select_clear()
            if event == '-tab_group-' and values[event] == '-wallet_tab-': window['-address-'].Widget.select_clear()
            if event == '-tab_group-' and values[event] == '-node_tab-': window['-node_ip-'].Widget.select_clear()

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
                            node.blockchain = Blockchain(dir_path, file_name, logger=gui_logger)
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
                            window['-address-'].update(node.wallet.address)
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

                            new_chain = Blockchain(dir_path, file_name, logger=gui_logger)
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

            # --- ICONS --- #
            # Server Icon
            if not app_thread.is_alive():
                window['-server_icon-'].update(RED_CIRCLE_PATH.absolute().as_posix())
                gui_logger.critical('Webserver thread failed. Stopping GUI')
                window['-logs-'].update(buffer)
                break
            # Network Icon
            if connected != node.is_connected:
                connected = node.is_connected
                if connected:
                    window['-network_icon-'].update(GREEN_CIRCLE_PATH.absolute().as_posix())
                else:
                    window['-network_icon-'].update(RED_CIRCLE_PATH.absolute().as_posix())
            # Mining Icon
            if mining != node.is_mining:
                mining = node.is_mining
                if mining:
                    window['-mining_icon-'].update(GREEN_CIRCLE_PATH.absolute().as_posix())
                else:
                    window['-mining_icon-'].update(RED_CIRCLE_PATH.absolute().as_posix())

            # --- LOGS --- #
            # Update Logs
            if log_string != buffer and logs_enabled:
                log_string = buffer
                window['-logs-'].update(buffer)
            # Disable Logging
            if event == '-toggle_logging-':
                if logs_enabled:
                    window['-toggle_logging-'].update(text='Enable Logging')
                    gui_logger.disabled = True
                else:
                    window['-toggle_logging-'].update(text='Disable Logging')
                    gui_logger.disabled = False
                logs_enabled = not logs_enabled
            # Clear logs
            if event == '-clear_logs-':
                buffer = ''
                window['-logs-'].update(buffer)
            # Save Logs
            if event == '-save_logs-':
                file_path = sg.popup_get_file('Save Logs', no_window=True, default_extension='.txt', save_as=True,
                                              initial_folder=node.dir_path,
                                              file_types=(('Text Files', '*.txt'), ('All Files', '*.*')))
                if file_path:
                    dir_path, file_name = os.path.split(file_path)
                    if file_name.endswith('.txt'):
                        with open(file_path, 'w') as f:
                            f.write(buffer)
                    else:
                        gui_logger.warning('Logs must have .txt extension.')

            # --- MINING --- #
            if event == '-start_miner-':
                node.start_miner()
                gui_logger.info('Miner running.')
            if event == '-stop_miner-':
                node.stop_miner()
                gui_logger.info('Miner stopped.')

            # --- WEBSERVER BUTTON --- #
            if event == '-open_browser-': webbrowser.open(f"http://{node.ip}:{node.assigned_port}", new=2)

            # --- UPDATE BLOCKCHAIN FIELDS --- #
            if height != node.height:
                height = node.height
                window['-height-'].update(str(height))
                # Also update wallet
                node.wallet.get_latest_height(node.node)
                node.wallet.update_utxo_df(node.wallet.get_utxos_from_node(node.node))
                node.wallet.update_utxos_from_pending_transactions()
            if target != f.target_from_int(node.target):
                target = f.target_from_int(node.target)
                window['-target-'].update(target)
            if reward != node.mining_reward:
                reward = node.mining_reward
                window['-reward-'].update(str(reward) + ' BBs')
            if total_mine_amount != node.total_mining_amount:
                total_mine_amount = node.total_mining_amount
                window['-mine_amount-'].update(str(total_mine_amount) + ' BBs')

            # --- UPDATE WALLET FIELDS --- #
            if available_funds != node.wallet.spendable:
                available_funds = node.wallet.spendable
                window['-available-'].update(str(available_funds) + ' BBs')
            if block_locked != node.wallet.block_locked:
                block_locked = node.wallet.block_locked
                window['-locked-'].update(str(block_locked) + ' BBs')
            if balance != node.wallet.balance:
                balance = node.wallet.balance
                window['-balance-'].update(str(balance) + ' BBs')

            # --- SEND FUNDS --- #
            # Send Funds
            if event == '-wallet_sendto-' + '_Enter': window['-wallet_amount-'].Widget.focus_force()
            if event == '-wallet_amount-' + '_Enter': window['-wallet_fees-'].Widget.focus_force()
            if event == '-wallet_fees-' + '_Enter': window['-wallet_block_height-'].Widget.focus_force()
            if event in ['-wallet_send_funds-', '-wallet_block_height' + '_Enter']:
                # Get Values
                sendto_address = values['-wallet_sendto-']
                string_amount = values['-wallet_amount-']
                string_fees = values['-wallet_fees-']
                string_block_height = values['-wallet_block_height-']

                # Verify numeric values
                if string_amount.isnumeric():
                    amount = int(string_amount)
                    if string_fees.isnumeric():
                        fees = int(string_fees)
                    else:
                        fees = 0
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
                    else:
                        new_tx = node.wallet.create_transaction(sendto_address, amount, fees, block_height)
                        # Logging
                        gui_logger.info(f'New transaction created with id {new_tx.id}.')
                        if new_tx:
                            tx_sent = node.send_raw_tx_to_node(new_tx.raw_tx, node.node)  # Triggers gossip protocol
                            # Logging
                            gui_logger.info(f'Transaction with id {new_tx.id} sent to network. Received: {tx_sent}.')
                            node.wallet.update_utxos_from_pending_transactions()
                        else:
                            # Logging
                            gui_logger.error('Error creating transaction.')
                        window['-wallet_sendto-'].update('')
                        window['-wallet_amount-'].update('')
                        window['-wallet_fees-'].update('0')
                        window['-wallet_block_height-'].update('0')
                else:
                    # Logging
                    gui_logger.warning('Enter a valid amount.')

            # Cancel Transaction
            if event == '-wallet_cancel-':
                window['-wallet_sendto-'].update('')
                window['-wallet_amount-'].update('')
                window['-wallet_fees-'].update('0')
                window['-wallet_block_height-'].update('0')

            # --- UPDATE NODE LIST --- #
            if node_list != node.node_list:
                # Get current nodes in node_list
                current_nodes = node_list.copy()

                # Update node list
                node_list = node.node_list.copy()

                # Remove Stale Pings
                ping_list_index = ping_list.copy()
                for t in ping_list_index:
                    t_ip, t_port, _, _ = t
                    if (t_ip, t_port) not in node_list:
                        ping_list.remove(t)

                # Ping new nodes if connected
                new_nodes = [n for n in node_list if n not in current_nodes]
                if connected:
                    for n in new_nodes:
                        start_time = time.time()
                        ping = node.ping_node(n)
                        if ping:
                            ping_time = int((time.time() - start_time) * 1000)
                            contact_dict.update({n: utc_to_seconds()})
                            ping_list.append(n + (seconds_to_utc(contact_dict[n]), ping_time))
                window['-node_list_table-'].update(values=ping_list)

            # --- SELECT NODE IN TABLE --- #
            if event == '-double_click-':
                # Get window
                element = window.FindElementWithFocus()
                if element:
                    window_key = element.Key
                    if window_key == '-node_list_table-':
                        try:
                            node_index = values['-node_list_table-'][0]
                            t_ip, t_port, _, _ = ping_list[node_index]
                            window['-selected_ip-'].update(t_ip)
                            window['-selected_port-'].update(t_port)
                        except IndexError:
                            # Logging
                            gui_logger.debug('Node list table event with no node selected in table.')

            # --- PING/VALIDATE NODE --- #
            if event in ['-ping_node-', '-validate_node-']:
                # Get node from table or manual entry
                try:
                    node_index = values['-node_list_table-'][0]
                    ip, port, _, _ = ping_list[node_index]
                except IndexError:
                    # Logging
                    gui_logger.warning('Ping node event with no node selected in table. Trying manual values.')
                    ip = values['-selected_ip-']
                    port = values['-selected_port-']
                    if port.isnumeric():
                        port = int(port)

                if event == '-ping_node-':
                    try:
                        pt = [pt for pt in ping_list if pt[0] == ip and pt[1] == port][0]
                        start_time = time.time()
                        pinged = node.ping_node((ip, port))
                        if pinged:
                            ping_time = int((time.time() - start_time) * 1000)
                            contact_dict.update({(ip, port): utc_to_seconds()})
                            ping_list.remove(pt)
                            ping_list.append(
                                (ip, port, seconds_to_utc(contact_dict[(ip, port)]), str(ping_time))
                            )
                            window['-node_list_table-'].update(ping_list)
                            # Logging
                            gui_logger.info(f'Ping to {(ip, port)} successful.')
                    except IndexError:
                        # Logging
                        gui_logger.error(f'No node in list with ip {ip} and port {port}')
                else:
                    validated = node.check_genesis((ip, port))
                    if validated:
                        # Logging
                        gui_logger.info(f'Successfully validated node {(ip, port)}.')
                    else:
                        # Logging
                        gui_logger.error(f'Unable to validate {(ip, port)}. Removing from node list.')
                        try:
                            node.node_list.remove((ip, port))
                        except ValueError:
                            # Logging
                            gui_logger.error(f'Unable to find {(ip, port)} in node list.')

            # --- CONNECT / DISCONNECT --- #
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
            if event == '-disconnect-':
                node.disconnect_from_network()
                window['-node_list_table-'].update(values=[])
                ping_list = []

            # --- AUTOMATICALLY PRUNE OLD NODES --- #
            now = utc_to_seconds()
            for node_tuple in node_list:
                if node_tuple in contact_dict.keys():
                    last_contact = contact_dict[node_tuple]
                else:
                    last_contact = now
                if now - last_contact > PING_TIMEOUT:
                    start_time = time.time()
                    ping = node.ping_node(node_tuple)
                    if ping:
                        # Update ping list
                        ping_time = int((time.time() - start_time) * 1000)
                        contact_dict.update({node_tuple: utc_to_seconds()})
                        ping_tuple = [(v1, v2, v3, v4) for (v1, v2, v3, v4) in ping_list if (v1, v2) == node_tuple][0]
                        ping_list.remove(ping_tuple)
                        ping_list.append(node_tuple + (seconds_to_utc(contact_dict[node_tuple]), ping_time))
                        window['-node_list_table-'].update(values=ping_list)
                    else:
                        # Logging - Remove stale node from node list
                        gui_logger.warning(
                            f'Did not ping {node_tuple} successfully after {PING_TIMEOUT} seconds. Removing from node list.')
                        try:
                            node.node_list.remove(node_tuple)
                        except ValueError:
                            # Logging
                            gui_logger.error(f'{node_tuple} not found in node list')

            # --- RIGHT CLICK MENU --- #
            if event == 'Copy':
                element = window.FindElementWithFocus()
                if element:
                    window_key = element.Key
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
                element = window.FindElementWithFocus()
                if element:
                    window_key = element.Key
                    if window_key in allow_paste_keys:
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
                element = window.FindElementWithFocus()
                if element:
                    window_key = element.Key
                    selected_text = None
                    try:
                        selected_text = window[window_key].Widget.selection_get()
                    except _tkinter.TclError:
                        pass
                    if selected_text:
                        window[window_key].Widget.selection_clear()
                        if window_key in allow_paste_keys:
                            temp_text = values[window_key]
                            updated_text = temp_text.replace(selected_text, '')
                            window[window_key].update(updated_text)

            # --- ABOUT WINDOW --- #
            if event == 'About BB POW': create_about_window()

            # --- AUTOMATICALLY SAVE/CLEAR LOGS --- #
            if height % (Formatter.HEARTBEAT * 24) == 0 and height > 0:
                # Save logs
                log_file = f'logs_block{height - Formatter.HEARTBEAT * 24}--{height}.txt'

                if not Path(node.dir_path, log_file).exists():
                    with open(Path(node.dir_path, log_file).absolute().as_posix(), 'w') as file:
                        file.write(buffer)

                    # Clear logs
                    buffer = ''

                    # Log message
                    gui_logger.info(f'Automatically saved logs to {log_file} at height {height}.')

        # Cleanup
        if node.is_mining:
            node.stop_miner()
        node.disconnect_from_network()
        window.close()


if __name__ == '__main__':
    # Spawn method works on Windows, Linux and MacOS
    multiprocessing.set_start_method('spawn')
    run_node_gui()
