import os
import re
import subprocess
import time

import displaypi.wifidisplay as _wfdconstants


def _create_config_dir(confdir='~/.displaypi'):
    """Prepare config directory ~/.displaypi

    TODO: move to a central point; directory is for all parts of the framework

    :param confdir: Full path of the confdir, defaults to ~/.displaypi
    :raises OSError: if directory is not createable. This is a fatal situation and exits the service
    """
    expanded_confdir = os.path.expanduser(confdir)
    os.makedirs(expanded_confdir, mode=0o700, exist_ok=True)

    return expanded_confdir


def _cmd(params):
    """Execute a wpa_cli specific wpa call and check for errors
    :param params: an array of command parameters as for subprocess.run
    """
    result = subprocess.run(params,
                            check=False, capture_output=True, text=True)
    if result.returncode != 0:
        raise P2pCmdError("Failed cmd '" + " ".join(params) +
                          "'", details=result.stdout)
    else:
        return result.stdout


def _wpacmd(params):
    """Execute a shell call and check for returncode only
    :param params: an array of command parameters as for subprocess.run
    """
    result = subprocess.run(params,
                            check=False, capture_output=True, text=True)
    if result.returncode != 0 or not result.stdout.endswith('OK\n'):
        raise P2pCmdError("Failed cmd '" + " ".join(params) +
                          "'", details=result.stdout)
    else:
        return result.stdout


def _find_p2pdev():
    """Find a suitable wifi device to establish p2p connection on

    :return: name of the p2p device to use
    :rtype: string
    :raises P2pInterfaceNotFoundError: no device supporting p2p found

    :example:
    :seealso:
    """
    try:
        output = _wpacmd(['wpa_cli', 'p2p_find', 'type=progressive'])
        matching_interface = re.search(
            "Selected interface '(.*)'", output, flags=re.MULTILINE)
        return matching_interface.group(1)
    except P2pCmdError as cmdEx:
        raise P2pInterfaceNotFoundError(
            "No progressive p2p device found.", details=cmdEx.message)

def _find_p2pinterface(p2pdev):
    """Find the persistent wlan p2p interface to operate on

    :return: name of the p2p interface
    :rtype: string
    :raises P2pInterfaceNotFoundError: trouble finding the persistent interface

    :example:
    :seealso:
    """
    try:
        output = _cmd(['wpa_cli', "-i"+p2pdev, 'interface'])
        matching_interface = re.search(
            "p2p-wl.*", output, flags=re.MULTILINE)
        return matching_interface.group(0)
    except P2pCmdError as cmdEx:
        raise P2pInterfaceNotFoundError(
            "Failed to detect the p2p interface.", details=cmdEx.message)


class P2pError(Exception):
    """General form of wifi p2p exceptions"""

    def __init__(self, message, details=""):
        self.message = message
        self.details = details


class P2pCmdError(P2pError):
    """Exception raised when not suitable P2p interface is found."""
    pass


class P2pInterfaceNotFoundError(P2pError):
    """Exception raised when not suitable P2p interface is found."""
    pass


class P2pSetupError(P2pError):
    pass


