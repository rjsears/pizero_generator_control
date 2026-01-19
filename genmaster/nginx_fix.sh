#!/bin/bash
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
# nginx_fix.sh - Fix Portainer nginx configuration
#
# This script patches an existing nginx.conf to fix
# Portainer reverse proxy issues (rewrite rule, WebSocket support)
#
# Usage: ./nginx_fix.sh [path_to_nginx.conf]
# Default path: ./nginx/nginx.conf
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

set -e

NGINX_CONF="${1:-./nginx/nginx.conf}"

if [ ! -f "$NGINX_CONF" ]; then
    echo "Error: nginx.conf not found at $NGINX_CONF"
    echo "Usage: $0 [path_to_nginx.conf]"
    exit 1
fi

echo "Fixing Portainer configuration in $NGINX_CONF..."

# Backup the original file
cp "$NGINX_CONF" "${NGINX_CONF}.bak"
echo "Backup created: ${NGINX_CONF}.bak"

# Create the new Portainer configuration
NEW_PORTAINER_CONFIG='        # Portainer - Container Management UI
        location /portainer/ {
            if ($access_level = "external") {
                return 403;
            }

            # Rewrite /portainer/ to / for Portainer
            rewrite ^/portainer/(.*) /$1 break;

            proxy_pass http://genmaster_portainer:9000;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;

            # WebSocket timeouts
            proxy_read_timeout 86400;
            proxy_send_timeout 86400;
            proxy_buffering off;
        }

        # Portainer WebSocket endpoint
        location /portainer/api/websocket/ {
            if ($access_level = "external") {
                return 403;
            }

            rewrite ^/portainer/(.*) /$1 break;

            proxy_pass http://genmaster_portainer:9000;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host $host;
            proxy_read_timeout 86400;
            proxy_buffering off;
        }'

# Use sed to replace the old Portainer location block
# First, check if the old configuration exists
if grep -q 'location /portainer/' "$NGINX_CONF"; then
    # Create a temp file for the replacement
    TEMP_FILE=$(mktemp)

    # Use awk to replace the entire location block
    awk -v new_config="$NEW_PORTAINER_CONFIG" '
    /location \/portainer\// {
        in_block = 1
        brace_count = 0
        print new_config
        next
    }
    in_block {
        # Count braces to find end of block
        for (i = 1; i <= length($0); i++) {
            c = substr($0, i, 1)
            if (c == "{") brace_count++
            if (c == "}") brace_count--
        }
        if (brace_count <= 0) {
            in_block = 0
        }
        next
    }
    { print }
    ' "$NGINX_CONF" > "$TEMP_FILE"

    mv "$TEMP_FILE" "$NGINX_CONF"
    echo "Portainer configuration updated successfully!"
else
    echo "Warning: No existing Portainer location block found in $NGINX_CONF"
    echo "You may need to add the Portainer configuration manually."
    exit 1
fi

echo ""
echo "To apply changes, restart nginx:"
echo "  docker exec genmaster_nginx nginx -s reload"
echo ""
echo "Or if running outside Docker:"
echo "  sudo nginx -s reload"
