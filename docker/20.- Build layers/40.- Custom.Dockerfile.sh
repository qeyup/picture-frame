#!/bin/bash

# Install apt packages
PACKAGES=()
PACKAGES+=(vim)
PACKAGES+=(bash-completion)
PACKAGES+=(tree)
PACKAGES+=(net-tools)
apt update
apt install -y ${PACKAGES[@]}

