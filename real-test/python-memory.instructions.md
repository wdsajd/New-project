---
name: python-memory
description: Python programming memories and lessons learned
---

# Python Programming Memories

## Memory 1: Virtual Environments
Always use virtual environments for Python projects. Key commands:
- `python -m venv venv` - Create virtual environment
- `venv\Scripts\activate` - Activate on Windows
- `source venv/bin/activate` - Activate on Mac/Linux

## Memory 2: Package Management
Use `requirements.txt` for dependencies:
- `pip freeze > requirements.txt` - Export dependencies
- `pip install -r requirements.txt` - Install dependencies
- Use `pip-tools` for complex dependency management

## Memory 3: Code Style
Follow PEP 8 guidelines:
- 4 spaces per indentation level
- Maximum line length of 79 characters
- Use descriptive variable names
- Import statements at the top of the file

## Memory 4: Error Handling
Use try-except blocks properly:
- Catch specific exceptions, not bare `except:`
- Log errors with context information
- Clean up resources in `finally` blocks
- Use custom exception classes for domain errors