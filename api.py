'''
REST API for the Blockchain
'''
import sqlite3

import flask
import requests
import waitress
from flask import Flask, jsonify, request, Response, json, render_template
from formatter import Formatter
from node import Node
from timestamp import utc_timestamp
from decoder import Decoder
from hashlib import sha256


def create_app(node: Node):
    app = Flask(__name__)
    app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True
    app.config['JSON_SORT_KEYS'] = False
    mimetype = 'application/json'
    f = Formatter()
    d = Decoder()

    @app.route('/')
    def home():
        return render_template('index.html', user_ip=node.ip, user_port=node.assigned_port)

    # --- STATIC GET ENDPOINTS --- #

    @app.route('/ping/')
    def ping():
        client_ip = flask.request.remote_addr
        response_string = f'Successful ping from {client_ip} to {node.ip}:{node.assigned_port} at {utc_timestamp()}'
        return Response(response_string, status=200, mimetype=mimetype)

    @app.route('/genesis_block/')
    def genesis_block():
        genesis_dict = {
            'raw_genesis': node.blockchain.chain[0].raw_block
        }
        return jsonify(genesis_dict)

    @app.route('/is_connected/')
    def is_connected():
        connected_string = f'Node connected to network: {node.is_connected}'
        if node.is_connected:
            return Response(connected_string, status=200, mimetype='application/json')
        else:
            return Response(connected_string, status=202, mimetype='application/json')

    @app.route('/height/')
    def height():
        height_dict = {
            'height': node.height
        }
        return jsonify(height_dict)

    @app.route('/block/')
    def block():
        block_dict = json.loads(node.last_block.to_json)
        block_dict.update({
            'raw_block': node.last_block.raw_block
        })
        return jsonify(block_dict)

    @app.route('/block/<height>')
    def block_height(height: int):
        # Check height
        if height > node.height or height < 0:
            return Response(f'No block at height {height}', status=400, mimetype=mimetype)

        # Return block dict
        raw_block_dict = json.loads(
            node.blockchain.chain_db.get_raw_block(height)
        )
        if raw_block_dict:
            raw_block = raw_block_dict['raw_block']
            temp_block = d.raw_block(raw_block)
            block_dict = json.loads(temp_block.to_json)
            block_dict.update({
                'raw_block': raw_block
            })
            return jsonify(block_dict)
        else:
            return Response(f'No block retrieved at height {height}', status=500, mimetype=mimetype)

    # --- DYNAMIC ENDPOINTS --- #
    @app.route('/node_list/', methods=['PUT', 'POST', 'DELETE'])
    def handle_node():
        if request.method in ['PUT', 'POST', 'DELETE']:
            # dict format = {'ip':<ip>, 'port':<port>}
            try:
                client_node_dict = request.get_json()
                ip = client_node_dict['ip']
                port = client_node_dict['port']
            except requests.exceptions.JSONDecodeError:
                return Response('JSON Decode error', status=400, mimetype=mimetype)
            except KeyError:
                return Response('Node dict error', status=400, mimetype=mimetype)

            # Validate client
            client_node = (ip, port)
            client_valid = node.check_genesis(client_node)
            if not client_valid:
                # Logging
                critical_message = f'Received {request.method} request from invalid client {client_node}'
                node.logger.critical(critical_message)
                return Response(critical_message, status=401, mimetype=mimetype)

            # PUT - RETURN NODE LIST
            if request.method == 'PUT':
                # Return node_list
                return jsonify(node.node_list)

            # POST - NEW CONNECTION
            if request.method == 'POST':
                if client_node not in node.node_list:
                    # Confirm connected status
                    connected = node.check_connected_status(client_node)
                    if connected:
                        node.node_list.append(client_node)
                        return Response(f'Added {client_node} to node_list in {node}.', status=200, mimetype=mimetype)
                    else:
                        return Response(f'{client_node} does not return connected status', status=401,
                                        mimetype=mimetype)
                else:
                    # Return success but not 200 if node already in node_list
                    return Response(f'{client_node} already in node list for {node.node}', status=202,
                                    mimetype=mimetype)

            # DELETE - REMOVE CONNECTION
            elif request.method == 'DELETE':
                if client_node in node.node_list:
                    # Confirm delete
                    disconnected = node.check_disconnected_status(client_node)
                    if disconnected:
                        node.node_list.remove(client_node)
                        return Response(f'Removed {client_node} from node_list.', status=200, mimetype=mimetype)
                    else:
                        # Logging
                        critical_message = f'Received DELETE request from {client_node} without disconnected status'
                        node.logger.critical(critical_message)
                        return Response(critical_message, status=401, mimetype=mimetype)
                else:
                    # Logging
                    node.logger.critical(f'Received DELETE request from {client_node} not found in node list.')
                    return Response(f'{client_node} not found in node_list', status=405, mimetype=mimetype)

        else:
            message = f'{request.method} method not available for /node_list'
            return Response(message, status=403, mimetype='application/json')

    @app.route('/raw_block/', methods=['GET', 'POST'])
    def handle_raw_block():
        # GET LAST RAW BLOCK
        if request.method == 'GET':
            raw_block_dict = {'raw_block': node.last_block.raw_block}
            return jsonify(raw_block_dict)

        # POST RAW BLOCK
        elif request.method == 'POST':
            # dict format = {'raw_block': <raw_block>}
            try:
                raw_block_dict = request.get_json()
                raw_block = raw_block_dict['raw_block']
            except requests.exceptions.JSONDecodeError:
                return Response('JSON Decode error', status=400, mimetype=mimetype)
            except KeyError:
                return Response('Raw block dict error', status=400, mimetype=mimetype)

            # Verify raw_block
            test_block = d.raw_block(raw_block)
            if test_block:
                added = node.add_block(test_block)
                if added:
                    # Stop mining
                    resume_mining = node.is_mining
                    node.stop_miner()

                    # # Gossip block
                    # node.gossip_protocol_block(test_block)

                    # Restart mining
                    if resume_mining:
                        node.start_miner()
                    #
                    #     # Return success
                    return Response(f'Successfully added block at height {test_block.height} for {node.node}',
                                    status=200, mimetype=mimetype)
                elif {test_block.height: test_block.raw_block} in node.blockchain.forks:
                    return Response(f'Raw block added to forks in {node.node}', status=202, mimetype=mimetype)
                else:
                    return Response(f'Failed to add or fork block', status=400, mimetype=mimetype)

            else:
                return Response(f'Failed to reconstruct raw block {raw_block}', status=400, mimetype=mimetype)

    @app.route('/raw_block/<height>')
    def handle_indexed_raw_block(height: str):
        # Get height as integer
        if not height.isnumeric():
            return Response(f'Incorrect value {height} for height variable', status=400, mimetype=mimetype)
        height = int(height)

        # Check height
        if height > node.height or height < 0:
            return Response(f'No block at height {height}', status=400, mimetype=mimetype)

        # Return block dict
        raw_block_dict = node.blockchain.chain_db.get_raw_block(height)
        return jsonify(raw_block_dict)

    # --- QUALITY OF LIFE ENDPOINTS --- #

    # @app.route('/data/')
    # def state_of_node():
    #     f = Formatter()
    #
    #     state_dict = {
    #         "height": node.blockchain.height,
    #         "encoded_target": f.target_from_int(node.blockchain.target),
    #         "hex_target": format(node.blockchain.target, f'0{f.HASH_CHARS}x'),
    #         "mining_reward": node.blockchain.mining_reward,
    #         "total_mine_amount": node.blockchain.total_mining_amount,
    #         "last_block": json.loads(node.blockchain.last_block.to_json)
    #     }
    #     return jsonify(state_dict)
    #
    # @app.route('/forks/')
    # def show_forks():
    #     fork_nums = len(node.blockchain.forks)
    #     fork_dict = {
    #         "number_of_forks": fork_nums
    #     }
    #     for x in range(fork_nums):
    #         fork_dict.update(
    #             {f'fork_{x + 1}': node.blockchain.forks[x]}
    #         )
    #     return jsonify(fork_dict)

    #
    # @app.route('/transaction/', methods=['GET', 'POST'])
    # def post_tx():
    #     if request.method == 'GET':
    #         validated_tx_dict = {
    #             "validated_txs": len(node.validated_transactions)
    #         }
    #         for tx in node.validated_transactions:
    #             validated_tx_dict.update({
    #                 f'tx_{node.validated_transactions.index(tx)}': json.loads(tx.to_json)
    #             })
    #         return validated_tx_dict
    #
    #     elif request.method == 'POST':
    #         try:
    #             tx_dict = request.get_json()
    #             raw_tx = tx_dict['raw_tx']
    #             tx = node.d.raw_transaction(raw_tx)
    #             added = node.add_transaction(tx)
    #             if added:
    #                 return Response(status=200, mimetype='application/json')
    #             else:
    #                 return Response(status=202, mimetype='application/json')
    #         except Exception as e:
    #             return Response(status=400, mimetype='application/json')
    #
    # @app.route('/transaction/<tx_id>')
    # def confirm_tx(tx_id: str):
    #     block = node.blockchain.find_block_by_tx_id(tx_id)
    #     tx_dict = {
    #         "tx_id": tx_id
    #     }
    #     if block:
    #         tx_dict.update({
    #             "in_chain": True,
    #             "in_block": block.id,
    #             "block_height": block.mining_tx.height
    #         })
    #     else:
    #         tx_dict.update({
    #             "in_chain": False
    #         })
    #
    #     return jsonify(tx_dict)
    #
    # @app.route('/block/', methods=['GET', 'POST'])
    # def get_last_block():
    #     # Return last block at this endpoint
    #     if request.method == 'GET':
    #         return jsonify(json.loads(node.last_block.to_json))
    #
    #     # Add new block at this endpoint
    #     if request.method == 'POST':
    #         try:
    #             block_dict = json.loads(request.get_json())
    #             temp_block = node.d.block_from_dict(block_dict)
    #             if temp_block:
    #                 # Construction successful, try to add
    #                 added = node.add_block(temp_block)
    #                 if added:
    #                     node.gossip_protocol_block(temp_block)
    #                     if node.is_mining:
    #                         # Logging
    #                         node.logger.info('Restarting Miner after receiving new block.')
    #                         node.stop_miner()
    #                         node.start_miner()
    #                     return Response(status=200, mimetype='application/json')
    #                 else:
    #                     return Response(status=202, mimetype='application/json')
    #             else:
    #                 return Response(status=406, mimetype='application/json')
    #         except Exception as e:
    #             # Logging
    #             node.logger.error(f'Post request failed with exception {e}')
    #             return Response(status=404, mimetype='application/json')
    #
    # @app.route('/block/<height>/', methods=['GET'])
    # def get_block_by_height(height):
    #     raw_block_returned = False
    #     raw_block_dict = {}
    #     while not raw_block_returned:
    #         try:
    #             raw_block_dict = node.blockchain.chain_db.get_raw_block(int(height))
    #             raw_block_returned = True
    #         except sqlite3.OperationalError:
    #             pass
    #     if raw_block_dict:
    #         raw_block = raw_block_dict['raw_block']
    #         block = node.d.raw_block(raw_block)
    #         return jsonify(json.loads(block.to_json))
    #     else:
    #         return Response(status=404, mimetype='application/json')
    #
    # @app.route('/block/ids/')
    # def get_block_ids():
    #     ids_returned = False
    #     block_id_dict = {}
    #     while not ids_returned:
    #         try:
    #             block_id_dict = node.blockchain.chain_db.get_block_ids()
    #             ids_returned = True
    #         except sqlite3.OperationalError:
    #             pass
    #     return block_id_dict
    #
    # @app.route('/block/headers/')
    # def get_last_block_headers():
    #     headers_returned = False
    #     header_dict = {}
    #     while not headers_returned:
    #         try:
    #             header_dict = node.blockchain.chain_db.get_headers_by_height(node.height)
    #             headers_returned = True
    #         except sqlite3.OperationalError:
    #             pass
    #     return header_dict
    #
    # @app.route('/block/headers/<height>')
    # def get_headers_by_height(height):
    #     headers_returned = False
    #     header_dict = {}
    #     while not headers_returned:
    #         try:
    #             header_dict = node.blockchain.chain_db.get_headers_by_height(int(height))
    #             headers_returned = True
    #         except sqlite3.OperationalError:
    #             pass
    #     if header_dict:
    #         return header_dict
    #     else:
    #         return Response(status=404, mimetype='application/json')
    #
    # @app.route('/raw_block/', methods=['GET', 'POST'])
    # def get_last_block_raw():
    #     # Return last block at this endpoint
    #     if request.method == 'GET':
    #         last_block_returned = False
    #         raw_block_dict = {}
    #         while not last_block_returned:
    #             try:
    #                 raw_block_dict = node.blockchain.chain_db.get_raw_block(node.height)
    #                 last_block_returned = True
    #             except sqlite3.OperationalError:
    #                 pass
    #         return jsonify(raw_block_dict)
    #
    #     # Add new block at this endpoint
    #     if request.method == 'POST':
    #         raw_block = request.get_data().decode()
    #         temp_block = node.d.raw_block(raw_block)
    #         if temp_block:
    #             # Construction successful, try to add
    #             added = node.add_block(temp_block)
    #             if added:
    #                 node.gossip_protocol_raw_block(temp_block)
    #                 if node.is_mining:
    #                     # Logging
    #                     node.logger.info('Restarting Miner after receiving new block.')
    #                     node.stop_miner()
    #                     node.start_miner()
    #                 return Response(status=200, mimetype='application/json')
    #             else:
    #                 return Response(status=202, mimetype='application/json')
    #         else:
    #             return Response(status=406, mimetype='application/json')
    #
    # @app.route('/raw_block/<height>')
    # def get_raw_block_by_height(height):
    #     block_returned = False
    #     raw_block_dict = {}
    #     while not block_returned:
    #         try:
    #             raw_block_dict = node.blockchain.chain_db.get_raw_block(int(height))
    #             block_returned = True
    #         except sqlite3.OperationalError:
    #             pass
    #     if raw_block_dict:
    #         return raw_block_dict
    #     else:
    #         return Response(status=404, mimetype='application/json')
    #
    # @app.route('/utxo/')
    # def get_utxo_display_info():
    #     info_string = "Get a utxo by /tx_id/index/."
    #     return jsonify(info_string)
    #
    # @app.route('/utxo/<tx_id>')
    # def get_utxos_by_tx_id(tx_id):
    #     utxos_returned = False
    #     utxo_dict = {}
    #     while not utxos_returned:
    #         try:
    #             utxo_dict = node.blockchain.chain_db.get_utxos_by_tx_id(tx_id)
    #             utxos_returned = True
    #         except sqlite3.OperationalError:
    #             pass
    #     return utxo_dict
    #
    # @app.route('/utxo/<tx_id>/<index>')
    # def get_utxo(tx_id, index):
    #     utxos_returned = False
    #     utxo_dict = {}
    #     while not utxos_returned:
    #         try:
    #             utxo_dict = node.blockchain.chain_db.get_utxo(tx_id, index)
    #             utxos_returned = True
    #         except sqlite3.OperationalError:
    #             pass
    #     return utxo_dict
    #
    # @app.route('/<address>')
    # def get_utxo_by_address(address: str):
    #     utxos_returned = False
    #     utxo_dict = {}
    #     while not utxos_returned:
    #         try:
    #             utxo_dict = node.blockchain.chain_db.get_utxos_by_address(address)
    #             utxos_returned = True
    #         except sqlite3.OperationalError:
    #             pass
    #     return jsonify(utxo_dict)

    return app


def run_app(node: Node):
    app = create_app(node)
    waitress.serve(app, listen=f'0.0.0.0:{node.assigned_port}', clear_untrusted_proxy_headers=True)
