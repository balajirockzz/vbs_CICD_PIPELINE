import requests
import time
import json
import os
import sys
from urllib.parse import quote

WAIT_TIME = 5
MAX_RUN_COUNT = os.cpu_count()
responseResult = []
input_parm = json.loads(sys.argv[2])

client_id = input_parm["clientid"]
client_secret = input_parm["clientsecret"]
scope = input_parm["scopeurl"]
token_url = input_parm["tokenurl"]
instance_id = input_parm["instanceid"]  # <--- YOUR REAL OIC INSTANCE OCID HERE
oic_url_stub1 = "/ic/api/integration/v1/integrations/"
oic_url_stub2 = f"?integrationInstance={instance_id}"
oic_design_url = input_parm["url"]

print ("client id used :",client_id)
print ("client secret used :",client_secret)
print ("scope used :",scope)
print ("token_url used :",token_url)
print ("instance_id used :",instance_id)
print ("oic_design_url used :",oic_design_url)
print ("oic_url_stub1 used :",oic_url_stub1)
print ("oic_url_stub2 used :",oic_url_stub2)

access_token = None
expires_at = 0

headers_base = {
    'X-HTTP-Method-Override': 'PATCH',
    'Accept': 'application/json'
}

def join_url(base, *parts):
    base_stripped = base.rstrip('/')
    segs = []
    for p in parts:
        if p is None:
            continue
        p = str(p)
        if p.startswith('?'):
            segs.append(p)
        else:
            segs.append(p.strip('/'))
    path_parts = [s for s in segs if not s.startswith('?')]
    joined = base_stripped + '/' + '/'.join(path_parts) if path_parts else base_stripped
    query_parts = [s for s in segs if s.startswith('?')]
    return joined + ''.join(query_parts)

def get_token():
    global access_token, expires_at
    token_data = {
        'grant_type': 'client_credentials',
        'scope': scope
    }
    try:
        resp = requests.post(token_url, data=token_data, auth=(client_id, client_secret), timeout=30)
        resp.raise_for_status()
        tokens = resp.json()
        access_token = tokens['access_token']
        expires_in = tokens.get('expires_in', 3600)
        expires_at = time.time() + int(expires_in) - 10
        print("Obtained access token, expires in", expires_in)
    except requests.HTTPError as e:
        try:
            err = resp.json()
        except Exception:
            err = resp.text if 'resp' in locals() else str(e)
        print("Failed to obtain token:", err)
        raise
    except Exception as e:
        print("Unexpected error obtaining token:", str(e))
        raise

def ensure_token():
    if access_token is None or time.time() >= expires_at:
        get_token()

def authorized_headers():
    ensure_token()
    authorized = {'Authorization': f'Bearer {access_token}'}
    authorized.update(headers_base)
    return authorized

def act_deactivate_iar(url, integration_id, status):
    if '|' in integration_id:
        integration_id_to_use = integration_id.replace('|', '%7C')
    else:
        integration_id_to_use = integration_id
    target = join_url(url, oic_url_stub1, integration_id_to_use) + oic_url_stub2
    payload = {'status': status}
    try:
        resp = requests.post(target, headers=authorized_headers(), json=payload, timeout=60)
        try:
            body = resp.json()
        except Exception:
            body = {"non_json": resp.text}
        if 200 <= resp.status_code < 300:
            activation_status = body.get('activationStatus') or body.get('status') or ''
            if activation_status:
                if status.upper() in activation_status.upper() or activation_status.upper().endswith('_SUCCEEDED'):
                    print(f"{integration_id}: {status}!")
                    return "Success"
            print(f"{integration_id}: API returned {resp.status_code} and body: {body}")
            return "Success"
        else:
            title = body.get('title') if isinstance(body, dict) else None
            msg = title or body or resp.text
            print(f"{integration_id} : {msg}")
            return "Error"
    except Exception as e:
        print(f"Error calling activation API for {integration_id}: {e}")
        return "Error"

