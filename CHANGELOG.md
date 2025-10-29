# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.0.2] - 2025-10-29

### Added
- `uv.lock` file for reproducible dependency management
- Improved README with better development setup instructions
- Better error handling in HTTP server

### Changed
- Updated documentation to remove references to non-existent files
- Improved code quality with ruff linting fixes
- Better import ordering across codebase

### Fixed
- Fixed linting issues (E402, W293, B904, SIM102)
- Fixed exception handling to include proper error chaining
- Consolidated nested if statements for cleaner code

## [0.0.1] - 2025-10-26

### Added
- Initial release
- Core `execute_job()` functionality
- HTTP worker with auto-loading
- Multi-turn conversation support
- Text-only agent execution
- Comprehensive test suite
- Example agents (weather, smart-home, customer-support, drive-thru)
