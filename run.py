from flask import Flask
import time

app = Flask(__name__)
import requests
import os
from threading import Thread


@app.route('/health')
def health():
    """ Use to test the web server is running."""
    # TODO: Return json response
    return 'ok'


@app.route("/provision/<serial>")
def provision(serial):
    """ Starts the provisioning of a device for a given serial number """
    print(f"Got provisioned request from {serial}")

    # TODO: Serial number validation can be done here.
    #  NSO could also do that check, mapping a serial to onboarding parameters

    # We hardcoded the same IP here as an example, but will be different for each serial number
    ip_address = "192.168.0.1"
    deployer = Deployer(serial, ip_address)
    deployer.setName(f"Provisioning process for {serial}")
    deployer.start()
    # TODO: return a json payload
    return "Started"


class Deployer(Thread):
    """ Simple class to allow each deployment to have its own thread """

    def __init__(self, serial, ip_address):
        Thread.__init__(self)
        self.serial = serial
        self.ip_address = ip_address

    def run(self):
        """ Entry point - wait 10 minutes before adding it to NSO"""
        print(f"Waiting for device to be reachable")
        # TODO: A more strict reachable validation can be done instead of just waiting 10 minutes for the
        #  device to come up
        time.sleep(10 * 60)  # 10 minutes
        print(f"Making API call to NSO")
        url = f"{os.getenv('NSO_URL')}/data/"
        headers = {
            'Content-Type': 'application/yang-data+json',
            'Accept': 'application/yang-data+json'
        }
        # Add Device
        payload = {
            "tailf-ncs:devices": {
                "device": [
                    {
                        "name": self.serial,
                        "address": self.ip_address,
                        "authgroup": "nso-onboard-default",  # Authentication group should be present on NSO
                        "device-type": {
                            "cli": {
                                # This could be changed to support multi-vendor
                                "ned-id": "cisco-nx-cli-5.16:cisco-nx-cli-5.16",
                                "protocol": "ssh"
                            }
                        },
                        "state": {
                            "admin-state": "unlocked"
                        }
                    }
                ]
            }
        }

        response = requests.request("PATH", url, headers=headers,
                                    auth=(os.getenv("NSO_USER"), os.getenv("NSO_PASSWORD")),
                                    json=payload)
        if not response.ok:
            print(f"Error: {response.text}")
            return
        # Fetch keys
        url = f"{os.getenv('NSO_URL')}/data/operations/devices/device={self.serial}/ssh/fetch-host-keys"
        response = requests.request("POST", url, headers=headers,
                                    auth=(os.getenv("NSO_USER"), os.getenv("NSO_PASSWORD")))
        if not response.ok:
            print(f"Error: {response.text}")
            return
        # Sync-from
        url = f"{os.getenv('NSO_URL')}/data/operations/devices/device={self.serial}/sync-from"
        response = requests.request("POST", url, headers=headers,
                                    auth=(os.getenv("NSO_USER"), os.getenv("NSO_PASSWORD")))
        if not response.ok:
            print(f"Error: {response.text}")
        else:
            print(f"Device {self.serial} has been onboarded into NSO")


if __name__ == '__main__':
    app.run(host="0.0.0.0")
