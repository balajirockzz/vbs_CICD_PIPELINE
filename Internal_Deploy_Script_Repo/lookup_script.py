import os
import sys
import time
import json
import requests
from urllib.parse import quote

WAIT_TIME = 5
MAX_RUN_COUNT = os.cpu_count()
responseResult = []

# ----------- HARDCODED CONFIG (same style as your IAR script) -------------
client_id = "21dbb2233d2647638113fc2274a4a201"
client_secret = "idcscs-9b9bbc38-a588-4d0d-8ea0-3d44eeed5d61"
scope = "https://EB5A96156AFB4995AAD03DAEAC380550.integration.us-ashburn-1.ocp.oraclecloud.com:443urn:opc:resource:consumer::all"
token_url = "https://idcs-1f63bf89f74648cdb31c1af6dfce9fe6.identity.oraclecloud.com/oauth2/v1/token"

# Instance OCID and base design URL (same defaults as your IAR script)
instance_id = "fusion-paas-oic-dev-idzdhlnqyhdp-ia"
oic_design_url = "https://design.integration.us-ashburn-1.ocp.oraclecloud.com"
access_token = None
expires_at = 0

headers_base = {
    'X-HTTP-Method-Override': 'PATCH',
    'Accept': 'application/json'
}

# query-string used in IAR script for instance context
oic_url_stub2 = "?integrationInstance=" + instance_id
# -------------------------------------------------------------------------

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
    """Obtain OAuth client_credentials token and set globals."""
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
        print("Obtained access token, expires in {}".format(expires_in))
    except requests.HTTPError as e:
        try:
            err = resp.json()
        except Exception:
            err = resp.text if 'resp' in locals() else str(e)
        print("Failed to obtain token: {}".format(err))
        raise
    except Exception as e:
        print("Unexpected error obtaining token: {}".format(str(e)))
        raise

def ensure_token():
    if access_token is None or time.time() >= expires_at:
        get_token()

def authorized_headers():
    ensure_token()
    authorized = {'Authorization': 'Bearer {}'.format(access_token)}
    authorized.update(headers_base)
    return authorized

def deploy_lookup(url, method, filepath, file_source_location):
    """
    Upload a lookup (CSV) to the OIC lookups/archive endpoint using OAuth bearer token.
    Raises Exception("SUCCESS:...") on success to match earlier flow.
    """
    lookup_import_path = "/ic/api/integration/v1/lookups/archive"
    full_path = os.path.join(file_source_location, filepath)
    print("base url : {}".format(url))
    print("method : {}".format(method))
    print("filepath : {}".format(filepath))
    print("file_source_location : {}".format(file_source_location))
    print("Full path being opened: {}".format(full_path))

    if not os.path.isfile(full_path):
        raise Exception("ERROR: Lookup file not found at path: {}".format(full_path))
    # Append instance query-string so the service gets instance context (fixes instanceId null errors)
    archive_url = join_url(url, lookup_import_path) + oic_url_stub2
    try:
        with open(full_path, 'rb') as f:
            files = {
                'file': f,
                'type': (None, 'application/octet-stream'),
            }
            resp = requests.request(method.upper(), archive_url, headers=authorized_headers(), files=files, timeout=120)
    except Exception as e:
        print("Error uploading lookup file {}: {}".format(filepath, e))
        raise

    print("HTTP status: {}".format(resp.status_code))
    if str(resp.status_code).startswith("20"):
        print("{}: DEPLOYED".format(filepath))
        # Keep behaviour consistent with IAR script that raises success as exception
        raise Exception("SUCCESS: {}: DEPLOYED".format(filepath))
    else:
        try:
            body = resp.json()
        except Exception:
            body = {"error": "Non-JSON response: {}".format(resp.text)}
        detail = body.get("detail") or body.get("message") or body.get("error") or str(body)
        print("{}: NOT DEPLOYED. Error: {}".format(filepath, detail))
        raise Exception("ERROR: {}".format(detail))

