'''
Main File for GUI
'''
import threading

import PySimpleGUI as sg

from api import run_app
from node import Node

# --- CONSTANTS --- #
DEFAULT_THEME = 'SystemDefault'
DEFAULT_WINDOW_SIZE = (1200, 800)


# --- MAIN GUI WINDOW --- #
def create_window(theme=DEFAULT_THEME):
    sg.theme(theme)
    sg.set_global_icon('./images/logo_icon.png')
    sg.set_options(font='Ubuntu 12')

    # --- Main Menu --- #
    menu_layout = [
        ['&File',
         ['&Open Blockchain', 'Open &Wallet', '---', '&Save Blockchain', 'Save Blockchain &As', '---', 'E&xit']],
        ['&Logs', ['&Display Logs', 'Save &Logs']],
        ['&Help', ['Abo&ut BB POW']]
    ]

    # --- Node Tab --- #

    node_column = [
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
        [sg.Push(), sg.Button('PING', size=(10, 2), key='-ping-'), sg.Button('STATUS', size=(10, 2), key='-status-'),
         sg.Push()],
        [sg.HorizontalSeparator(pad=5, color='#000000')],
        [sg.Push(), sg.Image('./images/logo_icon.png'), sg.Push()],  ###Relative Path!!!
        [sg.HorizontalSeparator(pad=5, color='#000000')],
        [sg.Push(), sg.Text('Consensus Height'),
         sg.InputText(key='-consensus_height-', disabled=True, use_readonly_for_disable=True, size=(20, 1),
                      justification='center')],
        [sg.Push(), sg.Text('Consensus ID'),
         sg.InputText(key='-consensus_id-', disabled=True, use_readonly_for_disable=True, size=(20, 1),
                      justification='center')],
        [sg.Push(), sg.Text('Consensus Timestamp'),
         sg.InputText(key='-consensus_timestamp-', disabled=True, use_readonly_for_disable=True, size=(20, 1),
                      justification='center')]

    ]

    node_table_headings = ['IP ADDRESS', 'PORT', 'PING (ms)']
    node_table_column_widths = [len(node_heading) + 2 for node_heading in node_table_headings]

    node_table_column = [
        [sg.Table(values=[], headings=node_table_headings, expand_y=True, expand_x=True, auto_size_columns=False,
                  col_widths=node_table_column_widths, key='-node_list_table-', bind_return_key=True)],
        [sg.Push(),
         sg.Button('CONNECT', button_color='#00AA00', size=(10, 2), tooltip='Connect to network', key='-connect-'),
         sg.Button('DISCONNECT', button_color='#FF0000', size=(10, 2), key='-disconnect-'), sg.Push()],
    ]

    node_tab_layout = [
        [sg.Column(node_column, vertical_alignment='top', pad=10, expand_y=True),
         sg.Column(node_table_column, expand_x=True, expand_y=True)
         ]
    ]

    # --- Mining Tab --- #

    mining_tab_layout = [
        [
            sg.Push(),
            sg.Button('START MINER', auto_size_button=False, size=(12, 2), key='-start_miner-', button_color='#00AA00'),
            sg.Button('STOP MINER', auto_size_button=False, size=(12, 2), key='-stop_miner-', button_color='#FF0000'),
            sg.Push()
        ]
    ]

    # --- Tab Group --- #
    tab_group = [
        [
            sg.TabGroup(
                [[sg.Tab('Node', node_tab_layout, key='-node_tab-'),
                  sg.Tab('Miner', mining_tab_layout, key='-miner_tab-')
                  ]],
                tab_location='topleft', border_width=5, expand_x=True, expand_y=True, key='-tab_group-',
                enable_events=True
            ),
        ]
    ]

    # --- Main Layout --- #

    layout = [
        [sg.Menu(menu_layout)],
        [tab_group]
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
    window['-node_ip-'].update(node.ip)
    window['-node_port-'].update(node.assigned_port)

    # GUI LOOP
    while True:
        event, values = window.read(timeout=10)

        if event in [sg.WIN_CLOSED, 'Exit']:
            break

        if event == '-start_miner-':
            node.start_miner()

        if event == '-stop_miner-':
            node.stop_miner()

    window.close()


if __name__ == '__main__':
    run_node_gui()
