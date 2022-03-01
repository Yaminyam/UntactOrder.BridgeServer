# -*- coding: utf-8 -*-
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
### Alias : BridgeServer.settings & Last Modded : 2022.02.27. ###
Coded with Python 3.10 Grammar by IRACK000
Description : BridgeServer Settings
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
from os import path, mkdir
import sys
import platform
import ssl
from getpass import getpass
from OpenSSL import crypto

builtin_print = print
from rich import print
from rich.traceback import install as install_traceback
install_traceback()


# public ip API link
IP_API_URL = "https://api.ipify.org"

# certificate settings
TYPE_RSA = crypto.TYPE_RSA
SHA256 = 'SHA256'
FILETYPE_PEM = crypto.FILETYPE_PEM

# os info
OS = platform.system()


class UnitType(object):
    unit_text = "A % Instance"
    CERT = unit_text.replace('%', "CertServer")
    BRIDGE = unit_text.replace('%', "BridgeServer")
    POS = unit_text.replace('%', "PosServer")


# server unit type setting
UNIT_TYPE = UnitType.BRIDGE
unit_type = "bridge" if UNIT_TYPE == UnitType.BRIDGE else "pos" if UNIT_TYPE == UnitType.POS else "cert"

# certificate path settings
CERT_DIR = "cert" if OS == "Windows" else f"/etc/{unit_type}server"
if not path.isdir(CERT_DIR):
    mkdir(CERT_DIR)
CERT_FILE = path.join(CERT_DIR, f"{unit_type}.crt")
KEY_FILE = path.join(CERT_DIR, f"{unit_type}.key")
PASS_FILE = path.join(CERT_DIR, "ssl.pass")
ROOT_CA = path.join(CERT_DIR, "rootCA.crt")
BUNDLE_CERT = path.join("root", "rootca.bundlecert")

# server settings path
SETTING_DIR = "data"
if path.isdir(SETTING_DIR):
    mkdir(SETTING_DIR)
SETTING_FILE_EXT = path.join(SETTING_DIR, f".{unit_type}setting")
CERT_SERVER = path.join("root", "rootca" + SETTING_FILE_EXT)
GATEWAY = path.join(SETTING_DIR, "gateway" + SETTING_FILE_EXT)
DB_LIST = path.join(SETTING_DIR, "db" + SETTING_FILE_EXT)

# organization name
ORGANIZATION = "UntactOrder"


class NetworkConfig(object):
    """ Network Setting """

    def __init__(self):
        # gateway settings for block arp attack

        from network import network
        info = network.get_network_info()
        self.ip_version = info['protocol_version']
        self.device = info['device']
        self.gateway_ip = info['target']['ip']
        self.gateway_mac = info['target']['mac']
        self.gateway_is_static = info['target']['is_static']
        self.internal_ip = info['internal_ip']
        self.external_ip = info['external_ip']

        if not path.isfile(GATEWAY):
            with open(GATEWAY, 'w+', encoding='utf-8') as gateway:
                gateway.write(",".join([self.gateway_ip, self.gateway_mac]))
        else:
            with open(GATEWAY, 'r', encoding='utf-8') as gateway:
                gateway_ip, gateway_mac = gateway.read().split(",")

            if gateway_ip != self.gateway_ip or gateway_mac != self.gateway_mac:
                print(f"[red]WARNING: Gateway address or mac has changed."
                      f" {gateway_ip} => {self.gateway_ip} | {gateway_mac} => {self.gateway_mac}[/red]")
                if network.are_duplicated_mac_exist():
                    print("[red]> Duplicated MAC address exist. It may be an ARP vulnerability attack, "
                          "so proceed after restoring to the previous state. "
                          "If it doesn't work normally, please check your network connection.[/red]")
                    self.gateway_ip = gateway_ip
                    self.gateway_mac = gateway_mac
                else:
                    print("[green]> ARP attack is not detected. Proceeding...[/green]")
                    print("[yellow]Did you changed your gateway device recently? "
                          "If so, this script overwrite the previous record(ip, mac) and proceed.[/yellow] (y to yes)")
                    if input().lower() != 'y':
                        print("[blue]>Overwrite Aborted. Do manually check your gateway status.[/blue]")
                        sys.exit(1)
                    else:
                        with open(GATEWAY, 'w+', encoding='utf-8') as gateway:
                            gateway.write(",".join([self.gateway_ip, self.gateway_mac]))
                        print("[blue]Overwrite Success.[/blue]")

        network.set_arp_static(self.ip_version, self.device, self.internal_ip, self.gateway_ip, self.gateway_mac)

    def is_public_ip_changed(self, stored_external_ip):
        """ Check if public ip is changed. """
        if stored_external_ip != self.external_ip:
            print(f"[green]NOTICE: External IP address has changed. {stored_external_ip} => {self.external_ip}[/green]")
            return True

    def is_private_ip_changed(self, stored_internal_ip):
        """ Check if private ip is changed. """
        if stored_internal_ip != self.internal_ip:
            print(f"[green]NOTICE: Internal IP address has changed. {stored_internal_ip} => {self.internal_ip}[/green]")
            return True


