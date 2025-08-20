#!/bin/bash

# Suna AI Code Server Startup Script
# This script initializes Code Server with recommended extensions and settings

set -e

echo "🚀 Starting Suna AI Code Server initialization..."

# Create necessary directories
mkdir -p /home/coder/.local/share/code-server/User
mkdir -p /home/coder/.local/share/code-server/extensions

# Copy settings if they don't exist
if [ ! -f "/home/coder/.local/share/code-server/User/settings.json" ]; then
    echo "📝 Installing VS Code settings..."
    cp /workspace/backend/services/code_server/settings.json /home/coder/.local/share/code-server/User/settings.json
fi

# Install recommended extensions
echo "🔌 Installing recommended extensions..."

# Core extensions
code-server --install-extension ms-python.python
code-server --install-extension ms-python.vscode-pylance
code-server --install-extension ms-vscode.vscode-typescript-next
code-server --install-extension bradlc.vscode-tailwindcss
code-server --install-extension esbenp.prettier-vscode
code-server --install-extension ms-vscode.vscode-eslint

# Additional useful extensions
code-server --install-extension ms-vscode.vscode-json
code-server --install-extension redhat.vscode-yaml
code-server --install-extension ms-vscode.vscode-markdown
code-server --install-extension eamodio.gitlens
code-server --install-extension formulahendry.auto-rename-tag
code-server --install-extension christian-kohler.path-intellisense

echo "✅ Code Server initialization complete!"
echo "🌐 Access your IDE at: http://localhost:8080"
echo "🔑 Password: suna-code-server"

# Start code-server
exec code-server "$@"