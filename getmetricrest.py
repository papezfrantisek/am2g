import requests
from prometheus_client import start_http_server, Gauge
import time

# Prometheus metriky
RESOURCE_GROUP_COUNT = Gauge('azure_resource_group_count', 'Count of Azure resource groups')

# Konfigurace pro Azure
TENANT_ID = '661f8f5f-1e7d-4d4d-a886-1d2661c4ddf8'
CLIENT_ID = '318e5469-4fbd-4f2a-b5b2-6f86ac5a41c4'
CLIENT_SECRET = '-PR8Q~xN5ruH.nC1J-_sBBIxuj8nuoNq6qnDxaNk'
RESOURCE = 'https://management.azure.com/'
SUBSCRIPTION_ID = '135c4851-f605-41ab-b698-2a474bc0a94a'

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
    # Startuje Prometheus HTTP server na portu 8000
    start_http_server(8000)
    while True:
        update_metrics()
        time.sleep(60)  # Aktualizuje metriky každou minutu