def deploy_filepath(url, method, filepath, file_source_location):
    print("base url :", url)
    print("method :", method)
    print("filepath :", filepath)
    print("file_source_location :", file_source_location)
    full_path = os.path.join(file_source_location, filepath)
    print("Full path being opened:", full_path)
    iar_import_path = "ic/api/integration/v1/integrations/archive"
    print(f"{method}ting the integrations for: {filepath}")
    archive_url = join_url(url, iar_import_path) + oic_url_stub2
    try:
        with open(full_path, 'rb') as f:
            files = {
                'file': f,
                'type': (None, 'application/octet-stream'),
            }
            o_iar_deploy = requests.request(
                method.upper(), archive_url, headers=authorized_headers(), files=files, timeout=120
            )
    except FileNotFoundError:
        raise Exception(f"ERROR: IAR file not found at path: {full_path}")
    except Exception as e:
        raise
    print("HTTP status:", o_iar_deploy.status_code)
    if str(o_iar_deploy.status_code).startswith("20"):
        print(f"{filepath}: DEPLOYED")
        print("Activating Integration....")
        base = os.path.splitext(filepath)[0]
        split_basename = base.split('_')
        if len(split_basename) >= 2:
            fileName = "_".join(split_basename[:-1])
            version = split_basename[-1].strip()
            if not fileName or not version or fileName.lower() == 'null' or version.lower() == 'null':
                raise Exception(f"ERROR: integration instanceId or version parsed as empty/'null' from {filepath}.")
            integration_id = f"{fileName}%7C{version}"
        else:
            integration_id = base.replace('|', '%7C')
        act_result = act_deactivate_iar(url, integration_id, "ACTIVATED")
        if act_result == "Success":
            print(f"{filepath}: ACTIVATED")
            raise Exception(f"SUCCESS: {filepath} ACTIVATED and DEPLOYED")
        elif act_result == "Error":
            print(f"{filepath}: got error while ACTIVATING")
            raise Exception(f"ERROR: {filepath} got error while ACTIVATING")
    else:
        try:
            o_iar_deploy_json = o_iar_deploy.json()
        except Exception:
            o_iar_deploy_json = {"error": f"Non-JSON response: {o_iar_deploy.text}"}
        print(o_iar_deploy_json)
        if o_iar_deploy_json.get("status") == "HTTP 500 Internal Server Error":
            raise Exception("ERROR: " + o_iar_deploy_json.get("status", "") + o_iar_deploy_json.get("title", ""))
        else:
            raise Exception("ERROR: " + str(o_iar_deploy_json))

