from prometheus_client import Gauge, start_http_server
import time, json, re, requests, os
from datetime import datetime
import concurrent.futures, threading


# Configuration for Azure
TENANT_ID = os.environ["TENANT_ID"]
CLIENT_ID = os.environ["CLIENT_ID"]
CLIENT_SECRET = os.environ["CLIENT_SECRET"]
SUBSCRIPTION_ID = os.environ["SUBSCRIPTION_ID"]
DATA_DIRECTORY = os.environ["HOME"]+"/data/"
RESOURCE = 'https://management.azure.com/'
RESOURCE_GROUP = ''
RESOURCE_NAME = ''
token = ''
# local config 
CFGFILENAME = 'actualdata.json'
resourceGroups = {}
resources = {}
metric_def_urls = []
metric_urls = []
version_regex = re.compile('\d\d\d\d-\d\d-\d\d-?\w?\w?\w?\w?\w?\w?\w?')
resources_metrics_definitions = {}
metrics_for_resource = {}
METRIC_DEFINITION = ''
new_list = {}

if DATA_DIRECTORY is None:
	DATA_DIRECTORY = "/"

print("your data will be saved in "+DATA_DIRECTORY)
	  


def write_actual_status(CFGFILENAME, var):
    print(var)
    with open(DATA_DIRECTORY+CFGFILENAME, 'a') as out:
        out.write(json.dumps(var) + '\n')
    out.close()

def read_last_saved_status(file=CFGFILENAME):
    with open(DATA_DIRECTORY+file, 'r') as f:
        data = json.load(f)
    f.close()
    return data

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
    for i in range(0, len(resourceGroups)-1):
        if 'resources' in resourceGroups[i].keys():
            if len(resourceGroups[i]['resources']) > 0:
                for k in range(0, len(resourceGroups[i]['resources'])-1):
                    if "type" in resourceGroups[i]['resources'][k].keys():
                        typeofresource = resourceGroups[i]['resources'][k]['type']
                        resources[resourceGroups[i]['resources'][k]['name']]['resourcetype'] = typeofresource
                        testurl = f"https://management.azure.com/subscriptions/{SUBSCRIPTION_ID}/resourceGroups/{resourceGroups[i]['name']}/providers/{resourceGroups[i]['resources'][k]['type']}/{resourceGroups[i]['resources'][k]['name']}/providers/microsoft.insights/metricDefinitions?api-version=2222-22-22"
                        message = get_azure_data(testurl, token).json()['error']['message']
                        versions = re.findall(version_regex, message)
                        #print(versions)
                        if len(versions) > 0:
                            url = f"https://management.azure.com/subscriptions/{SUBSCRIPTION_ID}/resourceGroups/{resourceGroups[i]['name']}/providers/{resourceGroups[i]['resources'][k]['type']}/{resourceGroups[i]['resources'][k]['name']}/providers/microsoft.insights/metricDefinitions?api-version={versions[1].replace(',', '')}"
                            resources[resourceGroups[i]['resources'][k]['name']]['resurl'] = url
                            definition = get_azure_data(url, token).json()
                            if len(definition.keys()) > 0:
                                resources_metrics_definitions[resourceGroups[i]['resources'][k]['name']] = {'definition': definition, 'resourceGroup': resourceGroups[i]['name'], 'type': typeofresource}
                        else:
                            print("Error: no version gathered from dummy request")
                    else:
                        print("fck no type key")
        elif 'type' in resourceGroups[i].keys():
            url = f"https://management.azure.com/subscriptions/{SUBSCRIPTION_ID}/resourceGroups/{resourceGroups[i]['name']}/providers/{resourceGroups[i]['type']}/{resourceGroups[i]['name']}/providers/microsoft.insights/metricDefinitions?api-version=2018-11-01"
            print(url)
        else:
            print("no resources")
    return resources_metrics_definitions

def get_metrics_resources():
    gathered_data = {}
    try:
        for i in resources_metrics_definitions:
            if 'value' in resources_metrics_definitions[i]['definition'].keys():
                if len(resources_metrics_definitions[i]['definition']['value']) > 0:
                    metrics = []
                    for k in range(0, len(resources_metrics_definitions[i]['definition']['value'])-1):
                        metrics+=(resources_metrics_definitions[i]['definition']['value'][k])
                    gathered_data[i] = metrics
    except SyntaxError as e:
        print(e)
    finally:
        return gathered_data

