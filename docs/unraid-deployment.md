# Deploying Forks on Unraid

## Overview

Forks runs as a single Docker container that bundles the FastAPI backend and Svelte frontend. Recipes are stored as markdown files in a mounted volume, versioned with git. No database required.

**Port:** 8420 (configurable)
**Data:** A single folder of markdown files + images

---

## Option A: Docker Compose (Recommended)

Unraid supports Docker Compose via the **Docker Compose Manager** plugin.

### 1. Install Docker Compose Manager

- Open the Unraid web UI
- Go to **Apps** (Community Applications)
- Search for **Docker Compose Manager** and install it

### 2. Create the recipes directory

Open an Unraid terminal and create a directory for your recipe data:

```bash
mkdir -p /mnt/user/appdata/forks/recipes
```

### 3. Create the compose file

Create `/mnt/user/appdata/forks/docker-compose.yml`:

```yaml
services:
  forks:
    image: ghcr.io/YOUR_USERNAME/forks:latest  # or build from source (see below)
    container_name: forks
    ports:
      - "8420:8000"
    volumes:
      - /mnt/user/appdata/forks/recipes:/data/recipes
    environment:
      - FORKS_RECIPES_DIR=/data/recipes
    restart: unless-stopped
```

> **Building from source** instead of a registry image: clone the repo to your Unraid server and use `build: .` instead of `image:`:
>
> ```yaml
> services:
>   forks:
>     build: /mnt/user/appdata/forks/repo
>     container_name: forks
>     ports:
>       - "8420:8000"
>     volumes:
>       - /mnt/user/appdata/forks/recipes:/data/recipes
>     environment:
>       - FORKS_RECIPES_DIR=/data/recipes
>     restart: unless-stopped
> ```

### 4. Start the container

In Docker Compose Manager, add the compose file and click **Compose Up**, or from the terminal:

```bash
cd /mnt/user/appdata/forks
docker compose up -d
```

### 5. Access Forks

Open your browser to `http://YOUR_UNRAID_IP:8420`

---

## Option B: Manual Docker Run

If you prefer not to use Docker Compose, you can run the container directly.

### 1. Build the image

Clone the repo and build:

```bash
cd /mnt/user/appdata/forks
git clone https://github.com/YOUR_USERNAME/forks.git repo
cd repo
docker build -t forks .
```

### 2. Create the recipes directory

```bash
mkdir -p /mnt/user/appdata/forks/recipes
```

### 3. Run the container

```bash
docker run -d \
  --name forks \
  -p 8420:8000 \
  -v /mnt/user/appdata/forks/recipes:/data/recipes \
  -e FORKS_RECIPES_DIR=/data/recipes \
  --restart unless-stopped \
  forks
```

### 4. Access Forks

Open your browser to `http://YOUR_UNRAID_IP:8420`

---

## Option C: Unraid Docker Template (Community Applications style)

You can also add Forks through the Unraid Docker UI manually:

1. Go to **Docker** tab → **Add Container**
2. Fill in:
   - **Name:** `forks`
   - **Repository:** `forks` (if built locally) or your registry image
   - **Port Mapping:** Host `8420` → Container `8000`
   - **Path Mapping:** Host `/mnt/user/appdata/forks/recipes` → Container `/data/recipes`
   - **Variable:** `FORKS_RECIPES_DIR` = `/data/recipes`
3. Click **Apply**

---

## Git Sync (Optional)

Forks can sync your recipes to a GitHub repository for backup and multi-device access. Configure this in the app's **Settings** page after deployment:

1. Open Forks at `http://YOUR_UNRAID_IP:8420`
2. Go to **Settings**
3. Enter your GitHub repo URL and a personal access token
4. Enable sync

Your recipes will be backed up to GitHub on the configured interval. The git history is stored inside the recipes volume, so all version history persists across container restarts.

---

## Updating

### Docker Compose

```bash
cd /mnt/user/appdata/forks/repo
git pull
cd /mnt/user/appdata/forks
docker compose up -d --build
```

### Manual Docker

```bash
cd /mnt/user/appdata/forks/repo
git pull
docker build -t forks .
docker stop forks && docker rm forks
docker run -d \
  --name forks \
  -p 8420:8000 \
  -v /mnt/user/appdata/forks/recipes:/data/recipes \
  -e FORKS_RECIPES_DIR=/data/recipes \
  --restart unless-stopped \
  forks
```

---

## Backup

Your recipe data lives entirely in `/mnt/user/appdata/forks/recipes`. This directory contains:

- `*.md` — Recipe files (markdown with YAML frontmatter)
- `*.fork.*.md` — Fork files
- `images/` — Uploaded recipe images
- `.git/` — Full version history
- `.forks-config.json` — App settings (sync config, etc.)
- `meal-plans/` — Saved meal plans

To back up, simply include `/mnt/user/appdata/forks/recipes` in your Unraid backup strategy (e.g., Appdata Backup plugin, rsync, or the built-in git sync to GitHub).

---

## Troubleshooting

**Container won't start:**
- Check logs: `docker logs forks`
- Ensure the recipes directory exists and is writable

**Permission issues:**
- Forks runs as root inside the container by default, which matches typical Unraid Docker behavior
- If you see permission errors, check that the host path `/mnt/user/appdata/forks/recipes` is accessible

**Port conflict:**
- Change `8420` to any available port in your compose file or run command
- Only the host port (left side of `:`) needs to change

**Git errors in logs:**
- Forks initializes a git repo in the recipes directory on first startup — this is normal
- If you see "dubious ownership" errors, the container handles this automatically
