
from multiprocessing import cpu_count as _cpu_count
import requests
from requests.auth import HTTPBasicAuth
import json
import os
import sys

WAIT_TIME = 5
MAX_RUN_COUNT = _cpu_count()
responseResult = []
headers = {'X-HTTP-Method-Override': 'PATCH', 'Accept': 'application/json'}

#####################################################Integrations Deployments#############################


def act_deactivate_iar(url, user, passs, id, status):  # Activate and deactivate the integrations using this method
    iar_deac_act_url = '/ic/api/integration/v1/integrations/'
    if status == "ACTIVATED":
        payload = {'status': 'ACTIVATED'}
        iar_act = requests.post(url + iar_deac_act_url + str(id), headers=headers,
                                auth=HTTPBasicAuth(user, passs), json=payload)
    else:
        payload = {'status': 'CONFIGURED'}
        iar_act = requests.post(url + iar_deac_act_url + id, headers=headers,
                                auth=HTTPBasicAuth(user, passs), json=payload)
    iar_act = json.loads(iar_act.content)
    if iar_act["status"] != status:
        print("{id} : {title}".format(id=id, title=iar_act["title"]))
        return "Error"
    else:
        print("{id}: {status}!".format(id=id, status=status))
        return "Success"



def deploy_par(url, user, passs, method, filepath, filename):
    par_import_url = '/ic/api/integration/v1/packages/archive'
    files = {
        'file': open(filepath+filename, 'rb'),
        'type': (None, 'application/octet-stream'),
    }
    pkg_import = requests.request(method, url + par_import_url, headers=headers, auth=HTTPBasicAuth(user, passs),
                               files=files)
    print(pkg_import.content)

    if str(pkg_import.status_code).startswith("20"):
        print("{filepath}: DEPLOYED".format(filepath=filename))
        raise Exception("SUCCESS: {filepath}: DEPLOYED".format(filepath=filename))

    else:
        o_par_deploy = json.loads(pkg_import.content)
        print("{filepath}: NOT DEPLOYED ".format(filepath=filename))
        print("Error: {error}".format(error=o_par_deploy["detail"]))
        raise Exception("ERROR: {error}".format(error=o_par_deploy["detail"]))

def integrations(url, user, passs, oci_filepath, file_source_location):
    # Intialize variable values
    print("Recieved Filepath: {V_FILEPATHS}".format(V_FILEPATHS=oci_filepath))
    print("Iterating over filepaths and processing for deployment......")
    import_put_post = 'put'
    par_check_url = '/ic/api/integration/v1/packages/'
    artifact_type = "OIC"
    if 'OIC' not in artifact_indv_sec["section"]:
        artifact_indv_sec["section"].append(artifact_type)
        artifact_indv_sec["section_data"][artifact_type] = []
    artifact_indv_sec["deployment_info"]["oic_env"] = artifact_indv_sec["deployment_info"]["oic_env"].replace(
        "##oic_env##", url)

    for filepath in oci_filepath:
        print("###################################{filepath}###############################".format(filepath=filepath))
        artifact_indv_sec_data = {
            "name": "#name#",
            "contains_error": "#contains_error#",
            "payload": "#payload#"
        }

        if filepath.lower().endswith(".par"):
            try:
                filetype = "PAR"
                print("FileType: PACKAGE ARCHIVE")
                print("{filepath}: Deployment has been started".format(filepath=filepath))
                # Checking the status of the package
                # checking the staus of the package
                o_par_statu = requests.get(url + par_check_url + os.path.splitext(filepath)[0], headers=headers,
                                           auth=HTTPBasicAuth(user, passs))
                o_par_status = json.loads(o_par_statu.content)
                if o_par_statu.status_code != 200:
                    print("Package Not Found. Deploying.......")
                    import_put_post = "post"
                elif str(o_par_statu.status_code).startswith("20"):
                    print("{filepath}: package found".format(filepath=filepath))
                    iar_list = o_par_status["integrations"]
                    print("Integrations list", iar_list)
                    for iar in iar_list:
                        iar_status = iar["status"]
                        print("Deactivate the integration if activated")
                        if iar_status == "ACTIVATED":
                            act_result = act_deactivate_iar(url, user, passs, iar["id"], "CONFIGURED")
                            if act_result == "Success":
                                print("{file_name}: DE_ACTIVATED".format(file_name=iar["name"]))
                            elif act_result == "Error":
                                print("{file_name}: Got error while DE_ACTIVATING".format(file_name=iar["name"]))
                                raise Exception("ERROR: {file_name} got error while DE_ACTIVATING".
                                                format(file_name=iar["name"]))
                    import_put_post='put'
                print("Deploying Package")
                deploy_par(url, user, passs, import_put_post, file_source_location,filepath)

            except Exception as e:

                print("{e}".format(e=e))

                artifact_indv_sec_data['name'] = artifact_indv_sec_data['name'].replace("#name#", filepath)
                artifact_indv_sec_data["payload"] = artifact_indv_sec_data["payload"].replace("#payload#", str(e))

                if str(e).split(":")[0] == "ERROR":
                    artifact_indv_sec_data["contains_error"] = artifact_indv_sec_data["contains_error"]. \
                        replace("#contains_error#", "yes")

                elif str(e).split(":")[0] == "SUCCESS":

                    artifact_indv_sec_data["contains_error"] = artifact_indv_sec_data["contains_error"].replace(
                        "#contains_error#", "no")

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

    json_file["deployment_info"]["status"] = json_file["deployment_info"]["status"]. \
        replace("##status##", 'Contains Error' if any(artifact_status) == True else 'Deployment Successfully Done')
    json_file["deployment_info"]["obj_count"] = json_file["deployment_info"]["obj_count"].replace("##obj_count##",
                                                                                                  str(obj_count))

    json_obj = json.dumps(json_file, indent=4)
    with open("pkg_dash.json", "w") as file:
        file.write(json_obj)


def read_json(json_file):
    f = open(json_file, "r")
    return json.loads(f.read())


if __name__ == "__main__":
    json_file_path = sys.argv[1]
    input_parm= json.loads(sys.argv[2])
    artifact_indv_sec = read_json(json_file_path + "artifact_indv.json")
    artifact_indv_sec_data = read_json(json_file_path + "artifact_indv_sec_data.json")
    a = integrations(input_parm["url"], input_parm["username"], input_parm["password"], input_parm["artifact_list"], input_parm["source_repo"])
    create_json(artifact_indv_sec)
