import os
import requests
import json
import re


# Configuration for Azure
TENANT_ID = os.environ["TENANT_ID"]
CLIENT_ID = os.environ["CLIENT_ID"]
CLIENT_SECRET = os.environ["CLIENT_SECRET"]
SUBSCRIPTION_ID = os.environ["SUBSCRIPTION_ID"]
RESOURCE = 'https://management.azure.com/'
RESOURCE_GROUP = ''
RESOURCE_NAME = ''
token = ''
# local config 
CFGFILENAME = 'data/actualdata.json'
resourceGroups = {}
resources = {}
metric_def_urls = []
metric_urls = []
version_regex = r'\d\d\d\d-\d\d-\d\d-?[a-z][A-Z]?'



def write_actual_status(CFGFILENAME, var):
    with open(CFGFILENAME, 'a') as out:
        out.write(json.dumps(var))
# Prometheus metrics

def read_last_saved_status(file=CFGFILENAME):
    with open(file) as f:
        resourceGroups = json.load(f)





resourcegroups_endpoint_url = f'https://management.azure.com/subscriptions/{SUBSCRIPTION_ID}/resourceGroups?api-version=2020-06-01'
resources_endpoint_url = f'https://management.azure.com/subscriptions/{SUBSCRIPTION_ID}/resourceGroups/{RESOURCE_GROUP}?api-version=2020-06-01'
metrics_endpoint_url = f'https://management.azure.com/subscriptions/{SUBSCRIPTION_ID}/resourceGroups/{RESOURCE_GROUP}/providers/Microsoft.Web/sites/{RESOURCE_NAME}/metrics?api-version=2018-11-01'

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

def get_azure_data(req_url, token):
    headers = {
        'Authorization': 'Bearer ' + token,
        'Content-Type': 'application/json'
    }
    endpoint_url = req_url
    response = requests.get(endpoint_url, headers=headers)
    return response
    

def get_resource_groups(token):
    headers = {
        'Authorization': 'Bearer ' + str(token),
        'Content-Type': 'application/json'
    }
    endpoint_url = f'https://management.azure.com/subscriptions/{SUBSCRIPTION_ID}/resourceGroups?api-version=2020-06-01'
    response = requests.get(endpoint_url, headers=headers)
    return response.json().get("value", [])

def get_resources(token, RESOURCE_GROUP):
    headers = {
        'Authorization': 'Bearer ' + token,
        'Content-Type': 'application/json'
    }
    endpoint_url = f'https://management.azure.com/subscriptions/{SUBSCRIPTION_ID}/resourceGroups/{RESOURCE_GROUP}/resources?api-version=2020-06-01'
    response = requests.get(endpoint_url, headers=headers)
    return response.json().get("value", [])

def get_metrics(token, RESOURCE_GROUP, RESOURCE_NAME):
    headers = {
        'Authorization': 'Bearer ' + token,
        'Content-Type': 'application/json'
    }
    endpoint_url = f'https://management.azure.com/subscriptions/{SUBSCRIPTION_ID}/resourceGroups?api-version=2020-06-01'
    response = requests.get(endpoint_url, headers=headers)
    return response.json().get("value", [])



def assign_ressources():    #add resources deffinition in the dictionary.
    for i in range(0, len(resourceGroups)-1):
        resources_data = {}
        #print(resourceGroups[i]['name'])
        resources_data = get_resources(token, resourceGroups[i]['name'])
        #print(resources_data)
        resourceGroups[i]['resources'] = resources_data
        #print("*****")

def generate_resources_dictionary():
    resources = {}
    for i in range(0, len(resourceGroups)-1):
        if ('resources' in resourceGroups[i].keys()) and (len(resourceGroups[i]['resources']) > 0):
            for k in range(0, len(resourceGroups[i]['resources'])-1):
                resources[resourceGroups[i]['resources'][k]['name']] = {'data': resourceGroups[i]['resources'][k], 'resourceGroup': resourceGroups[i]['name']}
    return resources

def generate_metric_urls():
    token = get_token()
    for i in range(0, len(resourceGroups)-1):
        if len(resourceGroups[i]['resources']) > 0:
            if 'resources' in resourceGroups[i].keys():
                for k in range(0, len(resourceGroups[i]['resources'])-1):
                    if "type" in resourceGroups[i]['resources'][k].keys():
                        print(resourceGroups[i]['resources'][k]['type'])
                        testurl = f"https://management.azure.com/subscriptions/{SUBSCRIPTION_ID}/resourceGroups/{resourceGroups[i]['name']}/providers/{resourceGroups[i]['resources'][k]['type']}/{resourceGroups[i]['resources'][k]['name']}/providers/microsoft.insights/metricDefinitions?api-version=2222-22-22"
                        message = get_azure_data(testurl, token).json()['error']['message']
                        versions = re.findall(r'\d\d\d\d\-\d\d-\d\d', message)
                        versions+= re.findall(r'\d\d\d\d\-\d\d-\d\d-?[a-z]+', message)
                        print(versions)
                        if len(versions) > 0:
                            url = f"https://management.azure.com/subscriptions/{SUBSCRIPTION_ID}/resourceGroups/{resourceGroups[i]['name']}/providers/{resourceGroups[i]['resources'][k]['type']}/{resourceGroups[i]['resources'][k]['name']}/providers/microsoft.insights/metricDefinitions?api-version={versions[1]}"
                            resources[resourceGroups[i]['resources'][k]['name']]['resurl'] = url
                        else:
                            print("Error: no version gathered from dummy request")
                    else:
                        print("fck")
            elif 'type' in resourceGroups[i].keys():
                url = f"https://management.azure.com/subscriptions/{SUBSCRIPTION_ID}/resourceGroups/{resourceGroups[i]['name']}/providers/{resourceGroups[i]['type']}/{resourceGroups[i]['name']}/providers/microsoft.insights/metricDefinitions?api-version=2018-11-01"
                print(url)
            else:
                print("no resources")

token = get_token()
print("###### getting resourceGroups #######\n ")
resourceGroups = get_resource_groups(token)  # gather resourcegroups and create dictionary .
print("###### Getting resources #######\n gathering info from:"+str(len(resourceGroups))+" resource groups")
assign_ressources() # create resources dicctionary 
write_actual_status(CFGFILENAME, resourceGroups)
resources = generate_resources_dictionary()
generate_metric_urls()
write_actual_status('data/resources.json', resources)














