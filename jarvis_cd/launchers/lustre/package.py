from jarvis_cd.echo_node import EchoNode
from jarvis_cd.exec_node import ExecNode
from jarvis_cd.hostfile import Hostfile
from jarvis_cd.launcher import Launcher, LauncherConfig
import os
import socket

from jarvis_cd.scp_node import SCPNode
from jarvis_cd.sleep_node import SleepNode
from jarvis_cd.ssh_node import SSHNode

class Lustre(Launcher):
    def __init__(self, config_path=None, args=None):
        super().__init__('lustre', config_path, args)

    def _ProcessConfig(self):
        self.ssh_port = int(self.config['BASIC']['SSH_PORT'])
        self.ssh_user = self.config['BASIC']['SSH_USER']
        self.oss_hosts = Hostfile().LoadHostfile(self.config['OBJECT_STORAGE_SERVERS']['HOSTFILE'])
        self.client_hosts = Hostfile().LoadHostfile(self.config['CLIENT']['HOSTFILE'])
        self.num_ost_per_node = int(self.config['OBJECT_STORAGE_SERVERS']['NUM_OST_PER_NODE'])

    def SetNumHosts(self, num_oss_hosts, num_client_hosts):
        self.oss_hosts.SelectHosts(num_oss_hosts)
        self.client_hosts.SelectHosts(num_client_hosts)
        return

    def _DefineClean(self):
        nodes = []
        #Remove Lustre Management Server
        rm_mgt_cmd = f"rm -rf {self.config['MANAGEMENT_SERVER']['MOUNT_POINT']}"
        nodes.append(SSHNode("rm_mgt",
                             self.config['MANAGEMENT_SERVER']['HOST'],
                             rm_mgt_cmd,
                             username=self.ssh_user, port=self.ssh_port, print_output=True, sudo=True))

        # Remove Lustre Metatadata Server (MDT)
        rm_mdt_cmd = f"rm -rf {self.config['METADATA_SERVER']['MOUNT_POINT']}"
        nodes.append(SSHNode(
            "make_mdt",
            self.config['METADATA_SERVER']['HOST'],
            rm_mdt_cmd,
            username=self.ssh_user, port=self.ssh_port, print_output=True, sudo=True))

        # Remove Lustre Object Storage Server (OSS) and Targets (OSTs)
        for host in self.oss_hosts:
            rm_ost_cmds = []
            for i in range(self.num_ost_per_node):
                ost_dir = f"{self.config['OBJECT_STORAGE_SERVERS']['MOUNT_POINT_BASE']}{i}"
                rm_ost_cmds.append(f"rm -rf {ost_dir}")
            rm_ost_cmd = ';'.join(rm_ost_cmds)
            nodes.append(SSHNode("rm_ost",
                                 host,
                                 rm_ost_cmd,
                                 username=self.ssh_user, port=self.ssh_port, print_output=True, sudo=True))

        # Remove the Lustre PFS on the clients
        rm_client_cmd = f"rm -rf {self.config['CLIENT']['MOUNT_POINT']}"
        nodes.append(SSHNode("mount_client",
                             self.client_hosts,
                             rm_client_cmd,
                             username=self.ssh_user, port=self.ssh_port, print_output=True, sudo=True))
        return nodes

    def _DefineStatus(self):
        nodes = []

        return nodes

    def _DefineStop(self):
        nodes = []

        # Unmount the Lustre PFS on the clients
        unmount_client_cmd = f"umount {self.config['CLIENT']['MOUNT_POINT']}"
        nodes.append(SSHNode("unmount_client",
                             self.client_hosts,
                             unmount_client_cmd,
                             username=self.ssh_user, port=self.ssh_port, print_output=True, sudo=True))

        # Unmount Lustre Object Storage Server (OSS) and Targets (OSTs)
        index = 1
        for host in self.oss_hosts:
            unmount_ost_cmd = []
            for i in range(self.num_ost_per_node):
                ost_dir = f"{self.config['OBJECT_STORAGE_SERVERS']['MOUNT_POINT_BASE']}{i}"
                unmount_ost_cmd.append(f"umount {ost_dir}")
                index += 1
            unmount_ost_cmd = ';'.join(unmount_ost_cmd)
            nodes.append(SSHNode("unmount_ost",
                                 host,
                                 unmount_ost_cmd,
                                 username=self.ssh_user, port=self.ssh_port, print_output=True, sudo=True))

        # Unmount Lustre Metatadata Server (MDT)
        unmount_mdt_cmd = f"umount {self.config['METADATA_SERVER']['MOUNT_POINT']}"
        nodes.append(SSHNode(
            "unmount_mdt",
            self.config['METADATA_SERVER']['HOST'],
            unmount_mdt_cmd,
            username=self.ssh_user, port=self.ssh_port, print_output=True, sudo=True))


        # Unmount Lustre Management Server (MGS)
        unmount_mgt_cmd = f"umount {self.config['MANAGEMENT_SERVER']['MOUNT_POINT']}"
        nodes.append(SSHNode("unmount_mgt",
                             self.config['MANAGEMENT_SERVER']['HOST'],
                             unmount_mgt_cmd,
                             username=self.ssh_user, port=self.ssh_port, print_output=True, sudo=True))
        return nodes

    def _DefineInit(self):
        nodes = []

        # Make and mount Lustre Management Server (MGS)
        make_mgt_cmd = f"mkfs.lustre --reformat --mgs {self.config['MANAGEMENT_SERVER']['STORAGE']}"
        mkdir_mgt_cmd = f"mkdir -p {self.config['MANAGEMENT_SERVER']['MOUNT_POINT']}"
        nodes.append(SSHNode("make_mgt",
                             self.config['MANAGEMENT_SERVER']['HOST'],
                             f'{make_mgt_cmd};{mkdir_mgt_cmd}',
                             username=self.ssh_user, port=self.ssh_port, print_output=True, sudo=True))

        # Make and mount Lustre Metatadata Server (MDT)
        make_mdt_cmd = (
            f"mkfs.lustre "
            f"--fsname={self.config['BASIC']['FSNAME']} "
            f"--reformat "
            f"--mgsnode={self.config['MANAGEMENT_SERVER']['HOST']}@tcp "
            f"--mdt "
            f"--index=0 {self.config['METADATA_SERVER']['STORAGE']}"
        )
        mkdir_mdt_cmd = f"mkdir -p {self.config['METADATA_SERVER']['MOUNT_POINT']}"
        nodes.append(SSHNode(
            "make_mdt",
            self.config['METADATA_SERVER']['HOST'],
            f'{make_mdt_cmd};{mkdir_mdt_cmd}',
            username=self.ssh_user, port=self.ssh_port, print_output=True, sudo=True))

        # Make and mount Lustre Object Storage Server (OSS) and Targets (OSTs)
        index = 1
        for host in self.oss_hosts:
            make_ost_cmd = []
            mkdir_ost_cmd = []
            for i in range(self.num_ost_per_node):
                ost_id = f"OST{i}"
                ost_dev = f"{self.config['OBJECT_STORAGE_SERVERS'][ost_id]}"
                ost_dir = f"{self.config['OBJECT_STORAGE_SERVERS']['MOUNT_POINT_BASE']}{i}"
                make_ost_cmd.append((
                    f"mkfs.lustre --ost "
                    f"--reformat "
                    f"--fsname={self.config['BASIC']['FSNAME']} "
                    f"--mgsnode={self.config['MANAGEMENT_SERVER']['HOST']}@tcp "
                    f"--index={index} {ost_dev}"
                ))
                mkdir_ost_cmd.append(f"mkdir -p {ost_dir}")
                index += 1
            make_ost_cmd = ';'.join(make_ost_cmd)
            mkdir_ost_cmd = ';'.join(mkdir_ost_cmd)
            nodes.append(SSHNode("mount_ost",
                                 host,
                                 f'{make_ost_cmd};{mkdir_ost_cmd}',
                                 username=self.ssh_user, port=self.ssh_port, print_output=True, sudo=True))

        # Mount the Lustre PFS on the clients
        mkdir_client_cmd = f"mkdir -p {self.config['CLIENT']['MOUNT_POINT']}"
        nodes.append(SSHNode("mount_client",
                             self.client_hosts,
                             mkdir_client_cmd,
                             username=self.ssh_user, port=self.ssh_port, print_output=True, sudo=True))
        return nodes

    def _DefineStart(self):
        nodes = []

        #Make and mount Lustre Management Server (MGS)
        mount_mgt_cmd = f"mount -t lustre {self.config['MANAGEMENT_SERVER']['STORAGE']} {self.config['MANAGEMENT_SERVER']['MOUNT_POINT']}"
        nodes.append(SSHNode("make_mgt",
                             self.config['MANAGEMENT_SERVER']['HOST'],
                             mount_mgt_cmd,
                             username=self.ssh_user, port=self.ssh_port, print_output=True, sudo=True))

        #Make and mount Lustre Metatadata Server (MDT)
        mount_mdt_cmd = f"mount -t lustre {self.config['METADATA_SERVER']['STORAGE']} {self.config['METADATA_SERVER']['MOUNT_POINT']}"
        nodes.append(SSHNode(
            "make_mdt",
            self.config['METADATA_SERVER']['HOST'],
            mount_mdt_cmd,
            username=self.ssh_user, port=self.ssh_port, print_output=True, sudo=True))

        #Make and mount Lustre Object Storage Server (OSS) and Targets (OSTs)
        index = 1
        for host in self.oss_hosts:
            mount_ost_cmd = []
            for i in range(self.num_ost_per_node):
                ost_id = f"OST{i}"
                ost_dev = f"{self.config['OBJECT_STORAGE_SERVERS'][ost_id]}"
                ost_dir = f"{self.config['OBJECT_STORAGE_SERVERS']['MOUNT_POINT_BASE']}{i}"
                mount_ost_cmd.append(f"mount -t lustre {ost_dev} {ost_dir}")
                index += 1
            mount_ost_cmd = ';'.join(mount_ost_cmd)
            nodes.append(SSHNode("mount_ost",
                                 host,
                                 mount_ost_cmd,
                                 username=self.ssh_user, port=self.ssh_port, print_output=True, sudo=True))

        #Mount the Lustre PFS on the clients
        mount_client_cmd = f"mount -t lustre {self.config['MANAGEMENT_SERVER']['HOST']}@tcp:/{self.config['BASIC']['FSNAME']} {self.config['CLIENT']['MOUNT_POINT']}"
        nodes.append(SSHNode("mount_client",
                             self.client_hosts,
                             mount_client_cmd,
                             username=self.ssh_user, port=self.ssh_port, print_output=True, sudo=True))
        return nodes




