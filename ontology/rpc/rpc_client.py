import requests
from ontology.rpc.define import *
import json
from time import time
from ontology.utils import util
from ontology.vm.neo_vm import build_neo_vm
from ontology.core.transaction import Transaction, Sig
from ontology.account.client import Account
from ontology.crypto.KeyType import KeyType
from ontology.crypto.SignatureScheme import SignatureScheme
from ontology.common.address import Address
from ontology.utils.util import bytes_reader
# from ontology.crypto.Signature import signature_serializae

rpc_address = "http://polaris1.ont.io:20336"
rest_address = "http://polaris1.ont.io:20334"


class HttpRequest(object):
    _timeout = 10

    @staticmethod
    def set_timeout(timeout=10):
        HttpRequest._timeout = timeout

    @staticmethod
    def request(method, url, payload):
        header = {'Content-type': 'application/json'}
        if method == "post":
            res = requests.post(url, json=payload, headers=header, timeout=HttpRequest._timeout)
            return res
        elif method == "get":
            res = requests.get(url, params=json.dumps(payload), timeout=HttpRequest._timeout)
            return res


class RpcClient(object):
    def __init__(self, qid=0, addr=""):
        self.qid = qid
        self.addr = addr

    def set_address(self, addr):
        self.addr = addr

    def set_json_rpc_version(self, method, param=[]):
        JsonRpcRequest["jsonrpc"] = JSON_RPC_VERSION
        JsonRpcRequest["id"] = "1"
        JsonRpcRequest["method"] = method
        JsonRpcRequest["params"] = param
        return JsonRpcRequest

    def get_version(self) -> str:
        rpc_struct = self.set_json_rpc_version(RPC_GET_VERSION, [])
        r = HttpRequest.request("post", self.addr, rpc_struct)
        res = json.loads(r.content.decode())["result"]
        return res

    def get_block_by_hash(self, hash: str):
        rpc_struct = self.set_json_rpc_version(RPC_GET_BLOCK, [hash, 1])
        r = HttpRequest.request("post", self.addr, rpc_struct)
        res = json.loads(r.content.decode())["result"]
        return res

    def get_block_by_height(self, height):
        rpc_struct = self.set_json_rpc_version(RPC_GET_BLOCK, [height, 1])
        r = HttpRequest.request("post", self.addr, rpc_struct)
        res = json.loads(r.content.decode())["result"]
        return res

    def get_block_count(self):
        rpc_struct = self.set_json_rpc_version(RPC_GET_BLOCK_COUNT)
        r = HttpRequest.request("post", self.addr, rpc_struct)
        res = json.loads(r.content.decode())["result"]
        return res

    def get_current_block_hash(self):
        rpc_struct = self.set_json_rpc_version(RPC_GET_CURRENT_BLOCK_HASH)
        r = HttpRequest.request("post", self.addr, rpc_struct)
        res = json.loads(r.content.decode())["result"]
        return res

    def get_block_hash_by_height(self, height):
        rpc_struct = self.set_json_rpc_version(RPC_GET_BLOCK_HASH, [height, 1])
        r = HttpRequest.request("post", self.addr, rpc_struct)
        res = json.loads(r.content.decode())["result"]
        return res

    def get_balance(self, addr):
        rpc_struct = self.set_json_rpc_version(RPC_GET_BALANCE, [addr, 1])
        r = HttpRequest.request("post", self.addr, rpc_struct)
        res = json.loads(r.content.decode())["result"]
        return res

    def get_storage(self, addr, key):
        rpc_struct = self.set_json_rpc_version(RPC_GET_STORAGE, [addr, key, 1])
        r = HttpRequest.request("post", self.addr, rpc_struct)
        s = json.loads(r.content.decode())["result"]
        s = bytearray.fromhex(s)
        res = (s[0]) | (s[1]) << 8 | (s[2]) << 16 | (s[3]) << 24 | (s[4]) << 32 | (s[5]) << 40 | (s[6]) << 48 | (
            s[7]) << 56
        return res

    def get_smart_contract_event_by_txhash(self, tx_hash):
        rpc_struct = self.set_json_rpc_version(RPC_GET_SMART_CONTRACT_EVENT, [tx_hash, 1])
        r = HttpRequest.request("post", self.addr, rpc_struct)
        res = json.loads(r.content.decode())["result"]
        return res

    def get_smart_contract_event_by_block(self, height):
        rpc_struct = self.set_json_rpc_version(RPC_GET_SMART_CONTRACT_EVENT, [height, 1])
        r = HttpRequest.request("post", self.addr, rpc_struct)
        res = json.loads(r.content.decode())["result"]
        return res

    def get_raw_transaction(self, tx_hash):
        rpc_struct = self.set_json_rpc_version(RPC_GET_TRANSACTION, [tx_hash, 1])
        r = HttpRequest.request("post", self.addr, rpc_struct)
        res = json.loads(r.content.decode())["result"]
        return res

    def get_smart_contract(self, contract_addr):
        rpc_struct = self.set_json_rpc_version(RPC_GET_SMART_CONTRACT, [contract_addr, 1])
        r = HttpRequest.request("post", self.addr, rpc_struct)
        res = json.loads(r.content.decode())["result"]
        return res

    def get_generate_block_time(self):
        rpc_struct = self.set_json_rpc_version(RPC_GET_GENERATE_BLOCK_TIME)
        r = HttpRequest.request("post", self.addr, rpc_struct)
        res = json.loads(r.content.decode())["result"]
        return res

    def get_merkle_proof(self, tx_hash):
        rpc_struct = self.set_json_rpc_version(RPC_GET_MERKLE_PROOF, [tx_hash, 1])
        r = HttpRequest.request("post", self.addr, rpc_struct)
        res = json.loads(r.content.decode())["result"]
        return res

    def transfer(self, gas_price: int, gas_limit: int, asset: str, from_account, to_addr, amount: int):
        tx = self.new_transfer_transaction(gas_price, gas_limit, asset, from_account.get_address(), to_addr, amount)
        tx = self.sign_to_transaction(tx, from_account)
        #util.print_byte_array(tx.serialize())
        print(bytes_reader(tx.serialize_unsigned()).hex())
        #self.send_raw_transaction(tx)
        return tx

    def new_transfer_transaction(self, gas_price, gas_limit, asset, from_addr, to_addr, amount):
        contract_address = util.get_asset_address(asset)  # []bytes
        state = [{"from": from_addr, "to": to_addr, "amount": amount}]
        invoke_code = build_neo_vm.build_native_invoke_code(contract_address, bytes([0]), "transfer", state)
        unix_timenow = 1#int(time())
        return Transaction(0, 0xd1, unix_timenow, gas_price, gas_limit, bytearray(), invoke_code, bytearray(),
                           [], bytearray())

    def sign_to_transaction(self, tx, signer: Account):
        tx.payer = signer.get_address().to_array()
        tx_hash = tx.hash256()
        sig_data = self.sign_to_data(tx_hash, signer)
        sig = [Sig([signer.get_public_key()], 1, [sig_data])]
        #print("## %s" %sig[0].M)
        tx.sigs = sig
        return tx

    def sign_to_data(self, data, signer: Account):
        signed_data = signer.generateSignature(data, SignatureScheme.SHA256withECDSA)
        return signed_data

    def send_raw_transaction(self, tx):
        buf = tx.serialize()
        tx_data = buf.hex()
        rpc_struct = self.set_json_rpc_version(RPC_GET_TRANSACTION, [tx_data, 1])
        r = HttpRequest.request("post", self.addr, rpc_struct)
        res = json.loads(r.content.decode())["result"]
        return res


