#!/bin/bash

set -e  # Exit script if any command fails

echo "🚨 WARNING: This script will remove all installed components from setup.sh!"
read -p "Are you sure you want to proceed? (y/N): " confirm
if [[ ! $confirm =~ ^[Yy]$ ]]; then
    echo "❌ Cleanup aborted!"
    exit 1
fi

echo "🔄 Stopping MongoDB service..."
sudo systemctl stop mongod || true
sudo systemctl disable mongod || true

echo "🗑️ Removing installed packages..."
sudo apt remove -y wget git gnupg curl gcc g++ cmake autoconf libtool pkg-config libmnl-dev libyaml-dev
sudo apt remove -y make libsctp-dev lksctp-tools iproute2 nodejs mongodb-org
sudo apt autoremove -y

echo "🗑️ Removing Go installation..."
sudo rm -rf /usr/local/go
rm -rf ~/go

echo "🗑️ Removing Free5GC installation..."
rm -rf ~/testbed/free5gc

echo "🗑️ Removing GTP5G installation..."
rm -rf ~/testbed/free5gc/gtp5g

echo "🗑️ Removing UERANSIM installation..."
rm -rf ~/testbed/UERANSIM

echo "🗑️ Removing Prometheus installation..."
rm -rf ~/testbed/prometheus-2.41.0.linux-amd64
rm -rf ~/testbed/prometheus-cpp

echo "🗑️ Removing NWDAF installation..."
rm -rf ~/testbed/mnc_NWDAF-main

echo "🗑️ Removing Testbed repository..."
rm -rf ~/testbed

echo "🔄 Unsetting environment variables..."
sed -i '/export GOPATH/d' ~/.bashrc
sed -i '/export GOROOT/d' ~/.bashrc
sed -i '/export PATH=.*GOROOT/d' ~/.bashrc
sed -i '/export GO111MODULE/d' ~/.bashrc
source ~/.bashrc

echo "✅ Cleanup complete! All installed components have been removed."

