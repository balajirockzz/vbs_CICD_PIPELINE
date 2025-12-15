import oracledb
wallet_dir = r"/Database/Wallet_FUSIONPAASDEV"
tns_service = "fusionpaasdev_high"
username = "TERCONV"
password = "j$ukmF34F4%K"
wallet_password = "Teradyne$123"
# In thin mode you can pass wallet_location and wallet_password to connect
conn = oracledb.connect(
user=username,
password=password,
dsn=tns_service,
config_dir=wallet_dir,# optional but useful: where sqlnet.ora / tnsnames.ora live
wallet_location=wallet_dir,# must contain ewallet.pem for thin mode
wallet_password=wallet_password)
cur = conn.cursor()
cur.execute("SELECT sysdate FROM dual")
print("Database time is:", cur.fetchone()[0])
cur.close()
conn.close()