def integrations(url, oci_filepath, file_source_location, artifact_indv_sec):
    print(f"Received Filepath: {oci_filepath}")
    print("Using OIC Environment URL:", url)
    print("Using OIC Instance OCID:", instance_id)
    print("Using OAuth client_id:", client_id)
    print("Using OAuth scope:", scope)
    import_put_post = 'put'
    artifact_type = "OIC"
    notauth_count = 0
    if 'OIC' not in artifact_indv_sec["section"]:
        artifact_indv_sec["section"].append(artifact_type)
        artifact_indv_sec["section_data"][artifact_type] = []
    artifact_indv_sec["deployment_info"]["oic_env"] = artifact_indv_sec["deployment_info"]["oic_env"].replace(
        "##oic_env##", url)
    for filepath in oci_filepath:
        print(f"###################################{filepath}###############################")
        artifact_indv_sec_data = {
            "name": filepath,
            "contains_error": "#contains_error#",
            "payload": "#payload#"
        }
        if filepath.lower().endswith(".iar"):
            try:
                result = os.path.splitext(filepath)
                split_basename = result[0].split('_')
                if len(split_basename) < 2:
                    err_msg = f"ERROR: Filename parsing failed for {filepath} (expected at least one '_' to split integration name/version)"
                    print(err_msg)
                    artifact_indv_sec_data["contains_error"] = "yes"
                    artifact_indv_sec_data["payload"] = err_msg
                    artifact_indv_sec["section_data"][artifact_type].append(artifact_indv_sec_data)
                    continue
                fileName = "_".join(split_basename[:-1])
                version = split_basename[-1].strip()
                filetype = "IAR"
                print(f"Parsed fileName: '{fileName}' | version: '{version}' for artifact: '{filepath}'")
                if not fileName or not version or fileName.lower() == 'null' or version.lower() == 'null':
                    err_msg = (
                        f"ERROR: integration instanceId or version parsed as empty/'null' from {filepath}. "
                        "Check the IAR filename convention and ensure it matches '<integrationName>_<version>.iar'"
                    )
                    print(err_msg)
                    artifact_indv_sec_data["contains_error"] = "yes"
                    artifact_indv_sec_data["payload"] = err_msg
                    artifact_indv_sec["section_data"][artifact_type].append(artifact_indv_sec_data)
                    continue
                check_id_encoded = f"{fileName}%7C{version}"
                check_url = join_url(url, oic_url_stub1, check_id_encoded) + oic_url_stub2
                print(f"Will call integration status API: {check_url}")
                headers = authorized_headers()
                print("headers", headers)
                if access_token is not None:
                    o_iar_status_resp = requests.get(check_url, headers=headers, timeout=30)
                    try:
                        o_iar_status = o_iar_status_resp.json()
                        print("OIC get response:try ", o_iar_status)
                    except Exception:
                        o_iar_status = {"error": f"Non-JSON response: {o_iar_status_resp.text}"}
                        print("OIC get response:exception ", o_iar_status)
                    print("status:Outside block ", o_iar_status)
                    if "code" in o_iar_status and o_iar_status.get("code") != fileName:
                        error_msg = (
                            f"API error ({o_iar_status.get('code')}): {o_iar_status.get('message', str(o_iar_status))}\n"
                            ">> This is usually caused by one of these:\n"
                            f"1. The integration instanceId ('{fileName}') does not exist or is not deployed in the Oracle instance you are targeting.\n"
                            "2. Your client_id/client_secret does not have access to this Oracle Integration instance (add 'IntegrationInstanceInvoker' or similar roles).\n"
                            f"3. Your OAuth scope '{scope}' is incorrect."
                        )
                        print(error_msg)
                        notauth_count += 1
                        artifact_indv_sec_data["contains_error"] = "yes"
                        artifact_indv_sec_data["payload"] = error_msg
                        artifact_indv_sec["section_data"][artifact_type].append(artifact_indv_sec_data)
                        if notauth_count >= 3:
                            print(
                                "\nFATAL: Multiple NotAuthorizedOrNotFound errors detected - check (1) integration exists, "
                                "(2) your OAuth user/credentials have correct role, (3) your scope string is valid!")
                            print("Script will not retry this artifact.")
                            continue
                    status_value = o_iar_status.get("status", None)
                    if o_iar_status.get("activationStatus"):
                        pass
                    if status_value == "ACTIVATED":
                        print("Integration Status: ACTIVATED")
                        print("Deactivating the integration...")
                        act_result = act_deactivate_iar(url, check_id_encoded, "CONFIGURED")
                        if act_result == "Success":
                            print(f"SUCCESS: {filepath} DE_ACTIVATED")
                        elif act_result == "Error":
                            print(f"{filepath}: got error while DE_ACTIVATING")
                            raise Exception(f"ERROR: {filepath} got error while DE_ACTIVATING")
                    elif status_value == "HTTP 404 Not Found":
                        print("Integration not found")
                        import_put_post = 'post'
                    elif status_value == "CONFIGURED":
                        print("Integration Status: CONFIGURED")
                        import_put_post = 'put'
                    else:
                        if status_value is None:
                            print("No 'status' in response, treating as new integration (POST).")
                            import_put_post = 'post'
                        else:
                            print(f"Integration status: {status_value} (proceeding with update/post as needed)")
                            import_put_post = 'put'
                print("Deploying Integration....")
                deploy_filepath(url, import_put_post, filepath, file_source_location)
            except Exception as e:
                print(f"{e}")
                artifact_indv_sec_data['payload'] = str(e)
                if str(e).startswith("ERROR"):
                    artifact_indv_sec_data["contains_error"] = "yes"
                elif str(e).startswith("SUCCESS"):
                    artifact_indv_sec_data["contains_error"] = "no"
            artifact_indv_sec["section_data"][artifact_type].append(artifact_indv_sec_data)

def create_json(json_file):
    obj_count = 0
    artifact_status = []
    for item in json_file["section"]:
        obj_count += len(json_file["section_data"][item])
        for value in json_file["section_data"][item]:
            if value["contains_error"] == "yes":
                artifact_status.append(1)
            elif value["contains_error"] == "no":
                artifact_status.append(0)
    json_file["deployment_info"]["status"] = json_file["deployment_info"]["status"].replace(
        "##status##", 'Contains Error' if any(artifact_status) else 'Deployment Successfully Done')
    json_file["deployment_info"]["obj_count"] = json_file["deployment_info"]["obj_count"].replace(
        "##obj_count##", str(obj_count))
    json_obj = json.dumps(json_file, indent=4)
    with open("int_dash.json", "w") as file:
        file.write(json_obj)

def read_json(json_file):
    with open(json_file, "r") as f:
        return json.load(f)

if __name__ == "__main__":
    json_file_path = sys.argv[1]
    input_parm = json.loads(sys.argv[2])
    artifact_indv_sec = read_json(os.path.join(json_file_path, "artifact_indv.json"))
    artifact_indv_sec_data = read_json(os.path.join(json_file_path, "artifact_indv_sec_data.json"))
    integrations(
        oic_design_url,
        input_parm["artifact_list"],
        input_parm["source_repo"],
        artifact_indv_sec
    )
    create_json(artifact_indv_sec)
