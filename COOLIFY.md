# Coolify Deployment

This repository is best deployed in Coolify as a small static site, not as an application backend.

## Use In Coolify

- Resource type: `Docker Compose`
- Compose file: `docker-compose.coolify.yml`
- Public service: `app`
- Public port inside the container: `80`

Coolify should expose the `app` service through its normal HTTP/HTTPS proxy. No host `ports:` mapping is needed in the compose file.

## What Gets Deployed

- A static landing page at `/`
- Raw project files for convenience:
  - `/README.md`
  - `/LICENSE`
  - `/install.sh`
  - `/assets/header.jpeg`

## Environment Variables

No environment variables are required for this deployment.

The repository's real functionality still happens on the user's machine after cloning the project and running `./install.sh`.

## Persistence

No persistent volume is needed.

This deployment is stateless.

## Important Caveat

This project does not include a long-running API, worker, or web application. The Coolify deployment created here is intentionally a documentation/download surface for the repository, not the council runtime itself.

If you want a browser-based council product later, that would be a separate application project with its own runtime, authentication, and provider-key handling.
