"""
This module provides classes and methods to inject the HermesMpiio interceptor.
HermesMpiio intercepts the MPI I/O calls used by a native MPI program and
routes it to Hermes.
"""
from jarvis_cd.basic.pkg import Interceptor
from jarvis_util import *


class HermesMpiio(Interceptor):
    """
    This class provides methods to inject the HermesMpiio interceptor.
    """
    def _init(self):
        """
        Initialize paths
        """
        pass

    def _configure_menu(self):
        """
        Create a CLI menu for the configurator method.
        For thorough documentation of these parameters, view:
        https://github.com/scs-lab/jarvis-util/wiki/3.-Argument-Parsing

        :return: List(dict)
        """
        return []

    def configure(self, **kwargs):
        """
        Converts the Jarvis configuration to application-specific configuration.
        E.g., OrangeFS produces an orangefs.xml file.

        :param kwargs: Configuration parameters for this pkg.
        :return: None
        """
        self.update_config(kwargs, rebuild=False)
        self.config['HERMES_MPIIO'] = self.find_library('hermes_mpiio')
        if self.config['HERMES_MPIIO'] is None:
            raise Exception('Could not find hermes_mpiio')
        print(f'Found libhermes_mpiio.so at {self.config["HERMES_MPIIO"]}')

    def modify_env(self):
        """
        Modify the jarvis environment.

        :return: None
        """
        self.prepend_path('LD_PRELOAD', self.config['HERMES_MPIIO'])