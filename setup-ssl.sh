#!/bin/bash

echo "======================================"
echo "  Knowledger SSL Setup with Certbot"
echo "======================================"
echo ""

# Check if domain is provided
if [ -z "$1" ] || [ -z "$2" ]; then
    echo "Usage: ./setup-ssl.sh YOUR_DOMAIN YOUR_EMAIL"
    echo "Example: ./setup-ssl.sh knowledger.example.com you@example.com"
    exit 1
fi

DOMAIN=$1
EMAIL=$2

echo "Domain: $DOMAIN"
echo "Email: $EMAIL"
echo ""

# Step 1: Create certbot directories
echo "Step 1: Creating certbot directories..."
mkdir -p certbot/conf certbot/www
echo "✅ Directories created"
echo ""

# Step 2: Update nginx config with domain
echo "Step 2: Setting up nginx for certificate verification..."
cp nginx/nginx.conf.http nginx/nginx.conf
sed -i.bak "s/YOUR_DOMAIN_HERE/$DOMAIN/g" nginx/nginx.conf
echo "✅ nginx configured for HTTP + certbot verification"
echo ""

# Step 3: Restart nginx
echo "Step 3: Starting nginx..."
docker compose up -d nginx
sleep 3
echo "✅ nginx running"
echo ""

# Step 4: Get SSL certificate
echo "Step 4: Obtaining SSL certificate from Let's Encrypt..."
echo "This may take a minute..."
docker compose run --rm --entrypoint certbot certbot certonly \
  --webroot \
  --webroot-path=/var/www/certbot \
  -d $DOMAIN \
  --email $EMAIL \
  --agree-tos \
  --no-eff-email \
  --non-interactive

if [ $? -eq 0 ]; then
    echo "✅ Certificate obtained successfully!"
else
    echo "❌ Failed to obtain certificate"
    echo "Check that:"
    echo "  - Your domain DNS points to this server's IP"
    echo "  - Port 80 is open and accessible"
    echo "  - Domain is spelled correctly"
    exit 1
fi
echo ""

# Step 5: Update nginx for HTTPS
echo "Step 5: Configuring nginx for HTTPS..."
cp nginx/nginx.conf.https nginx/nginx.conf
sed -i.bak "s/YOUR_DOMAIN_HERE/$DOMAIN/g" nginx/nginx.conf
echo "✅ nginx configured for HTTPS"
echo ""

# Step 6: Restart nginx
echo "Step 6: Restarting nginx with HTTPS..."
docker compose restart nginx
sleep 2
echo "✅ nginx restarted"
echo ""

# Step 7: Start certbot renewal service
echo "Step 7: Starting certbot auto-renewal..."
docker compose up -d certbot
echo "✅ certbot will auto-renew certificates every 12 hours"
echo ""

echo "======================================"
echo "  ✅ SSL Setup Complete!"
echo "======================================"
echo ""
echo "Your site is now available at:"
echo "  https://$DOMAIN"
echo ""
echo "HTTP traffic will automatically redirect to HTTPS"
echo ""
echo "Test your SSL configuration at:"
echo "  https://www.ssllabs.com/ssltest/analyze.html?d=$DOMAIN"
echo ""
