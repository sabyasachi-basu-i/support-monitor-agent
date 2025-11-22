import requests
import json

NEGOTIATE_URL = (
    "https://us01governor.futuredge.com/api/myhub/negotiate"
    "?Machine=WebClient&Key=random&negotiateVersion=1"
)

def negotiate_connection(access_token):
    headers = {
        "Authorization": access_token,
        "Accept": "*/*",
        "Content-Type": "text/plain;charset=UTF-8",
        "X-Requested-With": "XMLHttpRequest",
        "x-signalr-user-agent": "Microsoft SignalR/5.0 (5.0.17; Python)"
    }

    res = requests.post(NEGOTIATE_URL, headers=headers, data="")
    res.raise_for_status()
    data = res.json()

    print("✔ Negotiate Success")
    return data["connectionToken"]

LOGIN_URL = "https://us01governor.futuredge.com/api/api/login"

def get_token():
    login_body = {
        "loginType": "RiYSAGovernor",
        "loginuser": "admin",
        "pass": "FutureEdge@123",
        "tenant": "default"
    }

    res = requests.post(LOGIN_URL, json=login_body)
    res.raise_for_status()
    data = res.json()

    print("✔ Login Successful")
    return "Bearer " + data["token"]