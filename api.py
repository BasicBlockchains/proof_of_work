'''
REST API for the Blockchain
'''
import random
import secrets

import flask
import requests
import waitress
from flask import Flask, jsonify, request, Response, json, render_template

from decoder import Decoder
from formatter import Formatter
from node import Node
from timestamp import utc_timestamp


def create_app(node: Node):
    app = Flask(__name__)
    app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True
    app.config['JSON_SORT_KEYS'] = False
    mimetype = 'application/json'
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
        genesis_dict = {'raw_genesis': node.blockchain.chain[0].raw_block}
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
        height_dict = {'height': node.height}
        return jsonify(height_dict)

    @app.route('/block/')
    def block():
        block_dict = json.loads(node.last_block.to_json)
        block_dict.update({'raw_block': node.last_block.raw_block})
        return jsonify(block_dict)

    @app.route('/block/<height>')
    def block_height(height: str):
        # Verify height var
        if not height.isnumeric():
            return Response(f'Invalid value {height} for height.', status=400, mimetype=mimetype)
        height = int(height)

        # Check height
        if height > node.height or height < 0:
            return Response(f'No block at height {height}', status=404, mimetype=mimetype)

        # Return block dict
        raw_block_dict = node.blockchain.chain_db.get_raw_block(height)
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

    @app.route('/transactions/')
    def transactions():
        if request.method == 'GET':
            num_valid = len(node.validated_transactions)
            num_orphaned = len(node.orphaned_transactions)

            # Validated txs
            tx_dict = {'validated_txs': num_valid}
            for x in range(num_valid):
                tx_dict.update({f'valid_tx_{x + 1}': json.loads(node.validated_transactions[x].to_json)})

            # Orphaned txs
            tx_dict.update({'orphaned_txs': num_orphaned})
            for y in range(num_orphaned):
                tx_dict.update({f'orphan_tx_{y + 1}': json.loads(node.orphaned_transactions[y].to_json)})
            return jsonify(tx_dict)
        else:
            return Response(f'{request.method} method not allowed at /transactions/ endpoint', status=400,
                            mimetype=mimetype)

    @app.route('/transactions/<tx_id>')
    def find_tx_id(tx_id: str):
        '''
        Will return True/False dict
        '''
        tx_block = node.blockchain.find_block_by_tx_id(tx_id)
        tx_dict = {
            'in_chain': tx_block is not None
        }
        if tx_block:
            tx_dict.update({
                'in_block': tx_block.height
            })
        return jsonify(tx_dict)

    @app.route('/<address>/')
    def address(address: str):
        '''
        Returns dict of utxos for this address
        '''
        utxo_dict = node.blockchain.chain_db.get_utxos_by_address(address)
        return jsonify(utxo_dict)

    @app.route('/node_list/')
    def node_list():
        if request.method == 'GET':
            random_node_list = []
            node_list_index = node.node_list.copy()
            while len(random_node_list) < Formatter.HEARTBEAT and node_list_index != []:
                # Add random nodes to list until we have HEARTBEAT or we empty the node_list_index
                random_node_list.append(node_list_index.pop(secrets.randbelow(len(node_list_index))))
            return jsonify(random_node_list)
        else:
            return Response(f'{request.method} method not allowed at /node_list/ endpoint', status=400,
                            mimetype=mimetype)

    # --- DYNAMIC ENDPOINTS --- #
    @app.route('/node/', methods=['POST', 'DELETE'])
    def handle_node():
        if request.method in ['POST', 'DELETE']:
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
                    node.gossip_protocol_block(test_block)

                    # Restart mining
                    if resume_mining:
                        node.start_miner()

                    # Return success
                    return Response(f'Successfully added block at height {test_block.height} for {node.node}',
                                    status=200, mimetype=mimetype)
                elif {test_block.height: test_block.raw_block} in node.blockchain.forks:
                    return Response(f'Raw block added to forks in {node.node}', status=202, mimetype=mimetype)
                else:
                    return Response(f'Failed to add or fork block', status=400, mimetype=mimetype)

            else:
                return Response(f'Failed to reconstruct raw block {raw_block}', status=400, mimetype=mimetype)

    @app.route('/raw_block/<height>', methods=['GET'])
    def handle_indexed_raw_block(height: str):
        # Get height as integer
        if not height.isnumeric():
            return Response(f'Incorrect value {height} for height variable', status=400, mimetype=mimetype)
        height = int(height)

        # Check height
        if height > node.height or height < 0:
            return Response(f'No block at height {height}', status=404, mimetype=mimetype)

        # Return block dict
        raw_block_dict = node.blockchain.chain_db.get_raw_block(height)
        return jsonify(raw_block_dict)

    @app.route('/raw_tx/', methods=['POST'])
    def handle_raw_tx():
        # POST RAW TX
        if request.method == 'POST':
            # dict format = {'raw_tx': <raw_tx>}
            try:
                raw_tx_dict = request.get_json()
                raw_tx = raw_tx_dict['raw_tx']
            except requests.exceptions.JSONDecodeError:
                return Response('JSON Decode error', status=400, mimetype=mimetype)
            except KeyError:
                return Response('Raw tx dict error', status=400, mimetype=mimetype)

            # Verify raw_tx
            new_tx = d.raw_transaction(raw_tx)
            if new_tx:
                added = node.add_transaction(new_tx)
                if added:
                    return Response(f'{node.node} received raw_tx with id {new_tx.id} successfully.', status=200,
                                    mimetype=mimetype)
                else:
                    # raw_tx decoded but not added to node
                    return Response(f'{node.node} received raw_tx with id {new_tx.id} but was unable to process it.',
                                    status=406, mimetype=mimetype)
            else:
                # unable to decode raw_tx
                return Response(f'Unable to decode raw_tx {raw_tx}', status=400, mimetype=mimetype)
        else:
            # method other than POST
            return Response(f'{request.method} not allowed for /raw_tx/ endpoint', status=403, mimetype=mimetype)

    return app


def run_app(node: Node):
    app = create_app(node)
    waitress.serve(app, listen=f'0.0.0.0:{node.assigned_port}', clear_untrusted_proxy_headers=True)
