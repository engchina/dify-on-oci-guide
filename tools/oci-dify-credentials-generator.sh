#!/bin/bash

# Check parameters
if [ $# -lt 2 ]; then
    echo "Usage: $0 <profile> <compartment_ocid>"
    echo "Example: $0 DEFAULT ocid1.compartment.oc1..aaaaaaaa"
    exit 1
fi

profile=$1
compartment_ocid=$2
config_file=~/.oci/config

# Check if config file exists
if [ ! -f "$config_file" ]; then
    echo "Error: OCI config file not found: $config_file"
    exit 1
fi

# Read information from the specified profile in the config file
echo "Reading [$profile] configuration from config file..."

# Use awk to extract information for the specified profile
user=$(awk -v profile="[$profile]" '$0 == profile {flag=1; next} /^\[/ {flag=0} flag && /^user=/ {print $0}' "$config_file" | cut -d'=' -f2)
fingerprint=$(awk -v profile="[$profile]" '$0 == profile {flag=1; next} /^\[/ {flag=0} flag && /^fingerprint=/ {print $0}' "$config_file" | cut -d'=' -f2)
tenancy=$(awk -v profile="[$profile]" '$0 == profile {flag=1; next} /^\[/ {flag=0} flag && /^tenancy=/ {print $0}' "$config_file" | cut -d'=' -f2)
region=$(awk -v profile="[$profile]" '$0 == profile {flag=1; next} /^\[/ {flag=0} flag && /^region=/ {print $0}' "$config_file" | cut -d'=' -f2)
pem_file_path=$(awk -v profile="[$profile]" '$0 == profile {flag=1; next} /^\[/ {flag=0} flag && /^key_file=/ {print $0}' "$config_file" | cut -d'=' -f2)

# Check if all required information was successfully read
if [ -z "$user" ] || [ -z "$fingerprint" ] || [ -z "$tenancy" ] || [ -z "$region" ] || [ -z "$pem_file_path" ]; then
    echo "Error: Could not read complete configuration from config file"
    echo "Please ensure [$profile] configuration includes user, fingerprint, tenancy, region and key_file"
    exit 1
fi

# Display the read information
echo "Configuration loaded:"
echo "User OCID: $user"
echo "Fingerprint: $fingerprint"
echo "Tenancy OCID: $tenancy"
echo "Region: $region"
echo "PEM file path: $pem_file_path"
echo "Compartment OCID: $compartment_ocid"

# Create combined string
combined_string="$user/$fingerprint/$tenancy/$region/$compartment_ocid"

# Base64 encode the combined string
encoded_combined_string=$(echo -n "$combined_string" | base64 --wrap=0)

# Display results
echo
echo "[Dify: oci api key config file's content]"
echo "$encoded_combined_string"

# Check if PEM file exists
if [ ! -f "$pem_file_path" ]; then
    echo "Error: PEM file not found: $pem_file_path"
    exit 1
fi

# Base64 encode the PEM file content
encoded_pem_content=$(base64 --wrap=0 "$pem_file_path")

# Display results
echo
echo "[Dify: oci api key file's content]"
echo "$encoded_pem_content"