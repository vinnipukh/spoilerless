<!-- generated-by: gsd-doc-writer -->
# Contributing to Spoilerless

Thank you for your interest in contributing to Spoilerless!

## Code of Conduct
Please ensure that all interactions within the community are respectful and constructive.

## Issue Reporting
If you find a bug or have a feature request, please open an issue on GitHub. Include as much relevant information as possible, such as:
- A clear description of the issue or feature.
- Steps to reproduce (for bugs).
- Expected vs. actual behavior.
- Relevant logs or error messages.

## Development Setup
For full instructions on setting up your local environment, please refer to our [README.md](README.md) and [docs/CONFIGURATION.md](docs/CONFIGURATION.md). 

A brief overview:
- **Backend**: Uses Python 3.13 and `uv`. Run `uv sync` to install dependencies and `uv run pytest` for testing.
- **Frontend**: Uses Node.js. Navigate to the `frontend/` directory, run `npm ci` to install dependencies, and `npm run dev` to start the development server.
- **Database**: Uses Neo4j. A `docker-compose.yml` is provided in the project root to spin up the required services.

## Coding Standards
- **Backend (Python)**: Ensure your code works with Python 3.13. Write tests for new functionality and ensure `uv run pytest` passes.
- **Frontend (TypeScript/React)**: Follow the existing formatting. Ensure your code passes linting (`npm run lint`) and builds successfully (`npm run build`).

## Pull Request Guidelines
1. Fork the repository and create your branch from `main`.
2. Ensure you have added or updated tests as appropriate.
3. Verify that all CI checks pass. The `.github/workflows/ci.yml` pipeline will run automatically on pull requests.
   - This includes backend tests and frontend linting/builds.
4. Submit your pull request with a clear title and description of your changes.

We look forward to your contributions!
