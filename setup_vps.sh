#!/bin/bash
# VPS Setup Script for VirtualQubit Turbo Kernel

echo "=== VirtualQubit VPS Setup Script ==="
echo "Installing QEMU and dependencies..."

# Update system
apt update && apt upgrade -y

# Install QEMU
apt install -y qemu-system-x86 qemu-utils

# Install additional tools
apt install -y wget curl htop iotop sysstat zstd xxhash

echo "=== QEMU Installation Complete ==="
echo "Creating VM disk..."

# Create VM disk (20GB)
qemu-img create -f qcow2 vm.qcow2 20G

echo "=== Downloading Ubuntu ISO ==="
# Download Ubuntu Server 24.04
wget https://releases.ubuntu.com/24.04/ubuntu-24.04-live-server-amd64.iso

echo "=== Setup Complete ==="
echo "Files created:"
echo "- vm.qcow2 (20GB VM disk)"
echo "- ubuntu-24.04-live-server-amd64.iso"

echo ""
echo "Next steps:"
echo "1. Run: ./start_vm.sh"
echo "2. Install Ubuntu Server in the VM"
echo "3. Transfer VirtualQubit_Shared.zip to the VM"
echo "4. Extract and run: sudo ./install_kernel_modules.sh"