#!/bin/bash
# Complete VPS Installation Script for VirtualQubit Turbo Kernel

echo "=== VirtualQubit Turbo Kernel VPS Installation ==="
echo "Starting automated setup..."

# Step 1: Install QEMU and dependencies
echo "Step 1: Installing QEMU and dependencies..."
apt update && apt upgrade -y
apt install -y qemu-system-x86 qemu-utils wget curl htop iotop sysstat zstd xxhash

# Step 2: Create VM disk
echo "Step 2: Creating VM disk..."
qemu-img create -f qcow2 vm.qcow2 20G

# Step 3: Download Ubuntu ISO
echo "Step 3: Downloading Ubuntu ISO..."
wget https://releases.ubuntu.com/24.04/ubuntu-24.04-live-server-amd64.iso

# Step 4: Create VM startup script
echo "Step 4: Creating VM startup script..."
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

echo "=== VPS Setup Complete ==="
echo ""
echo "Files created:"
echo "- vm.qcow2 (20GB VM disk)"
echo "- ubuntu-24.04-live-server-amd64.iso"
echo "- start_vm.sh (VM startup script)"
echo ""
echo "Next steps:"
echo "1. Run: ./start_vm.sh"
echo "2. Install Ubuntu Server in the VM with SSH access"
echo "3. Transfer VirtualQubit_Shared.zip to the VM"
echo "4. Extract and run: sudo ./install_kernel_modules.sh"
echo ""
echo "VM startup command:"
echo "qemu-system-x86_64 -m 2048 -smp 2 -drive file=vm.qcow2,format=qcow2 -cdrom ubuntu-24.04-live-server-amd64.iso -boot d -net nic -net user -nographic"