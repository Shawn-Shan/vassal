from scp import SCPClient
import threading
from binascii import hexlify
import getpass
import os
import socket
import sys
import hashlib
from cryptography.fernet import Fernet
from paramiko.py3compat import input
import paramiko
import pickle


class SSH(object):
    def __init__(self, server, username, password=None, pkey_path=None, pkey_password=None):
        self.ssh = paramiko.SSHClient()
        self.ssh.load_system_host_keys()
        self.server = server

        self.username = username
        self.password = password
        self.pkey = self.load_key(pkey_path, pkey_password)
        self.port = 22
        if self.server.find(":") >= 0:
            self.server, portstr = self.server.split(":")
            self.port = int(portstr)

    def load_key(self, pkey_path, pkey_password):
        if pkey_path is not None:
            try:
                pkey = paramiko.RSAKey.from_private_key_file(pkey_path)
                return pkey
            except paramiko.ssh_exception.PasswordRequiredException:
                if pkey_password is None:
                    raise Exception("Public Private key file is encrypted: please add pkey_password to decrypt in SSH")
                try:
                    pkey = paramiko.RSAKey.from_private_key_file(pkey_path, password=pkey_password)
                except paramiko.ssh_exception.SSHException:
                    raise Exception("Wrong password for Public Private key file")
                return pkey
        return None

    def _input_auth(self):
        try:
            self.ssh.connect(hostname=self.server, username=self.username, pkey=self.pkey, password=self.password,
                             port=self.port)
            t = self.ssh.get_transport()
            chan = t.open_session()
            chan.get_pty()
            chan.invoke_shell()
            return t, chan
        except paramiko.ssh_exception.AuthenticationException:
            return None

    def run_exec(self, cmd, stderr=False):
        (stdin, stdout, stderr_out) = self.ssh.exec_command(cmd)
        if stderr:
            return stdout.read().decode(), stderr_out.read().decode()
        else:
            return stdout.read().decode()

    def _writeall(self, sock):
        while True:
            data = sock.recv(256)
            if not data:
                sys.stdout.write("\r\n*** EOF ***\r\n\r\n")
                sys.stdout.flush()
                break
            sys.stdout.write(data.decode())
            sys.stdout.flush()

    def run(self, cmds):
        self.authenticate()
        for i in range(len(cmds)):
            if not cmds[i].endswith("\n"):
                cmds[i] += "\n"
        cmds.append("exit\n")
        chan = self.chan
        sys.stdout.write("Line-buffered terminal emulation. Press F6 or ^Z to send EOF.\r\n\r\n")
        writer = threading.Thread(target=self._writeall, args=(chan,))
        writer.start()
        try:
            for i in cmds:
                chan.send(i)
        except (EOFError, KeyboardInterrupt):
            pass

    def _progress(self, filename, size, sent):
        sys.stdout.write("%s\'s progress: %.2f%%   \r" % (filename, float(sent) / float(size) * 100))

    def _load_auth(self, cred_fname):
        credentials = pickle.load(open(cred_fname, 'rb'))
        key = credentials['key']
        cipher_suite = Fernet(key)
        password = cipher_suite.decrypt(credentials['password'])
        mode = credentials['mode']
        keypass = credentials['keypass']

        return mode, password.decode(), keypass

    def _save_auth(self, cred_fname, mode, password="", keypass=""):
        if not os.path.exists("mapping"):
            os.mkdir("mapping")
        credentials = {}
        key = Fernet.generate_key()
        credentials['key'] = key
        cipher_suite = Fernet(key)
        credentials['password'] = cipher_suite.encrypt(password.encode())
        credentials['mode'] = mode
        credentials['keypass'] = keypass
        pickle.dump(credentials, open(cred_fname, 'wb'))

    def _rsa(self, t, username, path=None, password=None):
        default_path = os.path.join(os.environ["HOME"], ".ssh", "id_rsa")
        if path is None:
            path = input("RSA key [%s]: " % default_path)
        if len(path) == 0:
            path = default_path
        try:
            key = paramiko.RSAKey.from_private_key_file(path)
        except paramiko.PasswordRequiredException:
            if password is None:
                password = getpass.getpass("RSA key password: ")
            key = paramiko.RSAKey.from_private_key_file(path, password)
        t.auth_publickey(username, key)
        return password, path

    def _dss(self, t, username, path=None, password=None):
        default_path = os.path.join(os.environ["HOME"], ".ssh", "id_dsa")
        if path is None:
            path = input("DSS key [%s]: " % default_path)
        if len(path) == 0:
            path = default_path
        try:
            key = paramiko.DSSKey.from_private_key_file(path)
        except paramiko.PasswordRequiredException:
            if password is None:
                password = getpass.getpass("DSS key password: ")

            key = paramiko.DSSKey.from_private_key_file(path, password)
        t.auth_publickey(username, key)
        return password, path

    def _manual_auth(self, t, username, hostname, mode, password, keypass):
        default_auth = "p"
        path = None
        if mode is None:
            mode = input("%s: Auth by (p)assword, (r)sa key, or (d)ss key? [%s] " % (hostname, default_auth))
        if len(mode) == 0:
            mode = default_auth

        if mode == "r":
            password, path = self._rsa(t, username=username, path=keypass, password=password)
        elif mode == "d":
            password, path = self._dss(t, username=username, path=keypass, password=password)
        else:
            if password is None:
                password = getpass.getpass("Password for %s@%s: " % (username, hostname))
            t.auth_password(username, password)
        return mode, password, path

    def _agent_auth(self, transport, username):
        """
        Attempt to authenticate to the given transport using any of the private
        keys available from an SSH agent.
        """

        agent = paramiko.Agent()
        agent_keys = agent.get_keys()
        if len(agent_keys) == 0:
            return

        for key in agent_keys:
            print("Trying ssh-agent key %s" % hexlify(key.get_fingerprint()))
            try:
                transport.auth_publickey(username, key)
                print("... success!")
                return
            except paramiko.SSHException:
                print("... nope.")

    def _compute_key_path(self, server, username):
        m = hashlib.md5()
        m.update(server.encode())
        m.update(username.encode())
        md5sum = str(m.hexdigest())
        key_path = "mapping/{}.plk".format(md5sum)
        return key_path

    def _socket_server(self, hostname):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((hostname, self.port))
        except Exception as e:
            print("*** Connect failed: " + str(e))
            sys.exit(1)
        return sock

    def scp_upload(self, file, remote_path="", recursive=False):
        self.authenticate()
        scp_client = SCPClient(self.transport, progress=self._progress)
        if remote_path != "":
            scp_client.put(file, recursive=recursive, remote_path=remote_path)
        else:
            scp_client.put(file, recursive=recursive)
        scp_client.close()

    def scp_download(self, file, local_path="", recursive=False):
        self.authenticate()
        scp_client = SCPClient(self.transport, progress=self._progress)
        scp_client.get(file, recursive=recursive, local_path=local_path)
        scp_client.close()

    def authenticate(self, force=False, save_cred=True):
        try:
            chan_t = self._input_auth()
            if chan_t is not None:
                self.transport, self.chan = chan_t
                return
        except:
            pass

        key_path = self._compute_key_path(self.server, self.username)

        if not force and os.path.exists(key_path):
            mode, password, keypass = self._load_auth(key_path)
        else:
            mode, password, keypass = None, None, None

        sock = self._socket_server(self.server)
        try:
            t = paramiko.Transport(sock)
            try:
                t.start_client()
            except paramiko.SSHException:
                print("*** SSH negotiation failed.")
                sys.exit(1)
            try:
                keys = paramiko.util.load_host_keys(os.path.expanduser("~/.ssh/known_hosts"))
            except IOError:
                try:
                    keys = paramiko.util.load_host_keys(os.path.expanduser("~/ssh/known_hosts"))
                except IOError:
                    print("*** Unable to open host keys file")
                    keys = {}

            # check server's host key -- this is important.
            key = t.get_remote_server_key()
            if self.server not in keys:
                print("*** WARNING: Unknown host key!")
            elif key.get_name() not in keys[self.server]:
                print("*** WARNING: Unknown host key!")
            elif keys[self.server][key.get_name()] != key:
                print("*** WARNING: Host key has changed!!!")
                sys.exit(1)
            else:
                print("*** Host key OK.")
            # get username

            self._agent_auth(t, self.username)
            if not t.is_authenticated():
                mode, password, path = self._manual_auth(t, self.username, self.server, mode, password, keypass)
                if save_cred:
                    self._save_auth(cred_fname=key_path, mode=mode, password=password, keypass=path)
            if not t.is_authenticated():
                print("*** Authentication failed. :(")
                t.close()
                sys.exit(1)

            chan = t.open_session()
            chan.get_pty()
            chan.invoke_shell()
            self.chan = chan
            self.transport = t

        except Exception as e:
            print("*** Caught exception: " + str(e.__class__) + ": " + str(e))
            try:
                t.close()
            except:
                pass
            sys.exit(1)