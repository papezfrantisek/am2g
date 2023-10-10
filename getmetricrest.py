import requests
from prometheus_client import start_http_server, Gauge
import time
import os


# Prometheus metrics
RESOURCE_GROUP_COUNT = Gauge('azure_resource_group_count', 'Count of Azure resource groups')

# Konfiguration for Azure
TENANT_ID = os.environ["TENANT_ID"]
CLIENT_ID = os.environ["CLIENT_ID"]
CLIENT_SECRET = os.environ["CLIENT_SECRET"]
SUBSCRIPTION_ID = os.environ["SUBSCRIPTION_ID"]
RESOURCE = 'https://management.azure.com/'

def get_token():
    token_url = f'https://login.microsoftonline.com/{TENANT_ID}/oauth2/token'
    token_data = {
        'grant_type': 'client_credentials',
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'resource': RESOURCE
    }
    token_r = requests.post(token_url, data=token_data)
    return token_r.json().get("access_token")

def get_resource_group_count(token):
    headers = {
        'Authorization': 'Bearer ' + token,
        'Content-Type': 'application/json'
    }
    endpoint_url = f'https://management.azure.com/subscriptions/{SUBSCRIPTION_ID}/resourceGroups?api-version=2020-06-01'
    response = requests.get(endpoint_url, headers=headers)
    return len(response.json().get("value", []))

def update_metrics():
    token = get_token()
    count = get_resource_group_count(token)
    RESOURCE_GROUP_COUNT.set(count)

if __name__ == '__main__':
    # Starting Prometheus HTTP server on port 8000
    start_http_server(8000)
    while True:
        update_metrics()
        time.sleep(60)  # reads metrics every 1 minute



