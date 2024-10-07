# Directory Logger

Directory Logger is a powerful and flexible tool for generating detailed logs of directory structures and file metadata. It offers both a command-line interface and a graphical user interface, making it suitable for various use cases and user preferences.

## Features

- Log directory structures with detailed file metadata
- Filter files by extension
- Control logging depth
- Multiple output formats (text, JSON, CSV, XML)
- Concurrent processing for improved performance
- Progress tracking
- Configurable logging
- User-friendly GUI with dark mode
- Save and load configurations

## Installation

1. Clone the repository:

   ```sh
   git clone https://github.com/Xza85hrf/Directory-Logger.git
   cd directory-logger
   ```

2. Create a virtual environment (optional but recommended):

   ```sh
   python -m venv venv
   source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
   ```

3. Install the required packages:

   ```sh
   pip install -r requirements.txt
   ```

## Usage

### Command-line Interface

Run the directory logger from the command line:

```sh
python dir_log_gen.py /path/to/directory /path/to/logfile.txt [options]
```

Options:

- `--extension`: Filter files by extension (e.g., .txt)
- `--max-depth`: Maximum depth of directory traversal
- `--format`: Output format (text, json, csv, xml)
- `--console`: Print log to console
- `--verbose`: Enable verbose mode
- `--config`: Path to configuration file

### Graphical User Interface

Launch the GUI application:

```sh
python dir_log_gui.py
```

The GUI provides an intuitive interface for setting up and running the directory logger.

## Configuration

You can save and load configurations using the GUI. Configurations are stored in JSON format and include:

- Directory path
- Log file path
- File extension filter
- Maximum depth
- Output format

## Development

### Running Tests

Run the unit tests using:

```sh
python -m unittest dir_log_utests.py
```

### Code Style

This project follows the PEP 8 style guide. Use `black` for code formatting and `flake8` for linting:

```sh
black .
flake8
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
