import socket
from IPy import IP

ports = [22, 80, 443]
# ssh,http,https
targetip = "stackoverflow.com"

print(f"\nScanning {targetip}\n")
for port in ports:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(1)
    try:
        s.connect((targetip, port))
        print(f"Port {port}: OPEN")
    except (socket.timeout):
        print(f"Port {port}: CLOSED")
    finally:
        s.close()

single_ip = IP('192.168.1.1')
print("\nIP:", single_ip)

# /28 network 
network = IP('192.168.1.0/29')
print("\nNetwork Addresses are:")
for ip in network:
    print(ip)