class RootCA(object):
    """ RootCA Certificate Storage Object """

    def __init__(self):
        # check if root CA ip setting is exist.
        if not path.isfile(f"{SETTING_DIR}/{ROOT_CA}"):
            print("Root-CA ip address setting is not found. Please set the ip address of the root CA.")
            with open(path.join(SETTING_DIR, ROOT_CA), 'w+') as file:
                self.IP_ADDRESS = input("Root-CA IP Address: ")
                file.write(self.IP_ADDRESS)
        else:
            with open(path.join(SETTING_DIR, ROOT_CA), 'r', encoding='utf-8') as file:
                self.IP_ADDRESS = file.read().strip()

        # get root CA certificate
        print("Getting root CA certificate...")
        cert = self.get_root_ca_crt()
        print("Root CA certificate is received.\n", cert)
        self.__CA_CRT__ = crypto.load_certificate(FILETYPE_PEM, cert.encode('utf-8'))

    def get_root_ca_crt(self, port=443) -> str:
        """ Get the root CA certificate from CertServer. """
        from socket import error, timeout
        try:
            return ssl.get_server_certificate((self.IP_ADDRESS, port))
        except (error, timeout) as err:
            print(f"No connection: {err}")
            sys.exit(1)

    def check_issuer(self, crt: crypto.X509) -> bool:
        """ Check if the issuer of the certificate is same as the root CA. """
        # Start with a simple test. If the issuer is not same as the root CA, return False.
        if crt.get_issuer() != self.__CA_CRT__.get_subject():
            return False

        # If the issuer is same as the root CA, check the signature.
        # If the signature is not same, return False.
        #issuer = crt
        #return issuer.digest(SHA256) == self.__CA_CRT__.digest(SHA256)

    def get_root_ca_ip_address(self):
        """ Get the IP address of the root CA. """
        return self.__CA_CRT__.get_subject().CN


