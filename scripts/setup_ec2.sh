#!/bin/bash

# Update system packages
echo "🚀 Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install prerequisite packages
echo "📦 Installing prerequisites..."
sudo apt install -y curl git unzip ufw nginx certbot python3-certbot-nginx

# Install Docker
echo "🐳 Installing Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    rm get-docker.sh
fi

# Install Docker Compose plugin
echo "🐙 Installing Docker Compose..."
sudo apt install -y docker-compose-plugin

# Configure Firewall
echo "🛡️ Configuring Firewall..."
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw --force enable

echo "✅ EC2 Server setup completed successfully!"
echo "⚠️ IMPORTANT: Please log out and log back in (or run 'newgrp docker') for docker group permissions to take effect."