class P2pWifi:

    def __init__(self):
        pass

    def _assign_ip_to_interface(self, gateway_ip):
        """Assign an IP address to an interface 

        NOTE: this is the only step where you need sudoer rights! No way around found yet.

        :param gateway_ip: the ip for the interface; must fit to the dhcp range for the clients
        """
        # if already set, you have to flush
        _cmd(['sudo', 'ip', 'address', 'flush', 'dev', self.p2pinterface])  
        _cmd(['sudo', 'ip', 'address', 'add', gateway_ip, 'dev', self.p2pinterface])


    def _run_dhcp_server(self, min_ip, max_ip, subnet_mask="255.255.255.0", lease_time=60):
        """Configure a mini dhcp server (udhcpd taken from busybox) as subprocess.

        TODO: udhcpd creates and ICMP socket. Thus, it needs sudo rights. May find another
        way later to avoid running udhcpd as root

        Save config in ~/.displaypi/udhcpd.conf 
        :param min_ip: minimal ip of ip pool
        :param max_ip: max ip of ip pool
        :param subnet_mask: The subnet mask for the pool. Defaults to /24 CIDR
        :param int lease_time: the time in minutes a lease stays valid. Default 60 minutes
        """
        conf_filename = self.confdir + "/udhcp_" + self.p2pinterface + ".conf"
        pid_filename = self.confdir + "/udhcp_" + self.p2pinterface + ".pid"
        
        lease_filename = self.confdir + "/udhcp_" + self.p2pinterface + ".leases"
        _cmd(['touch', lease_filename])

        with open(conf_filename, 'w+') as fhandle:
            fhandle.write("start " + min_ip + "\n")
            fhandle.write("end	" + max_ip + "\n")
            fhandle.write("interface " + self.p2pinterface + "\n")
            fhandle.write("option subnet " + subnet_mask + "\n")
            fhandle.write("option lease " + str(lease_time)+ "\n")
            fhandle.write("lease_file " + lease_filename + "\n")
            fhandle.write("pidfile " + pid_filename + "\n")
            fhandle.flush()
        fhandle.close()

        self.udhcpd_handle = subprocess.Popen(
            ['sudo', 'busybox', "udhcpd", "-f", "-S", conf_filename], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        _cmd(["rm", "-f", conf_filename])

    def close(self):
        """ Backward cleanup or closing of system ressources """

        # stop subproccess mini dhcp server
        if self.udhcpd_handle is not None:
            self.udhcpd_handle.terminate()
            try:
                self.udhcpd_handle.wait(timeout=10)
            except subprocess.TimeoutExpired:
                # worst case: kill after timeout, keeps system unclean
                self.udhcpd_handle.kill()

        # remove persistent p2p interface (to start clean on next boot if shutdown properly)
        if self.p2pinterface is not None:
            # TODO: check whether this makes sense
            _wpacmd(["wpa_cli", "-i"+self.p2pdev,
                     "p2p_group_remove", self.p2pinterface])

    def open(self, wfdname):
        """Open and set up a wifi p2p connection as wifi display sink of the given name
        :param string wfdname: Name of the wifi display p2p sink, shown as name of the
                               display in display discovery.
        :raises P2pInterfaceNotFoundError: no device supporting p2p found
        :raises P2pSetupError: p2p connection setup for wifi display specific parameters failed
        """
        self.confdir = _create_config_dir()

        self.p2pdev = _find_p2pdev()
        try:
            self.p2pinterface = _find_p2pinterface(self.p2pdev)
        except:
            # configure interface for wifi display
            try:
                _wpacmd(["wpa_cli", "-i"+self.p2pdev,
                         "set", "device_name", wfdname])
                _wpacmd(["wpa_cli", "-i"+self.p2pdev, "set",
                         "device_type", "7-0050F204-1"])
                _wpacmd(["wpa_cli", "-i"+self.p2pdev,
                         "set", "p2p_go_ht40", "1"])
                _wpacmd(["wpa_cli", "-i"+self.p2pdev,
                         "wfd_subelem_set", "0", "00060151022a012c"])
                _wpacmd(["wpa_cli", "-i"+self.p2pdev,
                         "wfd_subelem_set", "1", "0006000000000000"])
                _wpacmd(["wpa_cli", "-i"+self.p2pdev,
                         "wfd_subelem_set", "6", "000700000000000000"])
                _wpacmd(["wpa_cli", "-i"+self.p2pdev,
                         "p2p_group_add", "persistent", "ht40"])
            except P2pCmdError as cmdEx:
                raise P2pSetupError(
                    "Unable to establish p2p wifi for " + self.p2pdev, details=cmdEx.message)

            self.p2pinterface = _find_p2pinterface(self.p2pdev)

        self._assign_ip_to_interface(_wfdconstants.GATEWAY_IP)

        # set a WPS pin; not anybody who detects the display should be able to connect
        # the WPS pin must be known
        try:
            # TODO: may roll PIN with each restart and show in subtitle (at start)
            _cmd(["wpa_cli", "-i"+self.p2pinterface,
                        "wps_pin", "any", _wfdconstants.WPS_PIN])
        except P2pCmdError as cmdEx:
            raise P2pSetupError(
                "Unable to set WPS pin for " + self.p2pinterface, details=cmdEx.message)

        # used a DHCP server to assign IPs to multiple partners
        self._run_dhcp_server(
            min_ip=_wfdconstants.DHCP_START_IP, max_ip=_wfdconstants.DHCP_END_IP)
