#!/bin/env python3
#md5sum="d86563a52cc420a3eb16f50a02a98531"
"""
If any changes are made to this script, please run the below command
in bash shell to update the above md5sum. This is used for integrity check.
f=poap_nexus_script.py ; cat $f | sed '/^#md5sum/d' > $f.md5 ; sed -i \
"s/^#md5sum=.*/#md5sum=\"$(md5sum $f.md5 | sed 's/ .*//')\"/" $f
"""

import os
import re
import shutil
import signal
import sys
import syslog
import errno
from cli import *
import time

options = {
   "config_url": "http://192.168.1.1/configs/lwr04-nxosv.cisco.com",
   "system_url": "http://192.168.1.1/images/nxos.9.3.5.bin",
   "target_system_image": "nxos.9.3.5.bin",
   "system_destination": "bootflash:/nxos.9.3.5.bin",
}


def get_version():
    """
    Gets the image version of the switch from CLI.
    """
    cli_output = cli("show version")
    result = re.search(r'NXOS.*version\s*(.*)\n', cli_output)
    if result is not None:
        return result.group(1)
    poap_log("Unable to get switch version")

def target_system_image_is_currently_running():
    """
    Checks if the system image that we would try to download is the one that's
    currently running.
    """
    version = get_version()
    image_parts = [part for part in re.split("[\.()]", version) if part]
    image_parts.insert(0, "nxos")
    image_parts.append("bin")
    running_image = ".".join(image_parts)
    poap_log("Running: '%s'" % running_image)
    poap_log("Target:  '%s'" % options["target_system_image"])
    return running_image == options["target_system_image"]

def poap_log(info):
    """
    Log the trace into console and poap_script log file in bootflash
    Args:
        file_hdl: poap_script log bootflash file handle
        info: The information that needs to be logged.
    """
    global log_hdl, syslog_prefix

    # Don't syslog passwords
    parts = re.split("\s+", info.strip())
    for (index, part) in enumerate(parts):
        # blank out the password after the password keyword (terminal password *****, etc.)
        if part == "password" and len(parts) >= index+2:
            parts[index+1] = "<removed>"

    # Recombine for syslogging
    info = " ".join(parts)

    # We could potentially get a traceback (and trigger this) before
    # we have called init_globals. Make sure we can still log successfully
    try:
        info = "%s - %s" % (syslog_prefix, info)
    except NameError:
        info = " - %s" % info

    syslog.syslog(9, info)
    if "log_hdl" in globals() and log_hdl is not None:
        log_hdl.write("\n")
        log_hdl.write(info)
        log_hdl.flush()

def setup_logging():
    """
    Configures the log file this script uses
    """
    global log_hdl

    poap_script_log = "/bootflash/poap_%s_script.log" % os.environ['POAP_PID']
    log_hdl = open(poap_script_log, "w+")

    poap_log("Logfile name: %s" % poap_script_log)

def sigterm_handler(signum, stack):
    """
    A signal handler for the SIGTERM signal. Cleans up and exits
    """
    poap_log("INFO: SIGTERM Handler")
    exit(1)

def sig_handler_no_exit(signum, stack):
    """
    A signal handler for the SIGTERM signal. Does not exit
    """
    poap_log("INFO: SIGTERM Handler while configuring boot variables")


def main():
    signal.signal(signal.SIGTERM, sigterm_handler)

    # Configure the logging for the POAP process
    setup_logging()

    if not target_system_image_is_currently_running():
        poap_log("Copying system image")

        try:
            poap_log("Executing: terminal dont-ask ; copy " + options["system_url"] + " " + options["system_destination"] + " vrf " + os.environ['POAP_VRF'])
            poap_log(cli("terminal dont-ask ; copy " + options["system_url"] + " " + options["system_destination"] + " vrf " + os.environ['POAP_VRF']))
        except Exception as e:
            poap_log("System copy failed: %s" % str(e))
            raise

        signal.signal(signal.SIGTERM, sig_handler_no_exit)
        # install system image
        poap_log("Installing system image")
        poap_log("Executing: config terminal ; boot nxos %s" % options["system_destination"])
        poap_log(cli("config terminal ; boot nxos %s" % options["system_destination"]))
        # Copy run start so it is booted with this image
        poap_log('terminal dont-ask ; copy running-config startup-config')
        poap_log(cli('terminal dont-ask ; copy running-config startup-config'))
    else:
        poap_log("Target image is current - boot update not needed ")

    # Applying config
    poap_log("Applying config for next restart")
    poap_log(cli('terminal dont-ask ; copy ' + options["config_url"] + ' tmp_cfg' + " vrf " + os.environ['POAP_VRF']))
    poap_log(cli('terminal dont-ask ; copy tmp_cfg scheduled-config'))
    # Let know middleware that we will be ready on next reboot
    serial = cli('show hardware | inc "Serial number"').splitlines()[0].replace("Serial number is","").strip()
    poap_log(cli('terminal dont-ask ; copy http://192.168.1.1:5000/provision/' + serial + ' nso_dummy' + " vrf " + os.environ['POAP_VRF']))
    poap_log("All set")

    
    log_hdl.close()
    exit(0)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        exc_type, exc_value, exc_tb = sys.exc_info()
        poap_log("Exception: {0} {1}".format(exc_type, exc_value))
        while exc_tb is not None:
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            poap_log("Stack - File: {0} Line: {1}"
                     .format(fname, exc_tb.tb_lineno))
            exc_tb = exc_tb.tb_next
        exit(1)
