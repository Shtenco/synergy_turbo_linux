#!/bin/bash
# VM Startup Script

echo "=== Starting Ubuntu VM ==="

# Launch Ubuntu VM with QEMU
qemu-system-x86_64 \
  -m 2048 \
  -smp 2 \
  -drive file=vm.qcow2,format=qcow2 \
  -cdrom ubuntu-24.04-live-server-amd64.iso \
  -boot d \
  -net nic -net user \
  -nographic

echo "VM started. Follow the Ubuntu installation prompts."
echo "After installation, reboot the VM and remove the -cdrom parameter."