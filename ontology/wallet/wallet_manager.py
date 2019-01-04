#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import copy
import json
import uuid
import base64
import codecs

from datetime import datetime

from ontology.common.define import DID_ONT
from ontology.crypto.scrypt import Scrypt
from ontology.wallet.control import Control
from ontology.common.address import Address
from ontology.account.account import Account
from ontology.wallet.wallet import WalletData
from ontology.wallet.identity import Identity
from ontology.wallet.account import AccountData
from ontology.exception.error_code import ErrorCode
from ontology.wallet.account_info import AccountInfo
from ontology.exception.exception import SDKException
from ontology.crypto.signature_scheme import SignatureScheme
from ontology.utils.utils import get_random_hex_str, is_file_exist


class WalletManager(object):
    def __init__(self, scheme: SignatureScheme = SignatureScheme.SHA256withECDSA):
        if not isinstance(scheme, SignatureScheme):
            raise SDKException(ErrorCode.other_error('Invalid signature scheme.'))
        self.scheme = scheme
        self.wallet_file = WalletData()
        self.wallet_in_mem = WalletData()
        self.__wallet_path = ''

    def open_wallet(self, wallet_path: str):
        self.__wallet_path = wallet_path
        if not is_file_exist(wallet_path):
            raise SDKException(ErrorCode.other_error('Wallet file not found.'))
        self.wallet_file = self.load_file()
        self.wallet_in_mem = copy.deepcopy(self.wallet_file)
        return self.wallet_file

    def create_wallet(self, wallet_path: str):
        if not is_file_exist(wallet_path):
            self.wallet_in_mem.create_time = datetime.today().strftime("%Y-%m-%d %H:%M:%S")
            self.save()
        else:
            raise SDKException(ErrorCode.other_error('Wallet file has existed.'))

    def load_file(self):
        with open(self.__wallet_path, "rb") as f:
            content = f.read()
            if content.startswith(codecs.BOM_UTF8):
                content = content[len(codecs.BOM_UTF8):]
            content = content.decode('utf-8')
            wallet_dict = json.loads(content)
            create_time = wallet_dict.get('createTime', '')
            default_id = wallet_dict.get('defaultOntid', '')
            default_address = wallet_dict.get('defaultAccountAddress', '')
            identities = wallet_dict.get('identities', list())
            try:
                scrypt_dict = wallet_dict['scrypt']
                scrypt_obj = Scrypt(scrypt_dict.get('n', 16384), scrypt_dict.get('r', 8), scrypt_dict.get('p', 8),
                                    scrypt_dict.get('dk_len', 64))
                wallet = WalletData(wallet_dict['name'], wallet_dict['version'], create_time, default_id,
                                    default_address, scrypt_obj, identities, wallet_dict['accounts'])
            except KeyError as e:
                raise SDKException(ErrorCode.param_err(f'wallet file format error: {e}.'))
        return wallet

    def save(self):
        try:
            with open(self.__wallet_path, 'w') as f:
                json.dump(self.wallet_in_mem, f, default=lambda obj: dict(obj), indent=4)
        except FileNotFoundError as e:
            raise SDKException(ErrorCode.other_error(e.args[1])) from None

    def get_wallet(self):
        return self.wallet_in_mem

    def write_wallet(self):
        self.save()
        self.wallet_file = self.wallet_in_mem
        return self.wallet_file

    def reset_wallet(self):
        self.wallet_in_mem = copy.deepcopy(self.wallet_file)
        return self.wallet_in_mem

    def get_signature_scheme(self):
        return self.scheme

    def set_signature_scheme(self, scheme):
        self.scheme = scheme

    def import_identity(self, label: str, encrypted_pri_key: str, pwd: str, salt: str,
                        b58_address: str) -> Identity or None:
        """
        This interface is used to import identity by providing encrypted private key, password, salt and
        base58 encode address which should be correspond to the encrypted private key provided.

        :param label: a label for identity.
        :param encrypted_pri_key: an encrypted private key in base64 encoding from.
        :param pwd: a password which is used to encrypt and decrypt the private key.
        :param salt: a salt value which will be used in the process of encrypt private key.
        :param b58_address: a base58 encode address which correspond with the encrypted private key provided.
        :return: if succeed, an Identity object will be returned.
        """
        scrypt_n = Scrypt().n
        pri_key = Account.get_gcm_decoded_private_key(encrypted_pri_key, pwd, b58_address, salt, scrypt_n, self.scheme)
        info = self.__create_identity(label, pwd, salt, pri_key)
        for identity in self.wallet_in_mem.identities:
            if identity.ont_id == info.ont_id:
                return identity
        raise SDKException(ErrorCode.other_error('Import identity failed.'))

    def create_identity(self, label: str, pwd: str) -> Identity:
        """

        :param label: a label for identity.
        :param pwd: a password which will be used to encrypt and decrypt the private key.
        :return: if succeed, an Identity object will be returned.
        """
        pri_key = get_random_hex_str(64)
        salt = get_random_hex_str(16)
        return self.__create_identity(label, pwd, salt, pri_key)

    def __create_identity(self, label: str, pwd: str, salt: str, private_key: str):
        acct = self.__create_account(label, pwd, salt, private_key, False)
        ont_id = DID_ONT + acct.get_address_base58()
        return self.wallet_in_mem.get_identity_by_ont_id(ont_id)

    def create_identity_from_private_key(self, label: str, pwd: str, private_key: str) -> Identity:
        """
        This interface is used to create identity based on given label, password and private key.

        :param label: a label for identity.
        :param pwd: a password which will be used to encrypt and decrypt the private key.
        :param private_key: a private key in the form of string.
        :return: if succeed, an Identity object will be returned.
        """
        salt = get_random_hex_str(16)
        identity = self.__create_identity(label, pwd, salt, private_key)
        return identity

    def create_account(self, label: str, pwd: str) -> AccountData:
        """
        This interface is used to create account based on given password and label.

        :param label: a label for account.
        :param pwd: a password which will be used to encrypt and decrypt the private key
        :return: if succeed, return an data structure which contain the information of a wallet account.
        """
        pri_key = get_random_hex_str(64)
        salt = get_random_hex_str(16)
        acct = self.__create_account(label, pwd, salt, pri_key, True)
        return self.wallet_in_mem.get_account_by_b58_address(acct.get_address_base58())

    def __create_account(self, label: str, pwd: str, salt: str, private_key: str, account_flag: bool) -> Account:
        account = Account(private_key, self.scheme)
        if self.scheme == SignatureScheme.SHA256withECDSA:
            acct_data = AccountData()
        else:
            raise SDKException(ErrorCode.other_error('Scheme type is error.'))
        if pwd is not None:
            acct_data.key = account.export_gcm_encrypted_private_key(pwd, salt, Scrypt().n)
        else:
            acct_data.key = account.get_private_key_hex()

        acct_data.b58_address = account.get_address_base58()
        # set label
        if label is None or label == '':
            label = uuid.uuid4().hex[0:8]
        if account_flag:
            for memory_acct in self.wallet_in_mem.accounts:
                if memory_acct.b58_address == account.get_address_base58():
                    raise SDKException(ErrorCode.other_error('Wallet account exists.'))
            if len(self.wallet_in_mem.accounts) == 0:
                acct_data.is_default = True
                self.wallet_in_mem.default_account_address = acct_data.b58_address
            acct_data.label = label
            acct_data.salt = base64.b64encode(salt.encode('latin-1')).decode('ascii')
            acct_data.public_key = account.get_public_key_hex()
            self.wallet_in_mem.accounts.append(acct_data)
        else:
            for identity in self.wallet_in_mem.identities:
                if identity.ont_id == DID_ONT + acct_data.b58_address:
                    raise SDKException(ErrorCode.other_error('Wallet identity exists.'))
            idt = Identity()
            idt.ont_id = DID_ONT + acct_data.b58_address
            idt.label = label
            if len(self.wallet_in_mem.identities) == 0:
                idt.is_default = True
                self.wallet_in_mem.default_ont_id = idt.ont_id
            ctl = Control(kid='keys-1', key=acct_data.key, salt=base64.b64encode(salt.encode()).decode('ascii'),
                          address=acct_data.b58_address, public_key=account.get_public_key_hex())
            idt.controls.append(ctl)
            self.wallet_in_mem.identities.append(idt)
        return account

    def add_control(self, ont_id: str, password: str):
        if not ont_id.startswith(DID_ONT):
            raise SDKException(ErrorCode.invalid_ont_id_format(ont_id))
        if not isinstance(password, str):
            raise SDKException(ErrorCode.require_str_params)
        private_key = get_random_bytes(32)
        salt = get_random_hex_str(16)
        b64_salt = base64.b64encode(salt.encode('utf-8')).decode('ascii')
        account = Account(private_key, self.scheme)
        key = account.export_gcm_encrypted_private_key(password, salt, Scrypt().n)
        b58_address = account.get_address_base58()
        public_key = account.get_public_key_hex()
        ctrl = Control(kid='', key=key, salt=b64_salt, address=b58_address, public_key=public_key)
        identity = self.get_identity_by_ont_id(ont_id)
        identity.add_control(ctrl)

    def add_control_by_private_key(self, ont_id: str, password: str, private_key: str) -> Account:
        if not ont_id.startswith(DID_ONT):
            raise SDKException(ErrorCode.invalid_ont_id_format(ont_id))
        if not isinstance(password, str):
            raise SDKException(ErrorCode.require_str_params)
        salt = get_random_hex_str(16)
        b64_salt = base64.b64encode(salt.encode('utf-8')).decode('ascii')
        account = Account(private_key, self.scheme)
        key = account.export_gcm_encrypted_private_key(password, salt, Scrypt().n)
        b58_address = account.get_address_base58()
        public_key = account.get_public_key_hex()
        ctrl = Control(kid='', key=key, salt=b64_salt, address=b58_address, public_key=public_key)
        identity = self.get_identity_by_ont_id(ont_id)
        identity.add_control(ctrl)
        return account

    def import_account(self, label: str, encrypted_pri_key: str, pwd: str, base58_address: str,
                       base64_salt: str) -> AccountData or None:
        """
        This interface is used to import account by providing account data.

        :param label: str, wallet label
        :param encrypted_pri_key: str, an encrypted private key in base64 encoding from
        :param pwd: str, a password which is used to encrypt and decrypt the private key
        :param base58_address: str, a base58 encode  wallet address value
        :param base64_salt: str, a base64 encode salt value which is used in the encryption of private key
        :return:
            if succeed, return an data structure which contain the information of a wallet account.
            if failed, return a None object.
        """
        salt = base64.b64decode(base64_salt.encode('ascii')).decode('latin-1')
        private_key = Account.get_gcm_decoded_private_key(encrypted_pri_key, pwd, base58_address, salt, Scrypt().n,
                                                          self.scheme)
        acct_info = self.create_account_info(label, pwd, salt, private_key)
        for acct in self.wallet_in_mem.accounts:
            if not isinstance(acct, AccountData):
                raise SDKException(ErrorCode.other_error('Invalid account data in memory.'))
            if acct_info.address_base58 == acct.b58_address:
                return acct
        raise SDKException(ErrorCode.other_error('Import account failed.'))

    def create_account_info(self, label: str, pwd: str, salt: str, private_key: str) -> AccountInfo:
        acct = self.__create_account(label, pwd, salt, private_key, True)
        info = AccountInfo()
        info.address_base58 = Address.address_from_bytes_pubkey(acct.get_public_key_bytes()).b58encode()
        info.public_key = acct.get_public_key_bytes().hex()
        info.encrypted_pri_key = acct.export_gcm_encrypted_private_key(pwd, salt, Scrypt().n)
        info.address_u160 = acct.get_address().to_bytes().hex()
        info.salt = salt
        return info

    def create_account_from_private_key(self, label: str, password: str, private_key: str) -> AccountData or None:
        """
        This interface is used to create account by providing an encrypted private key and it's decrypt password.

        :param label: a label for account.
        :param password: a password which is used to decrypt the encrypted private key.
        :param private_key: a private key in the form of string.
        :return: if succeed, return an AccountData object.
                  if failed, return a None object.
        """
        salt = get_random_hex_str(16)
        info = self.create_account_info(label, password, salt, private_key)
        for acct in self.wallet_in_mem.accounts:
            if info.address_base58 == acct.b58_address:
                return acct
        raise SDKException(ErrorCode.other_error(f'Create account from key {private_key} failed.'))

    def get_account_by_ont_id(self, ont_id: str, password: str) -> Account:
        """
        :param ont_id: OntId.
        :param password: a password which is used to decrypt the encrypted private key.
        :return:
        """
        if not ont_id.startswith(DID_ONT):
            raise SDKException(ErrorCode.invalid_ont_id_format(ont_id))
        for identity in self.wallet_in_mem.identities:
            if identity.ont_id == ont_id:
                addr = identity.ont_id.replace(DID_ONT, "")
                key = identity.controls[0].key
                salt = base64.b64decode(identity.controls[0].salt)
                n = self.wallet_in_mem.scrypt.n
                private_key = Account.get_gcm_decoded_private_key(key, password, addr, salt, n, self.scheme)
                return Account(private_key, self.scheme)
        raise SDKException(ErrorCode.other_error(f'Get account {ont_id} failed.'))

    def get_identity_by_ont_id(self, ont_id: str) -> Identity:
        return self.wallet_in_mem.get_identity_by_ont_id(ont_id)

    def get_control_account_by_index(self, ont_id: str, index: int, password: str) -> Account:
        if not ont_id.startswith(DID_ONT):
            raise SDKException(ErrorCode.invalid_ont_id_format(ont_id))
        identity = self.get_identity_by_ont_id(ont_id)
        try:
            ctrl = identity.controls[index]
        except IndexError:
            raise SDKException(ErrorCode.other_error(f'Get {ont_id}\'s control account failed.'))
        salt = base64.b64decode(ctrl.salt)
        key = ctrl.key
        b58_address = ctrl.b58_address
        n = self.wallet_in_mem.scrypt.n
        private_key = Account.get_gcm_decoded_private_key(key, password, b58_address, salt, n, self.scheme)
        return Account(private_key, self.scheme)

    def get_control_account_by_b58_address(self, ont_id: str, b58_address: str, password: str) -> Account:
        if not ont_id.startswith(DID_ONT):
            raise SDKException(ErrorCode.invalid_ont_id_format(ont_id))
        identity = self.get_identity_by_ont_id(ont_id)
        for ctrl in identity.controls:
            if ctrl.b58_address == b58_address:
                salt = base64.b64decode(ctrl.salt)
                key = ctrl.key
                b58_address = ctrl.b58_address
                n = self.wallet_in_mem.scrypt.n
                private_key = Account.get_gcm_decoded_private_key(key, password, b58_address, salt, n, self.scheme)
                return Account(private_key, self.scheme)
        raise SDKException(ErrorCode.other_error(f'Get account {b58_address} failed.'))

    def get_account_by_b58_address(self, b58_address: str, password: str) -> Account:
        """
        :param b58_address: a base58 encode address.
        :param password: a password which is used to decrypt the encrypted private key.
        :return:
        """
        for acct in self.wallet_in_mem.accounts:
            if not isinstance(acct, AccountData):
                raise SDKException(ErrorCode.other_error('Invalid account data in memory.'))
            if acct.b58_address == b58_address:
                n = self.wallet_in_mem.scrypt.n
                salt = base64.b64decode(acct.salt)
                private_key = Account.get_gcm_decoded_private_key(acct.key, password, b58_address, salt, n, self.scheme)
                return Account(private_key, self.scheme)
        raise SDKException(ErrorCode.other_error(f'Get account {b58_address} failed.'))

    def get_default_identity(self) -> Identity:
        for identity in self.wallet_in_mem.identities:
            if identity.is_default:
                return identity
        raise SDKException(ErrorCode.param_error)

    def get_default_account(self) -> AccountData:
        """
        This interface is used to get the default account in WalletManager.

        :return: an AccountData object that contain all the information of a default account.
        """
        for acct in self.wallet_in_mem.accounts:
            if not isinstance(acct, AccountData):
                raise SDKException(ErrorCode.other_error('Invalid account data in memory.'))
            if acct.is_default:
                return acct
        raise SDKException(ErrorCode.get_default_account_err)
