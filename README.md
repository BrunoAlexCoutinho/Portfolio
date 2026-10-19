# Python Portfolio Projects

Welcome to my code portfolio! This repository serves as a centralized collection of some of my projects.

**Author:** Bruno Coutinho

---

## Repository Architecture

This repository is organized by complexity and topic. Currently, it features core Python fundamentals and automation tools.

### `01-fundamentals`
A collection of standalone Python mini-projects demonstrating core programming concepts, file system operations, and data validation.

| Project | Description | Key Skills Demonstrated |
|---|---|---|
| **`file-organizer`** | An automated script to categorize and sort cluttered directories based on file extensions. | File I/O, `pathlib`, automation |
| **`duplicate-file-finder`** | A tool that scans directories to identify and report duplicate files to free up disk space. | Hashing algorithms, system traversal |
| **`pt-nif-iban-validator`** | A localized utility to validate Portuguese Tax Identification Numbers (NIF) and IBAN formats. | Regex, mathematical checksum validation |

---

## Engineering Best Practices

Every project in this repository is built to professional standards, featuring:
* **Automated Testing:** Comprehensive test suites built with `pytest` located in the `tests/` directory of each project.
* **CI/CD Pipelines:** Automated GitHub Actions workflows (`.github/workflows/`) that run tests on every push to ensure code stability.
* **Isolated Environments:** Configured to run in Python virtual environments using `pip install -e .` for clean dependency management.

---

## How to Run Locally

If you want to pull this code down and run the tests on your own Windows machine, follow these steps using PowerShell:

**1. Clone the repository**
```bash
git clone [https://github.com/BrunoAlexCoutinho/Portfolio.git](https://github.com/BrunoAlexCoutinho/Portfolio.git)
cd Portfolio/01-fundamentals/pt-nif-iban-validator
