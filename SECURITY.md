# Security Policy

## Supported Versions

We release patches for security vulnerabilities in the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |

## Reporting a Vulnerability

If you discover a security vulnerability within HRMS Freelancer, please send an email to security@example.com. All security vulnerabilities will be promptly addressed.

**Please do not report security vulnerabilities through public GitHub issues.**

## Security Considerations

### Environment Variables

Never commit sensitive information to the repository:
- Database passwords
- API keys
- Secret keys
- Email credentials

Use the `.env.example` file as a template and create your own `.env` file locally.

### Docker Defaults

The default `docker-compose.yml` uses simple passwords for development purposes. **Always change these in production**:
- Database root password
- Admin password
- Redis configuration

### Data Protection

This application handles personal data and must comply with:
- GDPR for EU residents
- Local data protection laws
- Industry-specific regulations

Ensure proper:
- Data encryption at rest and in transit
- Access control and authentication
- Regular security audits
- Backup procedures

### Production Deployment

For production environments:
1. Use strong, unique passwords
2. Enable SSL/TLS encryption
3. Configure firewall rules
4. Regularly update dependencies
5. Implement monitoring and logging
6. Follow Frappe/ERPNext security best practices

## Third-Party Dependencies

We regularly update dependencies to address security vulnerabilities. Review the `requirements.txt` file and keep packages up to date.

## Secure Configuration

See our [deployment documentation](docs/DEPLOYMENT.md) for secure configuration guidelines.