def generate_metrics(resource):
    metric_from_azure = ''
    resourcegroup = resources_metrics_definitions[resource]['resourceGroup']
    resourcetype = resources_metrics_definitions[resource]['type']
    print(resourcetype)
    for k in range(0, len(resources_metrics_definitions[resource]['definition']['value'])-1):
        metric = resources_metrics_definitions[resource]['definition']['value'][k]['name']['value']
        url = f'https://management.azure.com/subscriptions/{SUBSCRIPTION_ID}/resourceGroups/{resourcegroup}/providers/{resourcetype}/{resource}/metrics?api-version=2018-11-01'
        print(url)
        data = get_azure_data(url, token)
        if data.json()['error']['message']:
            print("error message aquired")
            versions = re.findall(version_regex, data.json()['error']['message'])
            print(versions)
            version = versions[1]
            url = f'https://management.azure.com/subscriptions/{SUBSCRIPTION_ID}/resourceGroups/{resourcegroup}/providers/{resourcetype}/{resource}/metrics?api-version={version}'
            data = get_azure_data(url, token).json().get("value", [])
        print("######")
        print(data)
        print("######")
        metric_from_azure.append(data)
    return metric_from_azure

def create_mulist(data):
    new_list = {}
    for i in data.keys():
        url = f"https://management.azure.com/subscriptions/135c4851-f605-41ab-b698-2a474bc0a94a/resourceGroups/{data[i]['resourceGroup']}/providers/{data[i]['type']}/{i}/metrics?api-version=2242-22-22"
        results = get_azure_data(url, token).json()['error']['message']
        #print(data)
        versions = re.findall(version_regex, results)
        if len(versions) > 0:
            print(versions)            
            version = versions[1]
            print(version)
        else:
            version = '2015-06-01'  
        url = f"https://management.azure.com/subscriptions/135c4851-f605-41ab-b698-2a474bc0a94a/resourceGroups/{data[i]['resourceGroup']}/providers/{data[i]['type']}/{i}/metrics?api-version={str(version)}"
        print(url)
        new_list[i] = url
        print("done!")
    return new_list

def copyFile(source, destination):
    try:
        os.stat(source)
        open(destination, 'wb').write(open(source, 'rb').read())
    except FileNotFoundError as e:
        print(f"while running copyFile function system error occured:\n{e}")

def generateurls(my_list):
    todelete = []
    results = {}
    for i in my_list.keys():
        if my_list[i]:
            try:
                get_response = get_azure_data(my_list[i], token)
                if get_response:
                    results[i] = get_response.json().get("value", [])
                else:
                    todelete.append(i)
            except SystemError as e:
            	print(e)
        else:
            print("empty list")
    for k in range(0, len(todelete)-1):
        del my_list[todelete[k]]
    write_actual_status('metrics_map.json', my_list)
    return results        

def custom_metrics_definer():
    metric_defs_generated ={}
    my_definitions = {}
    labels = []
    created_defs = []
    print(f"starting to generate  metric defs")
    for metric_definition in resources_metrics_definitions:
        #print(f"generating {resources_metrics_definitions[metric_definition]['definition']['value']}")
        if 'value' in (resources_metrics_definitions[metric_definition]['definition'].keys()):
            for k in range(0, len(resources_metrics_definitions[metric_definition]['definition']['value'])-1):
                print(f"generating {resources_metrics_definitions[metric_definition]['definition']['value'][k]['name']['value'] }")
                if resources_metrics_definitions[metric_definition]['definition']['value'][k]['name']['value']:
                    resources_metrics_definitions[metric_definition]['definition']['value'][k]['name']['value']= re.sub(r'\W+', '', resources_metrics_definitions[metric_definition]['definition']['value'][k]['name']['value'])
                    print(resources_metrics_definitions[metric_definition]['definition']['value'][k]['name']['value'])
                    my_definitions[resources_metrics_definitions[metric_definition]['definition']['value'][k]['name']['value']] = resources_metrics_definitions[metric_definition]['definition']['value'][k]
                else:
                    print("error")
    for i in my_definitions:
        if i not in created_defs:
            print(f"added new definition for metric {my_definitions[i]['name']['value']}")
            if not 'displayDescription' in my_definitions[i].keys():
                my_definitions[i]['displayDescription'] = "not specified"
            metric_defs_generated[i] = Gauge(
                my_definitions[i]['name']['value'],
                my_definitions[i]['displayDescription'],
                ['resource_name', 'unit', 'time_grain', 'resource_id', 'metric'],
            )
        created_defs.append(i)
    return metric_defs_generated

        
