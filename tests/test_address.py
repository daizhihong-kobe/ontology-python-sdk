"""
Copyright (C) 2018-2019 The ontology Authors
This file is part of The ontology library.

The ontology is free software: you can redistribute it and/or modify
it under the terms of the GNU Lesser General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

The ontology is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public License
along with The ontology.  If not, see <http://www.gnu.org/licenses/>.
"""

import unittest

from ontology.crypto.hd_public_key import HDPublicKey
from tests import sdk

from ontology.utils import utils
from ontology.common.address import Address


class TestAddress(unittest.TestCase):
    def setUp(self):
        self.bip32_pubkey = b'xpub6CbjoChWbA9TdLQKghCH5GzRrvjPxTiz6kYkW3frXyyN6vfbR7wGkYqd9jyEqkpYRe33oe5sQbamndiWQjc' \
                            b'9X3mr29HdKWqgjwb6G3xYXFo'

    def test_address_from_vm_code(self):
        code = '55c56b6a00527ac46a51527ac46a00c30548656c6c6f7d9c7c756419006a51c300c36a52527ac46a52c3650d006c7' \
               '566620300006c756652c56b6a00527ac46a00c3681553797374656d2e52756e74696d652e4e6f74696679516c7566'
        contract_address = 'f2b6efc3e4360e69b8ff5db8ce8ac73651d07a12'
        self.assertEqual(contract_address, sdk.neo_vm.address_from_avm_code(code).hex())

    def test_b58decode(self):
        length = 20
        rand_code = utils.get_random_bytes(length)
        address = Address(rand_code)
        b58_address = address.b58encode()
        zero = Address.b58decode(b58_address).to_bytes()
        self.assertEqual(rand_code, zero)
        decode_address = Address.b58decode(b58_address).to_bytes()
        self.assertEqual(rand_code, decode_address)

    def test_from_hd_pubkey(self):
        hd_pub_key = HDPublicKey.b58decode(self.bip32_pubkey)
        address = Address.from_hd_public_key(hd_pub_key)
        self.assertEqual('AW8Tf5R4kyURy6LQ8Th181Z5GpTovWGLg6', address.b58encode())
        child_address_lst = ['ARXRQog4iZazp5YfXRyDZvU6ahrt3c2bb7', 'APXh8MqcARUgafqvUNnpECzwKDtipkf3Zr',
                             'ASpmd1MpFSpQ5rhicjRDqBpE1inP3Z7tus', 'APA3M4BRqjBsHXRkeTFiFVb4X1u8FiEgAr',
                             'AKq5SBTCzHBaqWWDUTGvekbsNJKKtf4ff5', 'APzMnHqrGF1cGZyAdFCwEL29TnAgCuBrY6',
                             'AJ8LEkLGeNsWvVrP7SgK9szoZ1MGgUTq1s', 'AJo49LSK6rQEwc6qTYMsAZmvLPRrb6qcWa',
                             'AYzCcNY3PwV432iXVREpDHvpX166KN45xP', 'AbL1wvGCnbzywHBuX1VwQev8xuhJxbPE4P']
        for index, child_address in enumerate(child_address_lst):
            child_pks = HDPublicKey.from_path(hd_pub_key, f'0/{index}')
            address = Address.from_hd_public_key(child_pks[-1])
            self.assertEqual(child_address, address.b58encode())


if __name__ == '__main__':
    unittest.main()
