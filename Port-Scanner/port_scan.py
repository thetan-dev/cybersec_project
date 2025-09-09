import socket
from IPy import IP

ports = [22, 80, 443]
# ssh,http,https
target_ip = "scanme.nmap.org"

print(f"\nScanning {target_ip}\n")
for port in ports:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(1)
    try:
        s.connect((target_ip, port))
        print(f"Port {port}: OPEN")
    except (socket.timeout, ConnectionRefusedError, OSError):
        print(f"Port {port}: CLOSED")
    finally:
        s.close()

single_ip = IP('192.168.1.1')
print("\nIP:", single_ip)

# /28 network has 16 addresses
network = IP('192.168.1.0/28')
print("\n/28 Network Addresses:")
for ip in network:
    print(ip)
