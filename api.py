'''
REST API for the Blockchain
'''
import requests
import waitress
from flask import Flask, jsonify, request, Response, json

from node import Node
from timestamp import utc_timestamp


def create_app(node: Node):
    app = Flask(__name__)
    app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True
    app.config['JSON_SORT_KEYS'] = False

    @app.route('/')
    def hello_world():

        return "Welcome to the BBPOW!"

        # TODO: In prod enable the index page
        # return render_template('index.html')

    @app.route('/ping/')
    def ping():
        return Response(f'{utc_timestamp()}', status=200, mimetype='application/json')

    @app.route('/height/')
    def get_height():
        return node.blockchain.chain_db.get_height()

    @app.route('/is_connected/')
    def is_connected_endpoint():
        if node.is_connected:
            return Response("Node is connected", status=200, mimetype='application/json')
        else:
            return Response("Node is not connected", status=202, mimetype='application/json')

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
                    return Response("New node received", status=200, mimetype='application/json')
                elif (ip, port) in node.node_list:
                    return Response("Post successful, node already in list", status=202, mimetype='application/json')
            except KeyError:
                return Response("Submitted node malformed.", status=400, mimetype='application/json')

        elif request.method == 'DELETE':
            # Get node first
            node_dict = request.get_json()
            try:
                ip = node_dict['ip']
                port = node_dict['port']
            except KeyError:
                return Response("Submitted node malformed.", status=400, mimetype='application/json')

            # Confirm connected status
            url = f'http://{ip}:{port}/is_connected'
            headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
            try:
                r = requests.get(url, headers=headers)
            except requests.exceptions.ConnectionError:
                # Logging
                return Response(f"Could not confirm with {(ip, port)}", status=401, mimetype='application/json')

            # Remove node
            if r.status_code == 202:
                try:
                    node.node_list.remove((ip, port))
                    return Response("Node removed from list", status=200, mimetype='application/json')
                except ValueError:
                    return Response("Submitted node not in node list", status=404, mimetype='application/json')
            else:
                return Response(f"Wrong code from {ip,port} for disconnect", status=401, mimetype='application/json')

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
                    return Response("Tx received and validated or orphaned.", status=200, mimetype='application/json')
                else:
                    return Response("Tx Received but not validated or orphaned.", status=202,
                                    mimetype='application/json')
            except Exception as e:
                return Response(f'Exception encountered handling post request. Error {e}', status=400,
                                mimetype='application/json')

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
                        return Response("Block received and added successfully", status=200,
                                        mimetype='application/json')
                    else:
                        return Response("Block received but not added. Could be forked or orphan.", status=202,
                                        mimetype='application/json')
                else:
                    return Response("Block failed to reconstruct from dict.", status=406, mimetype='application/json')
            except Exception as e:
                # Logging
                node.logger.error(f'Post request failed with exception {e}')
                return Response(f'Post request failed with exception {e}', status=404, mimetype='application/json')

    @app.route('/block/<height>/', methods=['GET'])
    def get_block_by_height(height):
        raw_block_dict = node.blockchain.chain_db.get_raw_block(int(height))
        if raw_block_dict:
            raw_block = raw_block_dict['raw_block']
            block = node.d.raw_block(raw_block)
            return jsonify(json.loads(block.to_json))
        else:
            return Response("No block at that height", status=404, mimetype='application/json')

    @app.route('/block/ids/')
    def get_block_ids():
        return node.blockchain.chain_db.get_block_ids()

    @app.route('/block/headers/')
    def get_last_block_headers():
        return node.blockchain.chain_db.get_headers_by_height(node.height)

    @app.route('/block/headers/<height>')
    def get_headers_by_height(height):
        header_dict = node.blockchain.chain_db.get_headers_by_height(int(height))
        if header_dict:
            return header_dict
        else:
            return Response("No block at that height", status=404, mimetype='application/json')

    @app.route('/raw_block/', methods=['GET', 'POST'])
    def get_last_block_raw():
        # Return last block at this endpoint
        if request.method == 'GET':
            return jsonify(node.blockchain.chain_db.get_raw_block(node.height))

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
                    return Response("Block received and added successfully", status=200,
                                    mimetype='application/json')
                else:
                    return Response("Block received but not added. Could be forked or orphan.", status=202,
                                    mimetype='application/json')
            else:
                return Response("Block failed to reconstruct from dict.", status=406, mimetype='application/json')

    @app.route('/raw_block/<height>')
    def get_raw_block_by_height(height):
        raw_block_dict = node.blockchain.chain_db.get_raw_block(int(height))
        if raw_block_dict:
            return raw_block_dict
        else:
            return Response("No block at that height", status=404, mimetype='application/json')

    @app.route('/utxo/')
    def get_utxo_display_info():
        info_string = "Get a utxo by /tx_id/index/."
        return jsonify(info_string)

    @app.route('/utxo/<tx_id>')
    def get_utxos_by_tx_id(tx_id):
        utxo_dict = node.blockchain.chain_db.get_utxos_by_tx_id(tx_id)
        return utxo_dict

    @app.route('/utxo/<tx_id>/<index>')
    def get_utxo(tx_id, index):
        utxo_dict = node.blockchain.chain_db.get_utxo(tx_id, index)
        return utxo_dict

    @app.route('/<address>')
    def get_utxo_by_address(address: str):
        return jsonify(
            node.blockchain.chain_db.get_utxos_by_address(address)
        )

    return app


def run_app(node: Node):
    app = create_app(node)
    waitress.serve(app, listen=f'0.0.0.0:{node.assigned_port}')