def collect_metrics(metricdefs):
    iteration = 1
    iteration = (iteration +1)
    mydata = []
    metric_data = {}
        # Simulate fetching metric data from your source (replace with actual data retrieval logic)
    metric_urls = my_list        # get the metric data from  azure via requests
    metrics_map = generateurls(metric_urls)
        # Iterate through the metric data and update the Prometheus metric
    while True:
        for metric_group in metrics_map.keys():
            for i in metrics_map[metric_group]:
                mydata.append(i)
            for metric in mydata:
                name = metric["name"]["value"]
                unit = metric["unit"]
                time_grain = metric["timeGrain"]
                for metric_value in metric["metricValues"]:
                    timestamp = metric_value['timestamp']
                    #print(metric_value)
                    for m in metric_value.keys():
                        #print(metric_defs_generated)
                        if m == 'timestamp':
                            timestamp = metric_value[m]
                        elif m == 'properties':
                             metric_value[m]=0#print("empty mertic")
                        else:
                            #print(f"{name} metrika {m} ma hodnotu {metric_value[m]}")
                            metr = float(metric_value[m])
                            name = re.sub(r'\W+', '', name)
                            metric_defs_generated[name].labels(
                                resource_name=metric_group,
                                unit=unit,
                                time_grain=time_grain,
                                timestamp=timestamp,
                                resource_id=metric["resourceId"],
                                metric=m
                            ).set(metr)

        # Sleep for a while before collecting metrics again (adjust as needed)
        time.sleep(30)
        print(f"running {iteration} cycle from start")  # Collect metrics every minute


if os.environ["AM2G_DEBUG"] == 'Y' or os.environ["AM2G_DEBUG"] == None:
    token = get_token()
    resourceGroups = read_last_saved_status(CFGFILENAME)
    resources_metrics_definitions = read_last_saved_status('resources_resources_metrics_definitions.json')
    for i in metrics_for_resource.keys():
        testurl = generate_metrics(i)
    my_list = create_mulist(resources_metrics_definitions)
    results = {}
    results = generateurls(my_list)
    write_actual_status('result.json', results)
    
    if os.stat(DATA_DIRECTORY+'urls.json'):
        copyFile(DATA_DIRECTORY+'urls.json', DATA_DIRECTORY+'urls.json.backup')
        write_actual_status('urls.json', new_list)
    else:
        write_actual_status('urls.json', new_list)
    for key in results:
        print(f"gathered metrics for resource: {key}\n{results[key].keys()}")
    
    #print(results)    
else:
    token = get_token()
    print("###### getting resourceGroups #######\n ")
    resourceGroups = get_resource_groups(token)  # gather resourcegroups and create dictionary .
    print("###### Getting resources #######\n gathering info from:"+str(len(resourceGroups))+" resource groups")
    assign_ressources() # create resources dicctionary 
    write_actual_status(CFGFILENAME, resourceGroups)
    resources = generate_resources_dictionary()
    resources_metrics_definitions = generate_metric_urls()
    write_actual_status('resources.json', resources)
    write_actual_status('resources_resources_metrics_definitions.json', resources_metrics_definitions)
    metrics_for_resource = get_metrics_resources()
    write_actual_status('metrics_map.json', metrics_for_resource)
    my_list = create_mulist(resources_metrics_definitions)
    results = generateurls(my_list)
    write_actual_status('urls.json', my_list)
    write_actual_status('result.json', results)
    write_actual_status('urls.json', new_list)
    # Start the HTTP server to expose the metrics
    #with open('/Users/papezf01/data/resources_resources_metrics_definitions.json', 'r') as f:
    #    resources_metrics_definitions = json.load(f)
    #with open('/Users/papezf01/data/metric_names', 'r') as f:
    #    metric_names = f.readlines()
    token_lock = threading.Lock()
    shared_token = get_token()
    start_http_server(8000)
    metric_defs_generated = custom_metrics_definer()
    # Collect and update metrics
    collect_metrics(metric_defs_generated)
    

    
    
    


