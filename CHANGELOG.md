# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial release preparation for public repository

## [1.0.0] - 2026-02-01

### Added
- Core freelancer management functionality
- Contract management with milestone tracking
- Multi-currency payment processing
- EU VAT reverse charge mechanism
- Tax treaty support for non-EU countries
- GDPR compliance features
- Withholding tax calculations
- Exchange rate integration (ECB API, Frankfurter API)
- Scheduled tasks for compliance and reporting
- Comprehensive test suite
- Docker-based deployment option
- Employee/Freelancer hybrid worker support

### Features
- **Freelancer DocType**: Extended employee profile for contractors
- **Contract Management**: Fixed price, T&M, and retainer contracts
- **Payment Processing**: Invoice generation with tax calculations
- **Compliance**: VAT, withholding tax, GDPR, tax treaties
- **Multi-currency**: Automatic exchange rate updates
- **Reporting**: Tax summaries, compliance reports, VAT summaries

### Technical
- Python 3.10+ support
- Frappe Framework v15 compatibility
- ERPNext v15 integration
- Standalone tests for core utilities
- Unit tests for constants and currency modules
- CI/CD pipeline with GitHub Actions
- Docker Compose configuration
- Comprehensive documentation

### Documentation
- Installation guide
- Development setup instructions
- Contributing guidelines
- Security policy
- Code of conduct
- API documentation

## [0.9.0] - 2025-12-15 (Beta)

### Added
- Initial beta release for testing
- Basic freelancer and contract management
- Simple payment processing
- EU VAT handling

### Changed
- Migrated from v14 to v15 Frappe framework

### Fixed
- Various bug fixes from internal testing

## [0.1.0] - 2025-10-01 (Alpha)

### Added
- Initial alpha release
- Proof of concept implementation
- Basic freelancer profiles

---

[Unreleased]: https://github.com/YOUR_USERNAME/hrms_freelancer/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/YOUR_USERNAME/hrms_freelancer/releases/tag/v1.0.0
[0.9.0]: https://github.com/YOUR_USERNAME/hrms_freelancer/releases/tag/v0.9.0
[0.1.0]: https://github.com/YOUR_USERNAME/hrms_freelancer/releases/tag/v0.1.0
