# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Web Dashboard with modern UI for conversation management
- AI-powered conversation analysis using OpenAI GPT models
- Smart Message Starters feature with contextual generation
- Goal-driven message generation (respond to messages, check-in, plan events)
- Rich attachment information display with type detection
- Contact name resolution from macOS Contacts database
- Dynamic message limit configuration (500-2000+ messages)
- Conversation caching for improved performance
- Previous starter avoidance to ensure fresh suggestions
- Real-time message viewing with attachment metadata

### Changed
- Replaced hardcoded templates with full LLM-based generation
- Enhanced conversation analysis to include attachment context
- Improved contact resolution with multi-database search
- Updated API to include attachment information in responses

### Performance
- Implemented singleton pattern for ContactManager
- Added aggressive caching for macOS contact lookups
- Optimized database queries with pattern matching

### Security
- Environment variable configuration for sensitive data
- Proper permission handling for macOS Full Disk Access
- Input validation and sanitization
- Secure database connection management
- Removed all hardcoded test data from source code

## [0.1.0] - 2025-06-05

### Added
- Initial MVP release
- Core iMessage CRM functionality
- Basic contact and message management
- Documentation and open source preparation

[Unreleased]: https://github.com/yourusername/imessage-crm/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/yourusername/imessage-crm/releases/tag/v0.1.0