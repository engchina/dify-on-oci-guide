# Dify on OCI Deployment Guide

This repository provides comprehensive guidance and tools for deploying [Dify](https://github.com/langgenius/dify) on Oracle Cloud Infrastructure (OCI).

## Repository Structure

- **docs/** - Documentation and guides including installation steps, configuration instructions, and best practices
- **scripts/** - Automation scripts for deployment and environment setup
- **tools/** - Utility tools including OCI credential generators
- **templates/** - Configuration templates and example files for quick setup
- **resources/** - Resource files such as screenshots, diagrams, and reference materials

## Getting Started

1. Review the documentation in the `docs/` directory
2. Use the credential generator in `tools/` to set up your OCI authentication:
   ```bash
   cd tools
   ./oci-dify-credentials-generator.sh DEFAULT ocid1.compartment.oc1..aaaaaaaa
```
3. Refer to the templates in `templates/` for configuration examples
4. Follow the deployment scripts in `scripts/` to set up your Dify instance

## Prerequisites

- Oracle Cloud Infrastructure account
- Basic knowledge of cloud infrastructure and containerization
- Familiarity with Dify application requirements

## Contributing

Contributions to improve this guide are welcome. Please feel free to submit pull requests or open issues for any improvements or suggestions.

## License

[Apache License 2.0](LICENSE)
