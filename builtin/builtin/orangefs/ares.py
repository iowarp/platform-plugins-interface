from jarvis_util import *


class OrangefsAres:
    def ares_start(self):
        # start pfs servers
        cmd = [
            f'{self.pkg_dir}/ares_bash/ares-orangefs-deploy',
            self.config['pfs_conf'],
            self.config['server_hosts_path'],
            self.config['client_hosts_path'],
            self.config['mount'],
        ]
        cmd = ' '.join(cmd)
        print(cmd)
        Exec(cmd, LocalExecInfo(env=self.env))

    def ares_stop(self):
        cmd = [
            f'{self.pkg_dir}/ares_bash/ares-orangefs-terminate',
            self.config['pfs_conf'],
            self.config['server_hosts_path'],
            self.config['client_hosts_path'],
            self.config['mount'],
        ]
        cmd = ' '.join(cmd)
        print(cmd)
        Exec(cmd, LocalExecInfo(env=self.env))
