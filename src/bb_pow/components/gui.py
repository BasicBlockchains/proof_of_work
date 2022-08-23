'''
Main File for GUI
'''
import os
import threading

import PySimpleGUI as sg
from src.bb_pow.components.node import Node
from src.bb_pow.components.api import create_app, run_app
import waitress

# --- CONSTANTS --- #
DEFAULT_THEME = 'SystemDefault'
DEFAULT_WINDOW_SIZE = (1200, 800)


# --- MAIN GUI WINDOW --- #
def create_window(theme=DEFAULT_THEME):
    sg.theme(theme)
    sg.set_global_icon('./images/logo_small.png')
    sg.set_options(font='Ubuntu 12')

    mining_tab_layout = [
        [
            sg.Push(),
            sg.Button('START MINER', auto_size_button=False, size=(12, 2), key='-start_miner-', button_color='#00AA00'),
            sg.Button('STOP MINER', auto_size_button=False, size=(12, 2), key='-stop_miner-', button_color='#FF0000'),
            sg.Push()
        ]
    ]

    layout = [
        [sg.Push(),
         sg.Button('START MINER', auto_size_button=False, size=(12, 2), key='-start_miner-', button_color='#00AA00'),
         sg.Button('STOP MINER', auto_size_button=False, size=(12, 2), key='-stop_miner-', button_color='#FF0000'),
         sg.Push()]
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
