# Security Policy

## Supported Versions

We provide security updates for the following versions of iMessage CRM:

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

We take security seriously. If you discover a security vulnerability in iMessage CRM, please report it privately.

### How to Report

1. **DO NOT** create a public issue for security vulnerabilities
2. **Email us directly** at: security@your-domain.com (replace with actual email)
3. **Use GitHub Security Advisories** (preferred): https://github.com/yourusername/imessage-crm/security/advisories

### What to Include

Please include the following information in your report:

- **Description** of the vulnerability
- **Steps to reproduce** the issue
- **Potential impact** of the vulnerability
- **Suggested fix** (if you have one)
- **Your contact information** for follow-up

### Response Timeline

We will acknowledge receipt of your vulnerability report within **48 hours** and will send a more detailed response within **5 business days** indicating the next steps in handling your report.

### Security Update Process

1. **Confirmation**: We'll confirm the vulnerability and determine its impact
2. **Fix Development**: We'll develop a fix and create a security patch
3. **Testing**: Thorough testing of the security fix
4. **Release**: Security update release with appropriate versioning
5. **Disclosure**: Public disclosure after users have had time to update

## Security Considerations

### Data Privacy

iMessage CRM accesses sensitive personal data from your iMessage conversations. Please be aware:

- **Local Data**: All data processing happens locally on your Mac
- **API Keys**: Store API keys securely using environment variables
- **Database Access**: Requires Full Disk Access permission
- **Message Content**: Never transmit message content to external services without explicit consent

### Permissions

This application requires:

- **Full Disk Access**: To read the iMessage database
- **AppleScript Access**: To send messages through Messages app
- **Network Access**: For optional AI features (OpenAI integration)

### Best Practices

1. **Review permissions** before granting Full Disk Access
2. **Use environment variables** for sensitive configuration
3. **Keep dependencies updated** regularly
4. **Audit API usage** if using external services
5. **Backup your data** before running migrations or updates

### Known Security Limitations

- This tool requires elevated macOS permissions
- iMessage database access could potentially be misused
- External API integrations may transmit data outside your device

## Responsible Disclosure

We follow the principle of responsible disclosure:

- We will work with you to resolve the issue
- We will credit you for the discovery (unless you prefer to remain anonymous)
- We will not take legal action against researchers who follow responsible disclosure

## Contact

For security-related questions or concerns, please contact:
- Email: security@your-domain.com
- GitHub: Create a private security advisory

Thank you for helping keep iMessage CRM and our users safe!