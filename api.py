'''
REST API for the Blockchain
'''
import sqlite3

import requests
import waitress
from flask import Flask, jsonify, request, Response, json, render_template
from formatter import Formatter
from node import Node
from timestamp import utc_timestamp


def create_app(node: Node):
    app = Flask(__name__)
    app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True
    app.config['JSON_SORT_KEYS'] = False

    @app.route('/')
    def hello_world():

        # return "Welcome to the BBPOW!"

        # TODO: In prod enable the index page
        return render_template('index.html', user_ip=node.ip, user_port=node.assigned_port)

    @app.route('/ping/')
    def ping():
        url = f'http://{node.ip}:{node.assigned_port}'
        response_string = f'Successfully pinged {url} at {utc_timestamp()}'
        return Response(response_string, status=200, mimetype='application/json')

    @app.route('/data/')
    def state_of_node():
        f = Formatter()

        state_dict = {
            "height": node.blockchain.height,
            "encoded_target": f.target_from_int(node.blockchain.target),
            "hex_target": format(node.blockchain.target, f'0{f.HASH_CHARS}x'),
            "mining_reward": node.blockchain.mining_reward,
            "total_mine_amount": node.blockchain.total_mining_amount,
            "last_block": json.loads(node.blockchain.last_block.to_json)
        }
        return jsonify(state_dict)

    @app.route('/forks/')
    def show_forks():
        fork_nums = len(node.blockchain.forks)
        fork_dict = {
            "number_of_forks": fork_nums
        }
        for x in range(fork_nums):
            fork_dict.update(
                {f'fork_{x + 1}': node.blockchain.forks[x]}
            )
        return jsonify(fork_dict)

    @app.route('/height/')
    def get_height():
        height_returned = False
        height = 0
        while not height_returned:
            try:
                height = node.blockchain.chain_db.get_height()
                height_returned = True
            except sqlite3.OperationalError:
                pass
        return height

    @app.route('/is_connected/')
    def is_connected_endpoint():
        connected_string = f'Node connected to network: {node.is_connected}'
        if node.is_connected:
            return Response(connected_string, status=200, mimetype='application/json')
        else:
            return Response(connected_string, status=202, mimetype='application/json')

    @app.route('/node_list/', methods=['GET', 'POST', 'DELETE'])
    def get_node_list():
        if request.method == 'GET':
            return jsonify(node.node_list)

        elif request.method == 'POST':
            new_node_dict = request.get_json()
            try:
                ip = new_node_dict['ip']
                port = new_node_dict['port']
                if (ip, port) not in node.node_list:
                    node.node_list.append((ip, port))
                    node.ping_node((ip, port))
                    return Response(status=200, mimetype='application/json')
                elif (ip, port) in node.node_list:
                    return Response(status=202, mimetype='application/json')
            except KeyError:
                return Response(status=400, mimetype='application/json')

        elif request.method == 'DELETE':
            # Get node first
            node_dict = request.get_json()
            try:
                ip = node_dict['ip']
                port = node_dict['port']
            except KeyError:
                return Response(status=400, mimetype='application/json')

            # Confirm connected status
            url = f'http://{ip}:{port}/is_connected'
            headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
            try:
                r = requests.get(url, headers=headers)
            except requests.exceptions.ConnectionError:
                # Logging
                return Response(status=401, mimetype='application/json')

            # Remove node
            if r.status_code == 202:
                try:
                    node.node_list.remove((ip, port))
                    return Response(status=200, mimetype='application/json')
                except ValueError:
                    return Response(status=404, mimetype='application/json')
            else:
                return Response(status=401, mimetype='application/json')

    @app.route('/transaction/', methods=['GET', 'POST'])
    def post_tx():
        if request.method == 'GET':
            validated_tx_dict = {
                "validated_txs": len(node.validated_transactions)
            }
            for tx in node.validated_transactions:
                validated_tx_dict.update({
                    f'tx_{node.validated_transactions.index(tx)}': json.loads(tx.to_json)
                })
            return validated_tx_dict

        elif request.method == 'POST':
            try:
                tx_dict = request.get_json()
                raw_tx = tx_dict['raw_tx']
                tx = node.d.raw_transaction(raw_tx)
                added = node.add_transaction(tx)
                if added:
                    return Response(status=200, mimetype='application/json')
                else:
                    return Response(status=202, mimetype='application/json')
            except Exception as e:
                return Response(status=400, mimetype='application/json')

    @app.route('/transaction/<tx_id>')
    def confirm_tx(tx_id: str):
        block = node.blockchain.find_block_by_tx_id(tx_id)
        tx_dict = {
            "tx_id": tx_id
        }
        if block:
            tx_dict.update({
                "in_chain": True,
                "in_block": block.id,
                "block_height": block.mining_tx.height
            })
        else:
            tx_dict.update({
                "in_chain": False
            })

        return jsonify(tx_dict)

    @app.route('/block/', methods=['GET', 'POST'])
    def get_last_block():
        # Return last block at this endpoint
        if request.method == 'GET':
            return jsonify(json.loads(node.last_block.to_json))

        # Add new block at this endpoint
        if request.method == 'POST':
            try:
                block_dict = json.loads(request.get_json())
                temp_block = node.d.block_from_dict(block_dict)
                if temp_block:
                    # Construction successful, try to add
                    added = node.add_block(temp_block)
                    if added:
                        node.gossip_protocol_block(temp_block)
                        if node.is_mining:
                            # Logging
                            node.logger.info('Restarting Miner after receiving new block.')
                            node.stop_miner()
                            node.start_miner()
                        return Response(status=200, mimetype='application/json')
                    else:
                        return Response(status=202, mimetype='application/json')
                else:
                    return Response(status=406, mimetype='application/json')
            except Exception as e:
                # Logging
                node.logger.error(f'Post request failed with exception {e}')
                return Response(status=404, mimetype='application/json')

    @app.route('/block/<height>/', methods=['GET'])
    def get_block_by_height(height):
        raw_block_returned = False
        raw_block_dict = {}
        while not raw_block_returned:
            try:
                raw_block_dict = node.blockchain.chain_db.get_raw_block(int(height))
                raw_block_returned = True
            except sqlite3.OperationalError:
                pass
        if raw_block_dict:
            raw_block = raw_block_dict['raw_block']
            block = node.d.raw_block(raw_block)
            return jsonify(json.loads(block.to_json))
        else:
            return Response(status=404, mimetype='application/json')

    @app.route('/block/ids/')
    def get_block_ids():
        ids_returned = False
        block_id_dict = {}
        while not ids_returned:
            try:
                block_id_dict = node.blockchain.chain_db.get_block_ids()
                ids_returned = True
            except sqlite3.OperationalError:
                pass
        return block_id_dict

    @app.route('/block/headers/')
    def get_last_block_headers():
        headers_returned = False
        header_dict = {}
        while not headers_returned:
            try:
                header_dict = node.blockchain.chain_db.get_headers_by_height(node.height)
                headers_returned = True
            except sqlite3.OperationalError:
                pass
        return header_dict

    @app.route('/block/headers/<height>')
    def get_headers_by_height(height):
        headers_returned = False
        header_dict = {}
        while not headers_returned:
            try:
                header_dict = node.blockchain.chain_db.get_headers_by_height(int(height))
                headers_returned = True
            except sqlite3.OperationalError:
                pass
        if header_dict:
            return header_dict
        else:
            return Response(status=404, mimetype='application/json')

    @app.route('/raw_block/', methods=['GET', 'POST'])
    def get_last_block_raw():
        # Return last block at this endpoint
        if request.method == 'GET':
            last_block_returned = False
            raw_block_dict = {}
            while not last_block_returned:
                try:
                    raw_block_dict = node.blockchain.chain_db.get_raw_block(node.height)
                    last_block_returned = True
                except sqlite3.OperationalError:
                    pass
            return jsonify(raw_block_dict)

        # Add new block at this endpoint
        if request.method == 'POST':
            raw_block = request.get_data().decode()
            temp_block = node.d.raw_block(raw_block)
            if temp_block:
                # Construction successful, try to add
                added = node.add_block(temp_block)
                if added:
                    node.gossip_protocol_raw_block(temp_block)
                    if node.is_mining:
                        # Logging
                        node.logger.info('Restarting Miner after receiving new block.')
                        node.stop_miner()
                        node.start_miner()
                    return Response(status=200, mimetype='application/json')
                else:
                    return Response(status=202, mimetype='application/json')
            else:
                return Response(status=406, mimetype='application/json')

    @app.route('/raw_block/<height>')
    def get_raw_block_by_height(height):
        block_returned = False
        raw_block_dict = {}
        while not block_returned:
            try:
                raw_block_dict = node.blockchain.chain_db.get_raw_block(int(height))
                block_returned = True
            except sqlite3.OperationalError:
                pass
        if raw_block_dict:
            return raw_block_dict
        else:
            return Response(status=404, mimetype='application/json')

    @app.route('/utxo/')
    def get_utxo_display_info():
        info_string = "Get a utxo by /tx_id/index/."
        return jsonify(info_string)

    @app.route('/utxo/<tx_id>')
    def get_utxos_by_tx_id(tx_id):
        utxos_returned = False
        utxo_dict = {}
        while not utxos_returned:
            try:
                utxo_dict = node.blockchain.chain_db.get_utxos_by_tx_id(tx_id)
                utxos_returned = True
            except sqlite3.OperationalError:
                pass
        return utxo_dict

    @app.route('/utxo/<tx_id>/<index>')
    def get_utxo(tx_id, index):
        utxos_returned = False
        utxo_dict = {}
        while not utxos_returned:
            try:
                utxo_dict = node.blockchain.chain_db.get_utxo(tx_id, index)
                utxos_returned = True
            except sqlite3.OperationalError:
                pass
        return utxo_dict

    @app.route('/<address>')
    def get_utxo_by_address(address: str):
        utxos_returned = False
        utxo_dict = {}
        while not utxos_returned:
            try:
                utxo_dict = node.blockchain.chain_db.get_utxos_by_address(address)
                utxos_returned = True
            except sqlite3.OperationalError:
                pass
        return jsonify(utxo_dict)

    return app


def run_app(node: Node):
    app = create_app(node)
    waitress.serve(app, listen=f'0.0.0.0:{node.assigned_port}')