if __name__ == '__main__':
    cli = RpcClient(0,rpc_address)
    #from_addr = bytearray(
    #    [233, 90, 124, 86, 153, 119, 43, 68, 212, 191, 87, 222, 85, 139, 32, 23, 162, 238, 135, 191])
    #to_addr = bytearray(
    #    [133, 121, 185, 144, 156, 79, 58, 123, 214, 186, 172, 168, 89, 189, 199, 202, 42, 40, 22, 207])
    private_key = "523c5fcf74823831756f0bcb3634234f10b3beb1c05595058534577752ad2d9f"
    acc = Account(private_key, KeyType.ECDSA)
    print(acc.get_address_base58())
    print(acc.get_public_key().hex())
    toAddr = Address.decodeBase58("AKFMnJT1u5pyPhzGRuauD1KkyUvqjQsmGs")
    print(toAddr.to_array().hex())
    str = "00d101000000f401000000000000204e0000000000004756c9dd829b2142883adbe1ae4f8689a1f673e97100c66b144756c9dd829b2142883adbe1ae4f8689a1f673e96a7cc814261b18069e80f351a202cd1d230641dfa450b83b6a7cc8516a7cc86c51c1087472616e736665721400000000000000000000000000000000000000010068164f6e746f6c6f67792e4e61746976652e496e766f6b650000"
    print(str)
    res = cli.transfer(500, 20000, "ont", acc, toAddr.to_array(), 1)
    #print(res)



    #00d101000000f401000000000000204e0000000000004756c9dd829b2142883adbe1ae4f8689a1f673e97100c66b144756c9dd829b2142883adbe1ae4f8689a1f673e96a7cc814261b18069e80f351a202cd1d230641dfa450b83b6a7cc8516a7cc86c51c1087472616e736665721400000000000000000000000000000000000000010068164f6e746f6c6f67792e4e61746976652e496e766f6b650000
    #00d101000000f401000000000000204e0000000000004756c9dd829b2142883adbe1ae4f8689a1f673e900c66b6a7cc86                                                                                      a7cc8516a7cc86c51c1087472616e736665721400000000000000000000000000000000000000010068164f6e746f6c6f67792e4e61746976652e496e766f6b650000