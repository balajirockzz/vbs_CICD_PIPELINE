import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import base64
import json
import os
import sys

try:
    import oci
except ImportError:
    os.system('pip install oci')
    import oci

class SMTP_SERVER:
    def __init__(self, sender, subject):
        self.sender = sender
        self.subject = subject

    def get_credentials(self):
        config = oci.config.from_file()
        secrets_client = oci.secrets.SecretsClient(config)
        get_secret_bundle_by_name_response = secrets_client.get_secret_bundle_by_name(
            secret_name="DEV1_SMTP_1",
            vault_id="ocid1.vault.oc1.iad.ejurjoqaaahte.abuwcljsmbmhq7elzyjpfdweajchv3nvjblysoi5lq6bj6mhvgiwhy66bk2q"
        )
        base64_Secret_content = get_secret_bundle_by_name_response.data.secret_bundle_content.content
        base64_secret_bytes = base64_Secret_content.encode('ascii')
        base64_message_bytes = base64.b64decode(base64_secret_bytes)
        secret_content = base64_message_bytes.decode('ascii')
        secret_content_json = json.loads(secret_content)
        self. OCI_SMTP_USERID = secret_content_json["USERNAME"]
        self. OCI_SMTP_HOST = secret_content_json["SMTP_SERVER"]
        self. OCI_SMTP_PORT = secret_content_json["PORT"]
        self. OCI_SMTP_PASS = secret_content_json["PASSWORD"]
        self. OCI_SMTP_RECEIVERS = secret_content_json["RECEIVERS"]

    def create_email(self):
        msg = MIMEMultipart()
        filename = sys.argv[3]
        with open(filename) as report_file:
            html = report_file.read()
        email_body = f"""<p>
        <p style="font-size:15px">Hi,</p>
        <p style="font-size:15px">Please refer the deployment information or <a href="https://delmarketsol-nacaus19.developer.ocp.oraclecloud.com/delmarketsol-nacaus19/#projects/artifact-deployment-project/cibuild/jobs/test%20mail/builds/{sys.argv[2]}/log">click here</a> to view from VBS tool
        </p>{html.replace('<nav class="navbar navbar-inverse"><ul class="nav navbar-nav"><li><a href="#">Deployment Summary</a></li></ul></nav>'," ")}
        <p style="font-size:15px">Thanks</p>"""
        msg.attach(MIMEText(email_body, 'html'))
        msg['From'] = self.sender
        msg['To'] = self. OCI_SMTP_RECEIVERS[0]
        msg['Subject'] = self.subject
        self.msg = msg

    def send_email(self):
        try:
            context = ssl.create_default_context()
            with smtplib.SMTP(self. OCI_SMTP_HOST, int(self. OCI_SMTP_PORT)) as server:
                server.ehlo()
                server.starttls(context=context)
                server.ehlo()
                server.login(self. OCI_SMTP_USERID, self. OCI_SMTP_PASS)
                server.sendmail(self.sender, self. OCI_SMTP_RECEIVERS, self.msg.as_string())
        except Exception as e:
            print(f"SMTP Error: {e}")

if __name__ == "__main__":
    sender = "bumapathy1998@gmail.com"
    subject = "VBS {env} {art_type} Deployment Summary ".format(env=sys.argv[4], art_type=sys.argv[5])

    email_server = SMTP_SERVER(sender, subject)
    email_server.get_credentials()
    email_server.create_email()
    email_server.send_email()