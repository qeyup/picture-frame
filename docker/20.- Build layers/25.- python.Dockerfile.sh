#!/bin/bash
set -e


# Upgrade system
PACKAGES=()
PACKAGES+=(d2dcn)


# Install all
pip3 install ${PACKAGES[@]}


# Packages from apt repo
PACKAGES=()
PACKAGES+=(python3-pyqt5)


# Install all
apt install -y ${PACKAGES[@]}