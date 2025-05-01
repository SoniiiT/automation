import paramiko

# Kopieren Sie den privaten Schlüssel aus 1Password und fügen Sie ihn hier als String ein
PASSWORD = "123456789"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

# Verbindung mit SSH-Schlüssel
ssh.connect("192.168.178.240", username="vm1", password=PASSWORD)
ssh.connect("192.168.178.241", username="vm2", password=PASSWORD)

print("Connected to the server")

ssh.close()