# NX9k POAP & NSO middleware

Simple flask application that will react upon get requests (copy commands) from a NX device performing POAP. 
It will then wait for 10 minutes (for the device restart) to let NSO know that it should be onboarded

## Flow

1. Device restarts without configuration
2. Starts POAP process
3. Gets DHCP address
4. Downloads poap.py script
5. At the end, the poap.py script makes a get request using the copy command with its serial number
6. The middleware starts a new thread that will wait 10 minutes before sending requests to NSO

## Requisites
* See Pipfile.lock for python libraries
* NSO 5.3 or greater with NX driver

## Installation
1. Clone this repo on any OS with python 3 installed
2. Install dependencies (you can use pipenv - As long as you have flask and requests should be ok)
3. Add env variables with NSO credentials. For example

```bash
export NSO_URL=[http|https]://<NSO_IP>:<NSO_PORT>/restconf 
export NSO_USER=admin
export NSO_PASSWORD=supersecret
```

4. Start flask application
```bash
python run.py
```
5. Make sure to map the correct values for your infrastructure in the poap.py file (lines 20-25 and 142)
## Contacts
* Santiago Flores Kanter (sfloresk@cisco.com)