# Nginx Setup for Knowledger

## What Changed

1. **Created nginx configuration** in `nginx/nginx.conf`
   - Listens on port 80
   - Forwards all requests to web-ui container on port 8000
   - Includes gzip compression, logging, and proper headers

2. **Updated docker-compose.yml**
   - Changed web-ui from `ports: 8000:8000` to `expose: 8000` (only internal)
   - Added nginx service that maps port 80 to host

## Deploy to Server

```bash
# 1. Copy files to server
scp nginx/nginx.conf deploy@YOUR_SERVER_IP:~/knowledger/nginx/
scp docker-compose.yml deploy@YOUR_SERVER_IP:~/knowledger/

# 2. SSH into server
ssh deploy@YOUR_SERVER_IP

# 3. Navigate to project
cd ~/knowledger

# 4. Stop current services
docker compose down

# 5. Start with nginx
docker compose up -d

# 6. Check everything is running
docker compose ps

# 7. Check nginx logs if issues
docker compose logs nginx
```

## Firewall Update

```bash
# Allow port 80
sudo ufw allow 80/tcp

# Optional: Remove port 8000 if you want
sudo ufw delete allow 8000/tcp
```

## Test

After DNS propagates:
- `http://yourdomain.com` (no port needed!)
- `http://YOUR_SERVER_IP` (also works)

## Next Steps

Once domain works:
1. Update `server_name _;` in nginx.conf to `server_name yourdomain.com;`
2. Set up SSL with Let's Encrypt (I can help with this)