class ServerCert(object):
    """ BridgeServer Keypair Storage Object """

    def __init__(self):
        # check if certificate is exist.
        if not path.isfile(CERT_FILE):
            print(f"Certificate files not found. You must init(generate a certificate) first.")
            sys.exit(1)

        import requests
        import json


        HTTPS = "https"
        HTTP = "http"
        CERT_SERVER_PROTOCOL = HTTPS
        if CERT_SERVER_PROTOCOL == HTTPS:
            session = requests.Session()
            session.verify = "cert/rootCA.crt"
        else:
            session = requests
        CERT_SERVER_ADDR = '127.0.0.1'
        CERT_SERVER_PORT = ""  # ":5000"

        UNIT_TYPE = "pos"

        # ***** An error may occur in later times. *****
        # get a passphrase and key by an expedient way; waitress checks only part of the argv.
        #
        # check if redirection flag is set.
        if [i for i, arg in enumerate(sys.argv) if '--po=' in arg]:  # if --po= is in argv => redirect.
            __PASSPHRASE__ = input()
            __CA_ENCRYPTED_KEY__ = ""
            while True:
                try:
                    __CA_ENCRYPTED_KEY__ += input() + '\n'
                except EOFError:
                    break
            print("Passphrase entered by redirection.")
            print("Certificate Key entered by redirection.")
        elif OS == "Windows" and path.isfile(f"{CERT_DIR}/{PASS_FILE}"):  # if passphrase file is exist (windows only).
            with open(f"{CERT_DIR}/{PASS_FILE}", 'r', encoding='utf-8') as pass_file, \
                    open(f"{CERT_DIR}/{KEY_FILE}", 'r', encoding='utf-8') as ca_key_file:
                __PASSPHRASE__ = pass_file.read().replace('\n', '').replace('\r', '')
                __CA_ENCRYPTED_KEY__ = ca_key_file.read()
        else:  # formal input.
            __PASSPHRASE__ = getpass("Enter passphrase: ")
            __CA_ENCRYPTED_KEY__ = getpass("Enter certificate key: ") + '\n'
            while True:
                try:
                    # since some errors were found when I used getpass, I replace them with input.
                    # this is just a countermeasure that I added just in case, so please use redirection if possible.
                    __CA_ENCRYPTED_KEY__ += input() + '\n'
                except KeyboardInterrupt:
                    break

        self.__CA_KEY__ = crypto.load_privatekey(
            FILETYPE_PEM, __CA_ENCRYPTED_KEY__, passphrase=__PASSPHRASE__.encode('utf-8'))
        with open(path.join(CERT_DIR, CERT_FILE), 'r', encoding='utf-8') as ca_crt_file:
            self.__CA_CRT__ = crypto.load_certificate(FILETYPE_PEM, ca_crt_file.read().encode('utf-8'))

    def update_certificate(self):
        respond = session.get(f"{CERT_SERVER_PROTOCOL}://{CERT_SERVER_ADDR}{CERT_SERVER_PORT}")

        if not respond.status_code == 200:
            print(respond.text, flush=True)
            raise Exception("Couldn't connect with the certificate server.")
        else:
            print(respond.content.decode(), flush=True)

        private_ip = get_private_ip_address()

        if private_ip == 'error':
            exit(1)

        print(f"\n\nRequesting certificate for PosServer......", flush=True)
        cert_req_response = request_certificate(private_ip)
        print(cert_req_response.text, flush=True)
        parse_cert_file(cert_req_response)

        print(f"\n\nRequesting certificate for BridgeServer......", flush=True)
        UNIT_TYPE = "bridge"
        cert_req_response = request_certificate("")
        print(cert_req_response.text, flush=True)
        parse_cert_file(cert_req_response)

    def request_certificate(client_private_ip: str) -> requests.Response:
        """ Request a certificate from the certificate server(CS). """
        if UNIT_TYPE == "pos":
            personal_json = json.dumps({'ip': client_private_ip})
            headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
            return session.post(
                f"{CERT_SERVER_PROTOCOL}://{CERT_SERVER_ADDR}{CERT_SERVER_PORT}/cert_request/{UNIT_TYPE}",
                data=personal_json, headers=headers)
        elif UNIT_TYPE == "bridge":
            return session.post(f"{CERT_SERVER_PROTOCOL}://{CERT_SERVER_ADDR}{CERT_SERVER_PORT}/cert_request/{UNIT_TYPE}")

    def parse_cert_file(response: requests.Response):
        """ Parse the certificate file from the response.
        """
        content_json = response.content
        content_dict = json.loads(content_json)
        cert_file = content_dict['crt']
        key_file = content_dict['key']

        if not path.isdir("cert"):
            mkdir("cert")

        with open(f"cert/{UNIT_TYPE}.crt", 'w+') as crt, open(f"cert/{UNIT_TYPE}.key", 'w+') as key:
            crt.write(cert_file)
            key.write(key_file)


if OS == "Windows":
    # Windows only
    # https://stackoverflow.com/questions/1894967/how-to-request-administrator-access-inside-a-batch-file
    ELEVATION_CMD = """@echo off

:: BatchGotAdmin
:-------------------------------------
REM  --> Check for permissions
    IF "%PROCESSOR_ARCHITECTURE%" EQU "amd64" (
>nul 2>&1 "%SYSTEMROOT%\SysWOW64\cacls.exe" "%SYSTEMROOT%\SysWOW64\config\system"
) ELSE (
>nul 2>&1 "%SYSTEMROOT%\system32\cacls.exe" "%SYSTEMROOT%\system32\config\system"
)

REM --> If error flag set, we do not have admin.
if '%errorlevel%' NEQ '0' (
    echo Requesting administrative privileges...
    goto UACPrompt
) else ( goto gotAdmin )

:UACPrompt
    echo Set UAC = CreateObject^("Shell.Application"^) > "%temp%\getadmin.vbs"
    set params= %*
    echo UAC.ShellExecute "cmd.exe", "/c ""%~s0"" %params:"=""%", "", "runas", 1 >> "%temp%\getadmin.vbs"

    "%temp%\getadmin.vbs"
    del "%temp%\getadmin.vbs"
    exit /B

:gotAdmin
    pushd "%CD%"
    CD /D "%~dp0"
:--------------------------------------


"""
