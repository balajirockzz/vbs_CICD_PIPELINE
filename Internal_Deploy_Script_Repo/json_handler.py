import json

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
    with open("database_dash.json", "w") as file:
        file.write(json_obj)

# def collect_json_output(artifact_indv_sec, error_file):
#     with open(error_file, 'r') as file:
#         lines = file.readlines()
#     error_lines = []
#     files = []
#     found_error = False
    
#     for line in lines:
#         if line.startswith("Error starting at line :") and line.find(".sql") != -1:

#                 files.append((line.strip().split(".")[-2]+"."+line.strip().split(".")[-1]))
#                 found_error = False
#         if line.startswith("Error report -"):
#             found_error = True
#         if found_error:
#             error_lines.append((line.strip()))

        
#     error_logs=("".join(error_lines).split("Error report -"))
#     filtered_list = [item for item in error_logs if item != ""]
#     error_json = dict(zip(files, filtered_list))
#     print("error_json:", error_json)
#     print("artifact_indv_sec:", artifact_indv_sec)
#     for my_dict in artifact_indv_sec["section_data"]["Database"]:
#         for key, value in error_json.items():
#             if key.split("/")[-1] == my_dict["name"]:
#                 my_dict["contains_error"]="yes"
#                 my_dict["payload"]=value
    
#     return artifact_indv_sec


def read_json(json_file):
    f = open(json_file, "r")
    return json.loads(f.read())
