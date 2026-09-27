#!/usr/bin/env python3
"""
GIGABYTE G292-Z20 Fan Control Helper
MegaRAC SP-X Web API Client for fanprofile configuration and activation.
"""

import argparse
import json
import ssl
import sys
import urllib.parse
import urllib.request

def get_ssl_context():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx

class G292BMCClient:
    def __init__(self, host, user, password):
        self.host = host
        self.user = user
        self.password = password
        self.ctx = get_ssl_context()
        self.cookie = None
        self.csrf = None

    def login(self):
        url = f"https://{self.host}/api/session"
        data = urllib.parse.urlencode({"username": self.user, "password": self.password}).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "X-Requested-With": "XMLHttpRequest",
            },
        )
        with urllib.request.urlopen(req, context=self.ctx, timeout=15) as resp:
            raw_cookies = resp.headers.get("Set-Cookie")
            if raw_cookies:
                self.cookie = raw_cookies.split(";")[0]
            body = json.loads(resp.read().decode("utf-8"))
            self.csrf = body.get("CSRFToken") or resp.headers.get("X-CSRFTOKEN")
            if not self.csrf:
                raise RuntimeError("Failed to retrieve CSRF token from BMC login")
            print(f"[+] Login successful to {self.host}")

    def request(self, path, method="GET", body=None):
        url = f"https://{self.host}{path}"
        headers = {
            "X-CSRFTOKEN": self.csrf,
            "Cookie": self.cookie,
            "X-Requested-With": "XMLHttpRequest",
        }
        data = None
        if body is not None:
            headers["Content-Type"] = "application/json"
            data = json.dumps(body).encode("utf-8")

        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        with urllib.request.urlopen(req, context=self.ctx, timeout=15) as resp:
            content = resp.read().decode("utf-8")
            return json.loads(content) if content else {}

    def get_mode(self):
        return self.request("/api/settings/fanprofile/mode")

    def set_mode(self, mode_name):
        return self.request("/api/settings/fanprofile/mode", method="POST", body={"strMode": mode_name})

    def deploy_quiet_max(self):
        profile = {
            "strVersion": "1.00",
            "strName": "quiet_max",
            "arrPolicy": [
                {
                    "arrFanSensor": [160, 161, 164, 165, 166, 167],
                    "arrSensor": [28, 29, 30, 31],
                    "arrRef": [74, 82, 88],
                    "arrDuty": [5, 60, 100],
                    "iInitDuty": 5,
                    "iPolicyType": 2,
                    "iSensorCode": 1,
                    "iInSDR": 1,
                    "iHysteresis": 0,
                    "iPCIEDeviceEnable": 0,
                    "iCpuTdp": 0,
                    "iAmbientSensor": 0,
                    "iAmbientSensorTemp": 0,
                    "arrHexVendorID": [],
                    "arrHexDeviceID": [],
                },
                {
                    "arrFanSensor": [162, 163],
                    "arrSensor": [1],
                    "arrRef": [76, 84, 90],
                    "arrDuty": [5, 60, 100],
                    "iInitDuty": 5,
                    "iPolicyType": 2,
                    "iSensorCode": 1,
                    "iInSDR": 1,
                    "iHysteresis": 0,
                    "iPCIEDeviceEnable": 0,
                    "iCpuTdp": 0,
                    "iAmbientSensor": 0,
                    "iAmbientSensorTemp": 0,
                    "arrHexVendorID": [],
                    "arrHexDeviceID": [],
                },
            ],
        }
        try:
            print("[*] Creating quiet_max profile...")
            self.request("/api/settings/fanprofile/collection", method="POST", body=profile)
        except Exception as e:
            print(f"[*] Profile create returned: {e} (might already exist, trying update)")
            try:
                self.request("/api/settings/fanprofile/collection/quiet_max", method="PUT", body=profile)
            except Exception as e2:
                print(f"[*] Profile update returned: {e2}")

        print("[*] Activating quiet_max mode via POST...")
        res = self.set_mode("quiet_max")
        print(f"[+] Result: {res}")

def main():
    parser = argparse.ArgumentParser(description="Tune G292 Fan Speeds via BMC API")
    parser.add_argument("--host", default="<BMC_IP>", help="BMC IP Address")
    parser.add_argument("--user", default="admin", help="BMC Username")
    parser.add_argument("--password", required=True, help="BMC Password")
    parser.add_argument("--mode", choices=["status", "quiet_max", "default"], default="status")

    args = parser.parse_args()
    client = G292BMCClient(args.host, args.user, args.password)
    client.login()

    if args.mode == "status":
        print("[*] Current Fan Profile Mode:", client.get_mode())
    elif args.mode == "quiet_max":
        client.deploy_quiet_max()
        print("[*] Verify Mode:", client.get_mode())
    elif args.mode == "default":
        print("[*] Reverting to default mode...")
        client.set_mode("default")
        print("[*] Verify Mode:", client.get_mode())

if __name__ == "__main__":
    main()
