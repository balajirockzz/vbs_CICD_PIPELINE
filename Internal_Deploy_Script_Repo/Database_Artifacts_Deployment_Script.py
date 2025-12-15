import subprocess
import json_handler
import sys
import os          # <-- Added for path handling
import oracledb

json_file_path = sys.argv[1]
input_parm = json_handler.json.loads(sys.argv[2])
artifact_indv_sec = json_handler.read_json(json_file_path + "artifact_indv.json")
artifact_indv_sec_data = json_handler.read_json(json_file_path + "artifact_indv_sec_data.json")
tns_service = sys.argv[3]
wallet_password = input_parm["walletpassword"]
wallet_dir = sys.argv[4]
wallet_dir = r"{}".format(wallet_dir)

class database_artifact:
    def __init__(self, username, password, artifact_list, source_repo, connection_string, artifact_type):
        self.username = username
        self.password = password
        self.artifact_list = artifact_list
        self.source_repo = source_repo
        self.connection_string = connection_string
        self.artifact_type = artifact_type

    def sqlexecute(self, sql_file_full_path):
        print("Execution Block")
        artifact_indv_sec_metadata = artifact_indv_sec_data.copy() if isinstance(artifact_indv_sec_data, dict) else {}
        contains_error = "no"
        Message = ""
        cur = None
        conn = None

        try:
            conn = oracledb.connect(
                user=self.username,
                password=self.password,
                dsn=tns_service,
                config_dir=wallet_dir,
                wallet_location=wallet_dir,
                wallet_password=wallet_password
            )
            cur = conn.cursor()
            print(f"Looking for SQL file at: {sql_file_full_path}")
            with open(sql_file_full_path, 'r') as f:
                sql_script = f.read()

            statements = [s.strip() for s in sql_script.split(';') if s.strip()]

            for statement in statements:
                try:
                    if statement:
                        print(f"Executing: {statement[:50]}...")
                        cur.execute(statement)
                        if cur.description:
                            rows = cur.fetchall()
                            print(f"Fetched {len(rows)} row(s).")
                except oracledb.Error as e_stmt:
                    contains_error = "yes"
                    (err_obj,) = e_stmt.args
                    err_message = f"Error executing statement: {err_obj.message}"
                    print(err_message)
                    Message += err_message + "\n"
                    continue

            conn.commit()
            print("SQL file executed successfully.")

            if not Message:
                Message = f"{sql_file_full_path} Artifact Deployed Successfully"

        except oracledb.Error as e:
            contains_error = "yes"
            (error_obj,) = e.args if e.args else (e,)
            Message = getattr(error_obj, "message", str(e))
            print(f"Error executing SQL file: {Message}")
        except FileNotFoundError:
            contains_error = "yes"
            Message = f"Error: SQL file not found at {sql_file_full_path}"
            print(Message)
        except Exception as e:
            contains_error = "yes"
            Message = f"An unexpected error occurred: {e}"
            print(Message)
        finally:
            artifact_indv_sec_metadata["contains_error"] = contains_error
            artifact_indv_sec_metadata["name"] = sql_file_full_path
            artifact_indv_sec_metadata["payload"] = Message
            print(artifact_indv_sec_metadata)
            try:
                if cur:
                    cur.close()
            except Exception:
                pass
            try:
                if conn:
                    conn.close()
            except Exception:
                pass

        return artifact_indv_sec_metadata

    def upload(self):
        print("Artifact_list", self.artifact_list)
        atype = self.artifact_type

        artifact_indv_sec.setdefault("section", [])
        artifact_indv_sec.setdefault("section_data", {})
        artifact_indv_sec.setdefault("artifact_name", artifact_indv_sec.get("artifact_name", "##artifact_name##"))

        artifact_indv_sec["section"].append(atype)
        artifact_indv_sec["section_data"].update({atype: []})
        artifact_indv_sec["artifact_name"] = artifact_indv_sec["artifact_name"].replace("##artifact_name##", atype)

        for sql_file in self.artifact_list:
            # --- UPDATED: construct the full path if needed
            if not os.path.isabs(sql_file):
                sql_file_full_path = os.path.join(self.source_repo, sql_file)
            else:
                sql_file_full_path = sql_file
            print("SQL File name:", sql_file_full_path)
            out_json = self.sqlexecute(sql_file_full_path)
            print("out json", out_json)
            artifact_indv_sec["section_data"][atype].append(out_json.copy())

        if atype == "Database":
            update_deployment_info = artifact_indv_sec.setdefault("deployment_info", {})
            update_deployment_info["db_env"] = self.connection_string
            update_deployment_info["oic_env"] = "NA"
            update_deployment_info["report_env"] = "NA"

        return artifact_indv_sec

if __name__ == "__main__":
    artifact_type = "Database"
    a = database_artifact(
        input_parm["username"],
        input_parm["password"],
        input_parm["artifact_list"],
        input_parm["source_repo"],
        input_parm["url"],
        artifact_type
    )
    json_handler.create_json(a.upload())
