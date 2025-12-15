from multiprocessing import cpu_count as _cpu_count
import requests
from requests.auth import HTTPBasicAuth
import json
import sys
import os

try:
    from zipfile import ZipFile
except ImportError:
    os.system('pip install zipfile')
    os.system('pip list')

from zipfile import ZipFile

WAIT_TIME = 5
MAX_RUN_COUNT = _cpu_count()
responseResult = []
headers = {'X-HTTP-Method-Override': 'PATCH', 'Accept': 'application/json'}


def deploy_library(url, user, passs, method, filepath, file_source_location, version, fileName):
    files = {
        'name': (None, fileName),
        'code': (None, fileName.upper()),
        'version': (None, version),
        'description': (None, 'JavaScript library description'),
        'type': (None, 'API'),
        'file': open(file_source_location + filepath.replace("zip", "jar"), 'rb'),
    }
    library_import = requests.request(method, url , headers=headers,
                                      auth=HTTPBasicAuth(user, passs),
                                      files=files)
    if str(library_import.status_code).startswith("20"):
        print("{filepath}: DEPLOYED".format(filepath=filepath))
        return library_import.status_code
    else:
        library_deploy = json.loads(library_import.content)
        print("{filepath}: NOT DEPLOYED ".format(filepath=filepath))
        print("Error: {error}".format(error=library_deploy["detail"]))
        raise Exception("ERROR: {error}".format(error=library_deploy["detail"]))


def deploy_library_metadata(url, user, passs, method, filepath, file_source_location, id):
    library_import_url = '/ic/api/integration/v1/libraries/{id}/metadata'
    filepath = filepath.replace("zip", "xml")
    files = {
        'file': open(file_source_location + filepath, 'rb'),
    }
    library_import = requests.request(method, url + library_import_url.format(id=id), headers=headers,
                                      auth=HTTPBasicAuth(user, passs),
                                      files=files)
    print(json.loads(library_import.content))
    if str(library_import.status_code).startswith("20"):
        print("{filepath}: Metadata has been uploaded successfully!!".format(filepath=filepath))
        raise Exception("SUCCESS: {filepath}: Metadata has been uploaded successfully!!".format(filepath=filepath))
    else:
        library_deploy = json.loads(library_import.content)
        print(library_deploy)
        print("{filepath}: Metadata not able to upload ".format(filepath=filepath))
        print("Error: {error}".format(error=library_deploy["detail"]))
        raise Exception("ERROR: {error}".format(error=library_deploy["detail"]))


def integrations(url, user, passs, files, file_source_location):
    # Intialize variable values
    print("Recieved Filepath: {V_FILEPATHS}".format(V_FILEPATHS=files))
    print("Iterating over filepaths and processing for deployment......")
    import_put_post = 'put'
    library_check_url = '/ic/api/integration/v1/libraries/'
    artifact_type = "Library"
    if 'Library' not in artifact_indv_sec["section"]:
        artifact_indv_sec["section"].append(artifact_type)
        artifact_indv_sec["section_data"][artifact_type] = []
    artifact_indv_sec["deployment_info"]["oic_env"] = artifact_indv_sec["deployment_info"]["oic_env"].replace(
        "##oic_env##", url)

    for file in files:
        print("###################################{filepath}###############################".format(filepath=file))
        artifact_indv_sec_data = {
            "name": "#name#",
            "contains_error": "#contains_error#",
            "payload": "#payload#"
        }

        if file.lower().endswith(".zip"):
            try:
                result = os.path.splitext(file)
                fileName, fileExtension = "_".join(result[0].split('_')[:-1]), result[1]
                version = result[0].split("_")[-1].strip()
                with ZipFile(file_source_location + file, 'r') as zObject:
                    zObject.extractall(path=file_source_location + fileName + "/")

                print("Checking the status of the {filepath} integration".format(filepath=file))
                library_status = requests.get(url + library_check_url + fileName + "|" + version, headers=headers,
                                              auth=HTTPBasicAuth(user, passs))

                if library_status.status_code == 404:
                    import_put_post = 'post'
                    update_library_url = "/ic/api/integration/v1/libraries/archive"
                    library = deploy_library(url+update_library_url, user, passs, import_put_post, file,
                                             file_source_location + fileName + "/", version,
                                             fileName)

                elif library_status.status_code == 200:
                    import_put_post = 'post'
                    update_library_url = "/ic/api/integration/v1/libraries/{id}/archive".format(id=fileName + "|" + version)
                    library = deploy_library(url+update_library_url, user, passs, import_put_post, file,
                                             file_source_location + fileName + "/", version,
                                             fileName)

                if library == 200:
                        deploy_library_metadata(url, user, passs, import_put_post, file,
                                                file_source_location + fileName + "/",
                                                id=fileName.upper() + "|" + version)
                else:
                    print(json.loads(library_status.content))

            except Exception as e:
                print("{e}".format(filepath=file, e=e))
                print(artifact_indv_sec_data)
                artifact_indv_sec_data['name'] = artifact_indv_sec_data['name'].replace("#name#", file)
                artifact_indv_sec_data["payload"] = artifact_indv_sec_data["payload"].replace("#payload#", str(e))

                if str(e).split(":")[0] == "ERROR":
                    artifact_indv_sec_data["contains_error"] = artifact_indv_sec_data["contains_error"]. \
                        replace("#contains_error#", "yes")
                elif str(e).split(":")[0] == "SUCCESS":
                    artifact_indv_sec_data["contains_error"] = artifact_indv_sec_data["contains_error"].replace(
                        "#contains_error#", "no")
                print(artifact_indv_sec_data)
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
    with open("int_dash.json", "w") as file:
        file.write(json_obj)


def read_json(json_file):
    f = open(json_file, "r")
    return json.loads(f.read())


if __name__ == "__main__":
    json_file_path = sys.argv[1]
    input_parm = json.loads(sys.argv[2])
    artifact_indv_sec = read_json(json_file_path + "artifact_indv.json")
    artifact_indv_sec_data = read_json(json_file_path + "artifact_indv_sec_data.json")
    a = integrations(input_parm["url"], input_parm["username"], input_parm["password"], input_parm["artifact_list"], input_parm["source_repo"])
    create_json(artifact_indv_sec)
