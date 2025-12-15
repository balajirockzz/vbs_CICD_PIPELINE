#! /usr/bin/python
from logging import info as _info, error as _error
from threading import Thread as _Thread
from multiprocessing import cpu_count as _cpu_count
from base64 import b64encode as _b64encode
from requests import post as _post
from xml.etree import cElementTree as ET
import json
import os
import sys
 
WAIT_TIME = 5
MAX_RUN_COUNT = _cpu_count()
responseResult = []
 
 
class _SoapConsumeUpload:
    def __init__(self, targetURL, targetUserName, targetPassword, reportLocalPath):
        self.targetWsdlURL = targetURL + "/analytics-ws/saw.dll?SoapImpl="
        self.targetUserName = targetUserName
        self.targetPassword = targetPassword
        self.header = {"Content-Type": "text/xml;charset=UTF-8"}
        self.reportLocalPath = reportLocalPath
 
    def _callPostMethod(self, body, soup_service, timeout=60, verify=False, **kargs):
        _message = kargs.get('message')
        _url = kargs.get('url', self.targetWsdlURL)
        _header = kargs.get('header', self.header)
        response = _post(_url+soup_service, data=body, headers=_header, verify=verify,
                         timeout=timeout)
        print('{_message} : {status}'.format(_message=_message, status=response.status_code))
        return response
 
 
    def get_session_token(self):
        body = '''<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" 
            xmlns:v6="urn://oracle.bi.webservices/v6">
            <soapenv:Header/>
            <soapenv:Body>
            <v6:logon>
            <v6:name>{user}</v6:name>
            <v6:password>{passs}</v6:password>
            </v6:logon>
            </soapenv:Body>
            </soapenv:Envelope>'''.format(user=self.targetUserName, passs=self.targetPassword)
 
        token = self._callPostMethod(body, soup_service="nQSessionService", message='Genrating Session Token')
        token = ET.fromstring(str(token.content.decode("utf-8")))[0][0][0].text
        return token
 
    def create_folder_structure(self, path, session_id):
        body = '''<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" 
        xmlns:v6="urn://oracle.bi.webservices/v6">
                        <soapenv:Header/>
                        <soapenv:Body>
                        <v6:createFolder>
                        <v6:path>/shared{path}</v6:path>
                        <v6:createIfNotExists>true</v6:createIfNotExists>
                        <v6:createIntermediateDirs>true</v6:createIntermediateDirs>
                        <v6:sessionID>{sessionid}</v6:sessionID>
                        </v6:createFolder>
                        </soapenv:Body>
                        </soapenv:Envelope>'''.format(path=path, sessionid=session_id)
        cfs = self._callPostMethod(body, soup_service="webCatalogService",
                                      message='Create Folder Structure if not Exist')
        content = str(cfs.content.decode("utf-8"))
 
 
    def uploadObject(self, path, session_id):
        print('Upload object processs started for {path}'.format(path=path))
        responseMessage = '_error : File failed to uploaded : ' + path
        artifact_indv_sec_data = {
            "name": "#name#",
            "contains_error": "#contains_error#",
            "payload": "#payload#"
        }
        try:
            fileName = os.path.splitext(os.path.basename(path))[0]
            fileExtension = os.path.splitext(os.path.basename(path))[1].replace(".","")
            fileLocation = '{path}/{fileName}.{fileExtension}'.format(path=self.reportLocalPath, fileName=fileName,
                                                                      fileExtension=fileExtension)
            objectZippedData = _b64encode(open(fileLocation, 'rb').read()).decode('utf-8')
            body = '''<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" 
            xmlns:v6="urn://oracle.bi.webservices/v6">
                        <soapenv:Header/>
                        <soapenv:Body>
                            <v6:pasteItem2>
                            <v6:archive>{objectZippedData}</v6:archive>
                            <v6:replacePath>/shared{path}</v6:replacePath>
                            <v6:flagACL>1</v6:flagACL>
                            <v6:flagOverwrite>1</v6:flagOverwrite>
                            <v6:sessionID>{sessionid}</v6:sessionID>
                        </v6:pasteItem2>
                        </soapenv:Body>
            </soapenv:Envelope>'''.format(path="/".join(path.split("/")[:-1]), objectZippedData=objectZippedData, sessionid=session_id)
            response = self._callPostMethod(body, message='Upload Function Called', soup_service="webCatalogService")
            content = str(response.content.decode("utf-8"))
            response = ET.fromstring(content)
            artifact_indv_sec_data["name"] = artifact_indv_sec_data["name"].replace("#name#", path.split('/')[-1])
            if "faultstring" not in content:
                responseMessage = 'Success : File uploaded successfully : ' + path
                print("File uploaded successfully")
                artifact_indv_sec_data["contains_error"] = artifact_indv_sec_data["contains_error"].replace(
                    "#contains_error#", "no")
            else:
                faultString = response[0][0][1].text
                responseMessage = '_error : %s : %s' % (faultString.__str__().replace(':', ''), path)
                artifact_indv_sec_data["contains_error"] = artifact_indv_sec_data["contains_error"].replace(
                    "#contains_error#", "yes")
 
        except Exception as e:
            _error(str(e))
            responseMessage = '_error : %s : %s' % (e.__str__().replace(':', ''), path)
            artifact_indv_sec_data["contains_error"] = artifact_indv_sec_data["contains_error"].replace(
                "#contains_error#", "yes")
 
            print('Upload processs completed for {path} -- {responseMessage}'.format(path=path,
                                                                                     responseMessage=responseMessage))
        finally:
            if 'REPORT' not in artifact_indv_sec["section"]:
                artifact_indv_sec["section"].append("REPORT")
                artifact_indv_sec["section_data"]["REPORT"] = []
            artifact_indv_sec_data["payload"] = artifact_indv_sec_data["payload"].replace("#payload#", responseMessage)
            artifact_indv_sec["section_data"]["REPORT"].append(artifact_indv_sec_data)
            return responseMessage
 
 
