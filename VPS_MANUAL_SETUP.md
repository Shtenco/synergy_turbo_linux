# VirtualQubit Turbo Kernel - Manual VPS Setup

## VPS Connection Details
- **IP Address**: 92.246.131.14
- **Username**: root
- **SSH Key**: Linux Ubuntu.ppk

## Manual Setup Instructions

### Step 1: Connect to VPS
```bash
ssh -i "Linux Ubuntu.ppk" root@92.246.131.14
```

### Step 2: Install QEMU and Dependencies
```bash
# Update system
apt update && apt upgrade -y

# Install QEMU and tools
apt install -y qemu-system-x86 qemu-utils wget curl htop iotop sysstat zstd xxhash
```

### Step 3: Create VM Environment
```bash
# Create VM disk (20GB)
qemu-img create -f qcow2 vm.qcow2 20G

# Download Ubuntu Server ISO
wget https://releases.ubuntu.com/24.04/ubuntu-24.04-live-server-amd64.iso
```

### Step 4: Create VM Startup Script
```bash
cat > start_vm.sh << 'EOF'
#!/bin/bash
echo "=== Starting Ubuntu VM ==="
qemu-system-x86_64 \
  -m 2048 \
  -smp 2 \
  -drive file=vm.qcow2,format=qcow2 \
  -cdrom ubuntu-24.04-live-server-amd64.iso \
  -boot d \
  -net nic -net user \
  -nographic
EOF
chmod +x start_vm.sh
```

### Step 5: Transfer VirtualQubit Files to VPS
From your local machine:
```bash
scp -i "Linux Ubuntu.ppk" VirtualQubit_Shared.zip root@92.246.131.14:/root/
```

### Step 6: Transfer Files to VM
After VM installation, from VPS:
```bash
# Copy files to VM using scp or shared folders
scp VirtualQubit_Shared.zip user@vm_ip:/home/user/
```

### Step 7: Install Ubuntu VM
1. Run: `./start_vm.sh`
2. Follow Ubuntu Server installation
3. Enable SSH server during installation
4. Set up user account (e.g., vboxuser/vboxuser)
5. Reboot VM

### Step 8: VM Configuration
```bash
# Update VM
sudo apt update && sudo apt upgrade -y

# Install development tools
sudo apt install -y build-essential linux-headers-$(uname -r) dkms \
  python3 python3-pip git wget curl htop iotop sysstat zstd xxhash

# Install Python packages
pip3 install numpy scipy matplotlib numba zstandard xxhash
```

### Step 9: Install VirtualQubit Kernel Modules
```bash
# Extract files
unzip VirtualQubit_Shared.zip
cd VirtualQubit_Shared

# Run installation script
sudo ./install_kernel_modules.sh
```

### Step 10: System Optimization
```bash
# Configure HugePages
echo 32768 > /proc/sys/vm/nr_hugepages

# Disable NUMA balancing
echo 0 > /proc/sys/kernel/numa_balancing

# Set CPU governor to performance
for cpu in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do
  echo performance > "$cpu"
done

# Add to sysctl.conf for persistence
echo "vm.nr_hugepages = 32768" >> /etc/sysctl.conf
echo "kernel.numa_balancing = 0" >> /etc/sysctl.conf
```

### Step 11: Test Installation
```bash
# Load modules
sudo modprobe vqubit
sudo modprobe turbo_sched

# Test modules
python3 test_modules.py

# Run benchmarks
make benchmark
```

## Expected Results
- **FWHT Operations**: 3-5x faster
- **QFT Operations**: 4-8x faster
- **Overall Python Performance**: 2-3.5x faster
- **32GB HugePages allocated**
- **Optimized task scheduling**

## Troubleshooting

### SSH Connection Issues
```bash
# Check SSH service
systemctl status ssh

# Check firewall
ufw status
```

### QEMU Issues
```bash
# Check if KVM is available
egrep -c '(vmx|svm)' /proc/cpuinfo

# Use KVM if available
qemu-system-x86_64 -enable-kvm ...
```

### Module Installation Issues
```bash
# Check kernel headers
ls /lib/modules/$(uname -r)/build

# Check DKMS status
dkms status

# Check kernel messages
dmesg | grep vqubit
```

## VM Startup Commands

### Basic VM (without KVM)
```bash
qemu-system-x86_64 \
  -m 2048 \
  -smp 2 \
  -drive file=vm.qcow2,format=qcow2 \
  -cdrom ubuntu-24.04-live-server-amd64.iso \
  -boot d \
  -net nic -net user \
  -nographic
```

### VM with KVM (faster)
```bash
qemu-system-x86_64 \
  -enable-kvm \
  -m 2048 \
  -smp 2 \
  -drive file=vm.qcow2,format=qcow2 \
  -cdrom ubuntu-24.04-live-server-amd64.iso \
  -boot d \
  -net nic -net user \
  -nographic
```

### VM with SSH Port Forwarding
```bash
qemu-system-x86_64 \
  -m 2048 \
  -smp 2 \
  -drive file=vm.qcow2,format=qcow2 \
  -cdrom ubuntu-24.04-live-server-amd64.iso \
  -boot d \
  -net nic \
  -net user,hostfwd=tcp::2222-:22 \
  -nographic
```

Then connect to VM:
```bash
ssh user@localhost -p 2222