# Dify on OCI Tools

This directory contains utility tools for setting up and managing Dify on Oracle Cloud Infrastructure.

## OCI Credentials Generator

The `oci-dify-credentials-generator.sh` script helps generate the necessary credentials for Dify to interact with OCI services.

### Prerequisites

- OCI CLI installed and configured
- Valid OCI configuration in `~/.oci/config`
- Bash shell environment

### Usage

```bash
./oci-dify-credentials-generator.sh <profile> <compartment_ocid>