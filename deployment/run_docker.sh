#!/bin/bash
# Run Libra in Docker

docker run --rm -it -v $(pwd)/data:/app/data -v $(pwd)/logs:/app/logs libra-app
