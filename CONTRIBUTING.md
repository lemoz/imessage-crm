# Contributing to iMessage CRM

Thank you for your interest in contributing to the iMessage CRM project! This document provides guidelines and information for contributors.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Contributing Guidelines](#contributing-guidelines)
- [Pull Request Process](#pull-request-process)
- [Testing](#testing)
- [Coding Standards](#coding-standards)

## Code of Conduct

This project adheres to a Code of Conduct to ensure a welcoming environment for all contributors. Please read and follow our [Code of Conduct](CODE_OF_CONDUCT.md).

## Getting Started

### Prerequisites

- macOS (required for iMessage integration)
- Python 3.8 or higher
- Full Disk Access permission for your terminal/IDE
- iMessage account configured on your Mac

### Development Setup

1. **Fork and Clone**
   ```bash
   git clone https://github.com/your-username/imessage-crm.git
   cd imessage-crm
   ```

2. **Create Virtual Environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On macOS/Linux
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Environment**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Run Tests**
   ```bash
   python -m pytest tests/
   ```

## Contributing Guidelines

### Types of Contributions

We welcome various types of contributions:

- **Bug Reports**: Help us identify and fix issues
- **Feature Requests**: Suggest new functionality
- **Code Contributions**: Bug fixes, new features, improvements
- **Documentation**: Improve documentation, add examples
- **Testing**: Add test cases, improve test coverage

### Before You Start

1. **Check Existing Issues**: Look for existing issues or discussions
2. **Create an Issue**: For significant changes, create an issue first to discuss
3. **Fork the Repository**: Work on your own fork
4. **Create a Branch**: Use descriptive branch names

### Branch Naming

Use descriptive branch names:
- `feature/add-ai-integration`
- `bugfix/message-parsing-error`
- `docs/update-installation-guide`
- `test/add-contact-manager-tests`

## Pull Request Process

### Before Submitting

1. **Update Documentation**: Ensure documentation reflects your changes
2. **Add Tests**: Include tests for new functionality
3. **Run Tests**: Ensure all tests pass
4. **Code Style**: Follow coding standards
5. **Update Changelog**: Add entry to CHANGELOG.md if applicable

### PR Template

When creating a pull request, include:

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Performance improvement
- [ ] Refactoring

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] All tests pass
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] No new security vulnerabilities
```

### Review Process

1. Automated checks must pass
2. At least one maintainer review required
3. All conversations must be resolved
4. Squash and merge preferred for feature branches

## Testing

### Running Tests

```bash
# Run all tests
python -m pytest

# Run specific test files
python -m pytest tests/unit/test_contact_manager.py

# Run with coverage
python -m pytest --cov=src

# Run integration tests (requires iMessage setup)
python -m pytest tests/integration/
```

### Test Guidelines

- Write tests for all new functionality
- Maintain high test coverage (>80%)
- Use descriptive test names
- Include both positive and negative test cases
- Mock external dependencies appropriately

### Test Structure

```python
def test_specific_functionality_under_specific_conditions():
    """Test description explaining what is being tested."""
    # Arrange
    setup_test_data()
    
    # Act
    result = function_under_test()
    
    # Assert
    assert result == expected_value
```

## Coding Standards

### Python Style

- Follow PEP 8 guidelines
- Use type hints for function signatures
- Maximum line length: 100 characters
- Use meaningful variable and function names

### Code Organization

- Keep functions focused and small
- Use docstrings for all public functions
- Handle errors gracefully with appropriate exceptions
- Log important events and errors

### Documentation

- Document all public APIs
- Include examples in docstrings
- Keep README.md up to date
- Comment complex logic

### Security Considerations

- Never commit sensitive information (API keys, passwords)
- Use environment variables for configuration
- Validate all inputs
- Handle permissions and access controls properly

## Issue Guidelines

### Bug Reports

Include:
- Clear description of the issue
- Steps to reproduce
- Expected vs actual behavior
- Environment information (macOS version, Python version)
- Relevant logs or error messages

### Feature Requests

Include:
- Clear description of the proposed feature
- Use case and rationale
- Potential implementation approach
- Impact on existing functionality

## Getting Help

- **GitHub Issues**: For bug reports and feature requests
- **GitHub Discussions**: For questions and general discussion
- **Documentation**: Check existing documentation first

## Recognition

Contributors will be recognized in:
- CONTRIBUTORS.md file
- Release notes for significant contributions
- GitHub contributor graphs

Thank you for contributing to iMessage CRM!