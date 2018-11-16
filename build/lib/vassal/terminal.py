import subprocess
from vassal.ssh import SSH
import os


class ArgsSCP(object):
    def __init__(self):
        self.r = False
        self.server = None
        self.username = False
        self.put = False
        self.remote_path = ""
        self.pkey = None
        self.file = ""

    def check_fields(self):
        for i in [self.server, self.username, self.remote_path, self.file]:
            if i == "":
                raise Exception("Scp syntax problem")


class Terminal(object):
    def __init__(self, commands, ssh_password=None, pkey_path=None, pkey_password=None):
        self.commands = commands
        self.ssh_password = ssh_password
        self.pkey_path = pkey_path
        self.pkey_password = pkey_password
        self.cwd = os.path.dirname(os.path.realpath(__file__))

    def truncate_command(self):
        cmd_truncks = []
        cur_truck = self.init_trunk()
        for cmd in self.commands:
            cmd = cmd.strip()
            if cmd.startswith("cd"):
                self.update_cwd(cmd)
                cur_truck.commands.append(cmd)

            elif cmd.startswith("ssh"):
                cmd_truncks.append(cur_truck)
                cur_truck = self.init_trunk(cmd)

            elif cmd.startswith("scp"):
                cmd_truncks.append(cur_truck)
                cur_truck = self.init_trunk(cmd)
                cmd_truncks.append(cur_truck)
                cur_truck = self.init_trunk()

            elif cmd.startswith("exit"):
                cur_truck.commands.append(cmd)
                cmd_truncks.append(cur_truck)
                cur_truck = self.init_trunk()
            else:
                cur_truck.commands.append(cmd)

        cmd_truncks.append(cur_truck)
        cmd_truncks = [trunk for trunk in cmd_truncks if trunk.commands]
        return cmd_truncks

    def init_trunk(self, first_cmd=None):
        if first_cmd is None:
            commands = []
        else:
            commands = [first_cmd]
        cur_trunk = TerminalTrunk(commands, self.cwd, ssh_password=self.ssh_password, pkey_path=self.pkey_path,
                                  pkey_password=self.pkey_password)
        if first_cmd is not None:
            if first_cmd.startswith("ssh"):
                cur_trunk.ssh = True

            elif first_cmd.startswith("scp"):
                cur_trunk.scp = True
        return cur_trunk

    def update_cwd(self, cd_command):
        path = cd_command.split(" ")[-1]
        self.cwd = os.path.join(self.cwd, path)

    def run(self):
        all_trunks = self.truncate_command()
        for trunk in all_trunks:
            trunk.run()


class TerminalTrunk(object):
    def __init__(self, commands, cwd, ssh_password=None, pkey_path=None, pkey_password=None, ssh=False, scp=False):
        self.commands = commands
        self.ssh_password = ssh_password
        self.pkey_path = pkey_path
        self.pkey_password = pkey_password
        self.cwd = cwd
        self.ssh = ssh
        self.scp = scp

    def _run_local(self):
        change_cwd = "cd " + self.cwd
        commands = ";".join([change_cwd] + self.commands)
        process = subprocess.Popen(commands, stdout=subprocess.PIPE, shell=True)
        proc_stdout = process.communicate()[0].strip()
        return proc_stdout.decode()

    def _parse_ssh(self, cmd):
        cmd_seg = cmd.split()
        serverATuser = [c for c in cmd_seg if "@" in c]
        assert len(serverATuser) == 1
        serverATuser = serverATuser[0]
        username = serverATuser.split("@")[0]
        server = serverATuser.split("@")[-1]
        return username, server

    def _parse_scp(self, cmd):
        cmd_seg = cmd.split()
        args = ArgsSCP()
        i = 0
        while i < len(cmd_seg):
            if cmd_seg[i] == "-r":
                args.r = True
            if cmd_seg[i] == "-i":
                args.pkey = cmd_seg[i + 1]
                i += 1
            if "@" in cmd_seg[i]:
                args.username = cmd_seg[i].split("@")[0]
                server_path = cmd_seg[i].split("@")[1]
                assert ":" in server_path
                args.server = server_path.split(":")[0]
                args.remote_path = server_path.split(":")[1]
            i += 1

        if "@" in cmd_seg[-1]:
            args.put = True
            args.file = cmd_seg[-2]
        elif "@" in cmd_seg[-2]:
            args.file = cmd_seg[-1]
        else:
            raise Exception("Scp syntax problem")
        args.file = os.path.join(self.cwd, args.file)
        return args

    def _init_ssh(self):
        username, server = self._parse_ssh(self.commands[0])
        client = SSH(server, username, password=self.ssh_password, pkey_path=self.pkey_path,
                     pkey_password=self.pkey_password)
        return client

    def _run_ssh(self):
        client = self._init_ssh()
        results = client.run(self.commands[1:])
        print(results)
        return results

    def _run_scp(self):
        assert len(self.commands) == 1
        args = self._parse_scp(self.commands[0])
        args.check_fields()
        client = SSH(args.server, args.username, password=self.ssh_password, pkey_path=args.pkey,
                     pkey_password=self.pkey_password)  # TODO support different keys
        if args.put:
            client.scp_upload(args.file, remote_path=args.remote_path, recursive=args.r)
        else:
            client.scp_download(args.remote_path, recursive=args.r, local_path=args.file)

    def run(self):
        if self.commands[0].startswith("ssh"):
            self._run_ssh()
        elif self.commands[0].startswith("scp"):
            self._run_scp()
        else:
            self._run_local()