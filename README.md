# Desiree's Test Project

A Python project for testing Slack/GitHub repository integration and stale PR notifications.

## Project Structure

```
desireestest/
├── src/           # Main application source code
│   ├── __init__.py
│   └── main.py    # Hello world application
├── backend/       # Backend services and API
│   ├── __init__.py
│   └── api.py
├── frontend/      # Frontend views and templates
│   ├── __init__.py
│   └── views.py
├── utils/         # Shared utility functions
│   ├── __init__.py
│   └── helpers.py
├── .gitignore     # Python gitignore
├── requirements.txt
└── README.md
```

## Getting Started

### Prerequisites

- Python 3.8 or higher

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/desi-rayray/desireestest.git
   cd desireestest
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Running the Application

```bash
python src/main.py
```

## Purpose

This repository is designed to:
- Test Slack/GitHub repository integration
- Create multiple pull requests for testing stale PR notifications
- Demonstrate CODEOWNERS functionality with multiple directories
# Test Feature for Stale PR Notifications

This PR is created to test the stale PR notification workflow.
It will become stale after the configured STALE_HOURS period.
