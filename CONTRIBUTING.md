# Contributing to HRMS Freelancer

Thank you for your interest in contributing to HRMS Freelancer! This document provides guidelines for contributing to the project.

## Code of Conduct

Be respectful, inclusive, and professional in all interactions.

## How to Contribute

### Reporting Bugs

- Check existing issues first
- Use the bug report template
- Include detailed steps to reproduce
- Provide system information (OS, Python version, Frappe version)

### Suggesting Enhancements

- Check existing feature requests
- Clearly describe the use case
- Explain expected behavior vs current behavior

### Pull Requests

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests if applicable
5. Ensure all tests pass
6. Update documentation
7. Commit your changes (`git commit -m 'Add amazing feature'`)
8. Push to your branch (`git push origin feature/amazing-feature`)
9. Open a Pull Request

## Development Setup

See [RUNNING_LOCALLY.md](RUNNING_LOCALLY.md) for detailed setup instructions.

### Quick Start

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/hrms_freelancer.git
cd hrms_freelancer

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run tests
python test_standalone_v2.py
pytest
```

## Coding Standards

### Python

- Follow PEP 8 style guide
- Use meaningful variable names
- Add docstrings to functions and classes
- Keep functions focused and small
- Maximum line length: 100 characters

### JavaScript

- Use ES6+ features
- Follow Frappe's JS conventions
- Add JSDoc comments

### Commits

- Use clear, descriptive commit messages
- Start with a verb (Add, Fix, Update, Remove)
- Reference issue numbers when applicable
- Keep commits atomic and focused

Example:
```
Fix VAT calculation for cross-border EU transactions (#123)

- Correct reverse charge logic for B2B services
- Add validation for VAT numbers
- Update tests for edge cases
```

## Testing

- Add unit tests for new features
- Ensure existing tests pass
- Test manually in development environment
- Include test data when relevant

## Documentation

- Update README.md for user-facing changes
- Add docstrings for new functions/classes
- Update inline comments for complex logic
- Create/update documentation files as needed

## Review Process

1. Maintainers will review your PR
2. Address any requested changes
3. Once approved, your PR will be merged
4. Your contribution will be credited

## Questions?

Open an issue with the "question" label or join our community discussions.

## License

By contributing, you agree that your contributions will be licensed under the project's license.