def multiThreadingUploadBI(SoapObj, reportRelativePath, session_id):
    print('uploadBI processs started for {reportRelativePath}'.
          format(reportRelativePath=reportRelativePath))
    responseString = SoapObj.uploadObject(reportRelativePath.strip(), session_id=session_id)
    responseResult.append(responseString)
    print('uploadBI processs completed for {reportRelativePath}'.format(reportRelativePath=reportRelativePath))
 
 
def uploadBI(url, user_name, password, reportRelativePath, reportLocalPath):
    session_id = ''
    print('uploadBI processs started')
    print('MAX_RUN_COUNT: {MAX_RUN_COUNT}'.format(MAX_RUN_COUNT=MAX_RUN_COUNT))
    print('WAIT_TIME: {WAIT_TIME}'.format(WAIT_TIME=WAIT_TIME))
    artifact_indv_sec["deployment_info"]["report_env"] = artifact_indv_sec["deployment_info"]["report_env"].replace(
        "##report_env##", url)
    soapConsumeObject = _SoapConsumeUpload(targetURL=url, targetUserName=user_name, targetPassword=password,
                                           reportLocalPath=reportLocalPath)
    if session_id == '':
        session_id = soapConsumeObject.get_session_token()
 
        for item in reportRelativePath.split(","):
            soapConsumeObject.create_folder_structure("/".join(item.split("/")[:-1]), session_id)
            threadList = [_Thread(target=multiThreadingUploadBI, args=(soapConsumeObject, path, session_id), name=path)
                          for path in
                          reportRelativePath.split(',')]
 
            for i in range(0, len(threadList), MAX_RUN_COUNT):
                runThreadList = threadList[i:i + MAX_RUN_COUNT]
                _info(runThreadList)
                [i.start() for i in runThreadList]
                [i.join() for i in runThreadList]
            print('uploadBI processs finsished')
            print("UploadBI process finished", responseResult)
            return ';'.join(responseResult)

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
 
    json_file["deployment_info"]["status"] = json_file["deployment_info"]["status"].\
        replace("##status##", 'Contains Error' if any(artifact_status) == True else 'Deployment Successfully Done')
    json_file["deployment_info"]["obj_count"] = json_file["deployment_info"]["obj_count"].replace("##obj_count##",
                                                                                                  str(obj_count))
 
    json_obj = json.dumps(json_file, indent=4)
    with open("bi_report_dash.json", "w") as file:
        file.write(json_obj)
 
 
def read_json(json_file):
    f = open(json_file, "r")
    return json.loads(f.read())
 
 

if __name__ == "__main__":
    json_file_path = sys.argv[1]
    input_parm= json.loads(sys.argv[2])
    artifact_indv_sec = read_json(json_file_path + "artifact_indv.json")
    artifact_indv_sec_data = read_json(json_file_path + "artifact_indv_sec_data.json")
    a = uploadBI(input_parm["url"],input_parm["username"],input_parm["password"],",".join(input_parm["artifact_list"]),input_parm["source_repo"])
    create_json(artifact_indv_sec)
