# Big Kernel Manager

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.6+-green.svg)
![GTK](https://img.shields.io/badge/GTK-4.0-orange.svg)

A modern, user-friendly application for managing Linux kernels and Mesa drivers on BigLinux (and other Arch-based distributions).

## Features

- 🐧 **Kernel Management**
  - View installed and available kernels
  - Install new kernels with one click
  - Remove unused kernels safely
  - Automatic LTS kernel detection
  - Support for RT (Real-Time) and Xanmod kernels

- 🎮 **Mesa Driver Management**
  - Switch between stable, git, and amber Mesa drivers
  - Visual indication of active driver
  - Safe driver switching with confirmation dialogs

- 🎨 **Modern UI**
  - Built with GTK4 and Libadwaita
  - Dark mode support
  - Responsive design
  - Real-time progress feedback

## Screenshots

*Coming soon*

## Installation

### BigLinux (Recommended)

```bash
# Available in BigLinux repositories
sudo pacman -S big-kernel-manager
```

### Manual Installation

```bash
# Clone the repository
git clone https://github.com/communitybig/big-kernel-manager.git
cd big-kernel-manager

# Install dependencies
sudo pacman -S python python-gobject python-requests gtk4 libadwaita polkit

# Run directly
python usr/share/big-kernel-manager/main.py
```

### Building from PKGBUILD

```bash
cd pkgbuild
makepkg -si
```

## Usage

Launch the application from your application menu or run:

```bash
big-kernel-manager
```

### First Launch

On first launch, you'll see an informational dialog about kernel and Mesa management best practices. Key points:

- **Always keep at least one working kernel** as a fallback
- **LTS kernels** are recommended for stability
- **Test your system** after kernel changes
- **Backup your system** before major changes

## Architecture

```
usr/share/big-kernel-manager/
├── main.py              # Application entry point
├── core/                # Core functionality
│   ├── constants.py     # Application constants
│   ├── exceptions.py    # Custom exceptions
│   ├── logging_config.py # Logging configuration
│   ├── base_manager.py  # Base manager class
│   ├── kernel_manager.py # Kernel operations
│   ├── mesa_manager.py  # Mesa operations
│   └── package_manager.py # Pacman interface
├── ui/                  # User interface
│   ├── application.py   # Main application class
│   ├── window.py        # Main window
│   ├── base_page.py     # Base page class
│   ├── kernel_page.py   # Kernel management UI
│   └── mesa_page.py     # Mesa management UI
└── assets/
    └── css/
        └── style.css    # Custom styling
```

## Development

### Requirements

- Python 3.6+
- GTK 4.0
- Libadwaita 1.0
- PyGObject

### Running Tests

```bash
# Install pytest
pip install pytest

# Run tests
pytest tests/ -v
```

### Code Quality

The project uses:
- Structured logging
- Custom exception classes
- Type hints
- Comprehensive docstrings

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- BigLinux Team
- Manjaro Linux (original kernel manager inspiration)
- GTK/GNOME Team for GTK4 and Libadwaita