def integrations(url, oci_filepath, file_source_location, artifact_indv_sec):
    """
    Main entry to process list of lookup files and update artifact_indv_sec similar to the IAR script.
    - url: base OIC design URL (eg. https://design.integration... )
    - oci_filepath: list of filenames (artifacts)
    - file_source_location: folder where artifact files reside
    - artifact_indv_sec: preloaded artifact_indv.json structure to update
    """
    print("Received Filepath: {}".format(oci_filepath))
    print("Using OIC Environment URL: {}".format(url))
    print("Using OIC Instance OCID: {}".format(instance_id))
    print("Using OAuth client_id: {}".format(client_id))
    print("Using OAuth scope: {}".format(scope))

    import_put_post = 'put'
    lookup_check_stub = "/ic/api/integration/v1/lookups/"
    artifact_type = "OIC"

    # Ensure artifact_indv_sec has expected keys
    if 'section' not in artifact_indv_sec:
        artifact_indv_sec['section'] = []
    if 'section_data' not in artifact_indv_sec:
        artifact_indv_sec['section_data'] = {}
    if 'deployment_info' not in artifact_indv_sec:
        artifact_indv_sec['deployment_info'] = {"oic_env": "##oic_env##", "status": "##status##", "obj_count": "##obj_count##"}

    if artifact_type not in artifact_indv_sec["section"]:
        artifact_indv_sec["section"].append(artifact_type)
        artifact_indv_sec["section_data"][artifact_type] = []

    artifact_indv_sec["deployment_info"]["oic_env"] = artifact_indv_sec["deployment_info"].get("oic_env", "##oic_env##").replace("##oic_env##", url)
    for filepath in oci_filepath:
        print("#" * 80)
        print("Processing: {}".format(filepath))
        artifact_indv_sec_data = {
            "name": filepath,
            "contains_error": "#contains_error#",
            "payload": "#payload#"
        }
        # Only process CSV lookups
        if not filepath.lower().endswith(".csv"):
            msg = "Skipping non-csv file: {}".format(filepath)
            print(msg)
            artifact_indv_sec_data["contains_error"] = "yes"
            artifact_indv_sec_data["payload"] = msg
            artifact_indv_sec["section_data"][artifact_type].append(artifact_indv_sec_data)
            continue
        try:
            # parse filename (without extension) as lookup id
            base = os.path.splitext(filepath)[0]
            lookup_name = base.strip()
            if not lookup_name:
                raise Exception("ERROR: Failed to derive lookup name from filename: {}".format(filepath))
            check_id_encoded = quote(lookup_name, safe='')
            # append instance query-string here too
            check_url = join_url(url, lookup_check_stub, check_id_encoded) + oic_url_stub2
            print("Will call lookup status API: {}".format(check_url))
            headers = authorized_headers()
            print("headers {}".format(headers))
            # Call GET to check lookup exists
            lookup_status_resp = requests.get(check_url, headers=headers, timeout=30)
            try:
                lookup_status = lookup_status_resp.json()
            except Exception:
                lookup_status = {"status": "HTTP {}".format(lookup_status_resp.status_code), "raw": lookup_status_resp.text}
            print("Lookup status response (code {}): {}".format(lookup_status_resp.status_code, lookup_status))
            import_put_post = 'put'
            # If service returns 404 or NotFound message -> POST, else PUT
            if lookup_status_resp.status_code == 404 or lookup_status.get("status", "").startswith("HTTP 404") or lookup_status.get("code") == "NotAuthorizedOrNotFound":
                # NotAuthorizedOrNotFound often appears when lookup is absent for this instance; treat as not found
                import_put_post = 'post'
                print("Lookup '{}' not found or not authorized for this instance; will POST.".format(lookup_name))
            else:
                import_put_post = 'put'
                print("Lookup '{}' exists or returned non-404; will PUT.".format(lookup_name))
            # Deploy
            deploy_lookup(url, import_put_post, filepath, file_source_location)
        except Exception as e:
            print("Exception handling {}: {}".format(filepath, e))
            artifact_indv_sec_data["payload"] = str(e)
            # determine contains_error by prefix in exception message following earlier convention
            s = str(e)
            if s.startswith("ERROR"):
                artifact_indv_sec_data["contains_error"] = "yes"
            elif s.startswith("SUCCESS"):
                artifact_indv_sec_data["contains_error"] = "no"
            else:
                artifact_indv_sec_data["contains_error"] = "yes"
            artifact_indv_sec["section_data"][artifact_type].append(artifact_indv_sec_data)

def create_json(json_file):
    obj_count = 0
    artifact_status = []
    for item in json_file.get("section", []):
        obj_count += len(json_file["section_data"].get(item, []))
        for value in json_file["section_data"].get(item, []):
            if value.get("contains_error") == "yes":
                artifact_status.append(1)
            elif value.get("contains_error") == "no":
                artifact_status.append(0)
    json_file["deployment_info"]["status"] = json_file["deployment_info"].get("status", "##status##").replace(
        "##status##", 'Contains Error' if any(artifact_status) else 'Deployment Successfully Done'
    )
    json_file["deployment_info"]["obj_count"] = json_file["deployment_info"].get("obj_count", "##obj_count##").replace(
        "##obj_count##", str(obj_count)
    )
    json_obj = json.dumps(json_file, indent=4)
    with open("int_dash.json", "w") as file:
        file.write(json_obj)
    print("Wrote int_dash.json summary.")

def read_json(json_file):
    with open(json_file, "r") as f:
        return json.load(f)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: lookup_script.py <json_file_path> '<input_parm_json>'")
        sys.exit(2)
    json_file_path = sys.argv[1]
    input_parm = json.loads(sys.argv[2])
    # load artifact metadata files (same names as your other script expects)
    artifact_indv_sec = read_json(os.path.join(json_file_path, "artifact_indv.json"))
    artifact_indv_sec_data = read_json(os.path.join(json_file_path, "artifact_indv_sec_data.json"))
    # Call integrations — uses oic_design_url as default (same pattern as your IAR script)
    integrations(
        oic_design_url,
        input_parm["artifact_list"],
        input_parm["source_repo"],
        artifact_indv_sec
    )
    # write out status summary (int_dash.json)
    create_json(artifact_indv_sec)
