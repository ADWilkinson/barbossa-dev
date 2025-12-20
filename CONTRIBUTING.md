# Contributing to Barbossa

Thanks for your interest in contributing to Barbossa! This document outlines how to get started.

## Getting Started

1. Fork the repository
2. Clone your fork locally
3. Set up the development environment (see README.md)
4. Create a feature branch: `git checkout -b feature/your-feature`

## Development Setup

```bash
# Clone your fork
git clone https://github.com/your-username/barbossa.git
cd barbossa

# Copy example config
cp config/barbossa.example.json config/repositories.json

# Set up environment
cp .env.example .env
# Edit .env with your settings

# Run locally (without Docker)
python3 barbossa_engineer.py --help
```

## Making Changes

1. Make your changes in a feature branch
2. Test your changes locally
3. Ensure code follows existing patterns
4. Update documentation if needed

## Submitting a Pull Request

1. Push to your fork
2. Open a PR against the `main` branch
3. Describe what your change does and why
4. Link any related issues

## Code Style

- Follow existing patterns in the codebase
- Use meaningful variable and function names
- Add comments for complex logic
- Keep functions focused and reasonably sized

## Areas for Contribution

- Bug fixes
- Documentation improvements
- New agent features
- Integration improvements
- Test coverage
- Performance optimizations

## Reporting Issues

When reporting issues, please include:

- Steps to reproduce
- Expected vs actual behavior
- Relevant logs or error messages
- Your environment (OS, Python version, Docker version)

## Questions?

Open a GitHub Discussion for questions or ideas.

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
