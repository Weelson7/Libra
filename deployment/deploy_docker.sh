#!/bin/bash
# Libra deployment script for Docker
set -e

docker build -t libra-app .
echo "Libra Docker image built as libra-app. Use ./run_docker.sh to start a container."
