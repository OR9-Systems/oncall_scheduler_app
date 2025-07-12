# Oncall Scheduler App
## Overview

This repository contains a web application designed to be deployed using Docker and Docker Compose. The application is a Flask-based web service and uses PostgreSQL for its database. This README provides instructions for deploying the application with Docker Compose and securely managing secrets using Docker secrets.
Prerequisites
Test
- Docker
- Docker Compose

## Secrets Configuration

1. **Create Docker Secrets**
Docker secrets are used to manage sensitive information securely. Follow these steps to set up your secrets:

```bash
echo "your_db_user" | docker secret create db_user -
echo "your_db_password" | docker secret create db_password -
echo "your_db_name" | docker secret create db_name -
```


2. **Verify Secrets**

To ensure that the secrets were created successfully, you can list them using:

```bash
docker secret ls
```

3. **Running the App in Docker**

To start the app have docker running and run the command

```bash
docker-compose up -d --build
```




