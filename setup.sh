#!/bin/bash

set -e  # Exit script if any command fails

echo "🚀 Starting setup..."
sudo apt install git
sudo apt install wget

# Clone testbed repository
cd ~
echo "📥 Cloning testbed repository..."
git clone https://github.com/HenokDanielbfg/testbed.git
cd testbed

# Install Go
echo "📦 Installing Go..."
wget https://dl.google.com/go/go1.21.8.linux-amd64.tar.gz
sudo tar -C /usr/local -zxvf go1.21.8.linux-amd64.tar.gz
mkdir -p ~/go/{bin,pkg,src}

# Set up Go environment variables
echo "🔧 Setting up Go environment..."
echo 'export GOPATH=$HOME/go' >> ~/.bashrc
echo 'export GOROOT=/usr/local/go' >> ~/.bashrc
echo 'export PATH=$PATH:$GOPATH/bin:$GOROOT/bin' >> ~/.bashrc
echo 'export GO111MODULE=auto' >> ~/.bashrc
source ~/.bashrc

# Install dependencies
echo "📦 Installing dependencies..."
sudo apt -y update
sudo apt -y install wget git gnupg curl gcc g++ cmake autoconf libtool pkg-config libmnl-dev libyaml-dev
sudo apt -y install make libsctp-dev lksctp-tools iproute2
sudo snap install cmake --classic  # Ensure version > 3.17.0

# Install MongoDB
echo "📦 Installing MongoDB..."
curl -fsSL https://www.mongodb.org/static/pgp/server-7.0.asc | sudo gpg -o /usr/share/keyrings/mongodb-server-7.0.gpg --dearmor
echo "deb [ arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb-server-7.0.gpg ] https://repo.mongodb.org/apt/ubuntu focal/mongodb-org/7.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-7.0.list
sudo apt update
sudo apt install -y mongodb-org

# Start MongoDB
echo "🚀 Starting MongoDB..."
sudo systemctl start mongod
sudo systemctl enable mongod

# Install Node.js & Yarn
echo "📦 Installing Node.js & Yarn..."
sudo curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt update
sudo apt install -y nodejs
sudo corepack enable  # Enable Yarn

# Install Prometheus C++ library
echo "📦 Installing Prometheus C++ library..."
cd ~/testbed
git clone https://github.com/jupp0r/prometheus-cpp.git
cd prometheus-cpp
git submodule init
git submodule update
sudo apt install zlib1g-dev
sudo apt install libcurl4-openssl-dev
mkdir _build
cd _build
sudo cmake .. -DBUILD_SHARED_LIBS=ON
sudo cmake --build . --parallel 4
sudo cmake --install .

# Install Prometheus
echo "📦 Installing Prometheus..."
cd ~/testbed
sudo wget https://github.com/prometheus/prometheus/releases/download/v2.41.0/prometheus-2.41.0.linux-amd64.tar.gz
sudo tar -xvf prometheus-2.41.0.linux-amd64.tar.gz

# Reminder for manual Free5GC modification
echo "⚠️ MANUAL STEP REQUIRED:"
echo "Open testbed/go/pkg/mod/github.com/free5gc/openapi@v1.0.8/models/model_smf_event.go"
echo "Add the following line to the const variables:"
echo 'SmfEvent_PDU_SES_EST SmfEvent = "PDU_SES_EST"'
echo "Press Enter after completing this step..."
read -p ""



sudo apt remove --purge cmake -y && sudo apt update && sudo apt install -y software-properties-common && sudo add-apt-repository -y ppa:kitware/ppa && sudo apt update && sudo apt install -y cmake && cmake --version
# Install UERANSIM
echo "🛠️ Installing UERANSIM..."
cd ~/testbed/UERANSIM
# git checkout e4c492d
sudo make  # Make sure Prometheus C++ is installed first

# Install Free5GC
echo "🛠️ Installing Free5GC..."
cd ~/testbed
cd free5gc
# rmdir gtp5g
sudo make
sudo make webconsole

# Install GTP5G
echo "🛠️ Installing GTP5G..."
sudo git clone -b v0.8.7 https://github.com/free5gc/gtp5g.git
cd gtp5g
sudo make
sudo make install

echo "✅ Setup complete!"

