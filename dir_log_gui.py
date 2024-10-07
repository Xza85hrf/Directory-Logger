import sys
import os
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLineEdit,
    QLabel,
    QFileDialog,
    QComboBox,
    QSpinBox,
    QTextEdit,
    QProgressBar,
    QMessageBox,
    QGroupBox,
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QFont, QColor, QPalette

import logging
from pathlib import Path
from typing import Optional
import json

# Import the existing directory logger class
from dir_log_gen import DirectoryLogger, DirectoryLoggerError


class LoggerThread(QThread):
    """
    A QThread subclass for running the directory logging process in the background.
    This allows the GUI to remain responsive during logging operations.
    """

    update_signal = Signal(str)
    progress_signal = Signal(float)
    finished_signal = Signal()

    def __init__(self, logger: DirectoryLogger):
        super().__init__()
        self.logger = logger

    def run(self):
        """
        Execute the logging process and emit signals for updates and completion.
        """
        try:
            self.logger.log_directory_with_metadata()
            self.update_signal.emit(
                f"Logging complete. Output saved to {self.logger.log_file}"
            )
        except DirectoryLoggerError as e:
            self.update_signal.emit(f"Logging stopped: {str(e)}")
        except Exception as e:
            self.update_signal.emit(f"An error occurred: {str(e)}")
        finally:
            self.finished_signal.emit()


class LogHandler(logging.Handler):
    """
    Custom logging handler that emits log messages through a Qt signal.
    This allows log messages to be displayed in the GUI.
    """

    def __init__(self, signal):
        super().__init__()
        self.signal = signal

    def emit(self, record):
        msg = self.format(record)
        self.signal.emit(msg)


class MainWindow(QMainWindow):
    """
    The main window of the Directory Logger GUI application.
    This class sets up the user interface and handles user interactions.
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Directory Logger")
        self.setGeometry(100, 100, 800, 600)
        self.setStyleSheet(
            """
            QMainWindow, QWidget {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #555555;
                border-radius: 5px;
                margin-top: 10px;
                color: #ffffff;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px 0 3px;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 5px 10px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #555555;
            }
            QLineEdit, QComboBox, QSpinBox {
                background-color: #3a3a3a;
                color: #ffffff;
                padding: 5px;
                border: 1px solid #555555;
                border-radius: 3px;
            }
            QLabel {
                color: #ffffff;
            }
            QTextEdit {
                background-color: #1e1e1e;
                color: #ffffff;
                border: 1px solid #555555;
            }
            QProgressBar {
                border: 1px solid #555555;
                border-radius: 3px;
                background-color: #3a3a3a;
                color: #ffffff;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                width: 10px;
                margin: 0.5px;
            }
        """
        )

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Input Group
        input_group = QGroupBox("Input Settings")
        input_layout = QVBoxLayout(input_group)

        # Directory selection
        dir_layout = QHBoxLayout()
        self.dir_input = QLineEdit()
        self.dir_input.setPlaceholderText("Select a directory to log")
        dir_button = QPushButton("Browse")
        dir_button.clicked.connect(self.select_directory)
        dir_layout.addWidget(QLabel("Directory:"))
        dir_layout.addWidget(self.dir_input)
        dir_layout.addWidget(dir_button)
        input_layout.addLayout(dir_layout)

        # Log file selection
        log_layout = QHBoxLayout()
        self.log_input = QLineEdit()
        self.log_input.setPlaceholderText("Choose a location for the log file")
        log_button = QPushButton("Browse")
        log_button.clicked.connect(self.select_log_file)
        log_layout.addWidget(QLabel("Log File:"))
        log_layout.addWidget(self.log_input)
        log_layout.addWidget(log_button)
        input_layout.addLayout(log_layout)

        main_layout.addWidget(input_group)

        # Options Group
        options_group = QGroupBox("Logging Options")
        options_layout = QVBoxLayout(options_group)

        # File extension
        extension_layout = QHBoxLayout()
        self.extension_input = QLineEdit()
        self.extension_input.setPlaceholderText("e.g., .txt, .py")
        extension_layout.addWidget(QLabel("File Extension:"))
        extension_layout.addWidget(self.extension_input)
        options_layout.addLayout(extension_layout)

        # Max depth
        depth_layout = QVBoxLayout()  # Changed to QVBoxLayout for better organization
        depth_input_layout = QHBoxLayout()
        self.max_depth_input = QSpinBox()
        self.max_depth_input.setSpecialValueText("No limit")
        self.max_depth_input.setRange(0, 999)
        depth_input_layout.addWidget(QLabel("Max Depth:"))
        depth_input_layout.addWidget(self.max_depth_input)
        depth_layout.addLayout(depth_input_layout)

        # Add detailed instructions for max depth
        max_depth_instructions = QLabel(
            "Max Depth determines how deep the logger will traverse into subdirectories:\n"
            "• 0 (No limit): Log all subdirectories, regardless of depth\n"
            "• 1: Log only the specified directory and its immediate subdirectories\n"
            "• 2+: Log up to the specified level of subdirectories\n"
            "Use this to control the scope of your directory logging."
        )
        max_depth_instructions.setWordWrap(True)
        max_depth_instructions.setStyleSheet("font-size: 10pt; color: #a0a0a0;")
        depth_layout.addWidget(max_depth_instructions)

        options_layout.addLayout(depth_layout)

        # Output format
        format_layout = QHBoxLayout()
        self.format_combo = QComboBox()
        self.format_combo.addItems(["text", "json", "csv", "xml"])
        format_layout.addWidget(QLabel("Output Format:"))
        format_layout.addWidget(self.format_combo)
        options_layout.addLayout(format_layout)

        main_layout.addWidget(options_group)

        # Control Group
        control_group = QGroupBox("Control")
        control_layout = QHBoxLayout(control_group)

        self.run_button = QPushButton("Run Logger")
        self.run_button.clicked.connect(self.run_logger)
        self.stop_button = QPushButton("Stop")
        self.stop_button.clicked.connect(self.stop_logger)
        self.stop_button.setEnabled(False)
        control_layout.addWidget(self.run_button)
        control_layout.addWidget(self.stop_button)

        main_layout.addWidget(control_group)

        # Progress bar
        self.progress_bar = QProgressBar()
        main_layout.addWidget(self.progress_bar)

        # Output area
        output_group = QGroupBox("Output")
        output_layout = QVBoxLayout(output_group)
        self.output_area = QTextEdit()
        self.output_area.setReadOnly(True)
        output_layout.addWidget(self.output_area)
        main_layout.addWidget(output_group)

        # Configuration Group
        config_group = QGroupBox("Configuration")
        config_layout = QHBoxLayout(config_group)
        save_config_button = QPushButton("Save Configuration")
        save_config_button.clicked.connect(self.save_configuration)
        load_config_button = QPushButton("Load Configuration")
        load_config_button.clicked.connect(self.load_configuration)
        config_layout.addWidget(save_config_button)
        config_layout.addWidget(load_config_button)
        main_layout.addWidget(config_group)

        # Set up logging
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s - %(levelname)s - %(message)s",
            filename="directory_log.log",
            filemode="a",
        )
        log_handler = LogHandler(self.update_output)
        logging.getLogger().addHandler(log_handler)

        logging.info("GUI application started")

        self.logger = None
        self.logger_thread = None

        # Add tooltips
        self.add_tooltips()

    def add_tooltips(self):
        """
        Add tooltips to various UI elements to provide additional information to the user.
        """
        self.dir_input.setToolTip("Select the directory you want to log")
        self.log_input.setToolTip("Choose where to save the log file")
        self.extension_input.setToolTip(
            "Optionally filter files by extension (e.g., .txt)"
        )
        self.max_depth_input.setToolTip(
            "Set the maximum depth for directory traversal:\n"
            "0 (No limit) - Log all subdirectories\n"
            "1 - Log only immediate subdirectories\n"
            "2+ - Log up to the specified level of subdirectories"
        )
        self.format_combo.setToolTip("Choose the output format for the log file")
        self.run_button.setToolTip("Start the logging process")
        self.stop_button.setToolTip("Stop the current logging process")

    def select_directory(self):
        """
        Open a file dialog for the user to select a directory to log.
        """
        directory = QFileDialog.getExistingDirectory(self, "Select Directory")
        if directory:
            self.dir_input.setText(directory)

    def select_log_file(self):
        """
        Open a file dialog for the user to select a location to save the log file.
        """
        file_name, _ = QFileDialog.getSaveFileName(self, "Select Log File")
        if file_name:
            self.log_input.setText(file_name)

    def run_logger(self):
        """
        Start the logging process based on the user's input and settings.
        """
        path = self.dir_input.text()
        log_file = self.log_input.text()
        file_extension = self.extension_input.text() or None
        max_depth = self.max_depth_input.value() or None
        output_format = self.format_combo.currentText()

        if not path or not log_file:
            QMessageBox.warning(
                self, "Input Error", "Please select both directory and log file."
            )
            return

        self.run_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.output_area.clear()
        self.progress_bar.setValue(0)
        self.update_output("Starting logging process...")

        logging.info(f"Starting logging process for directory: {path}")

        self.logger = DirectoryLogger(
            path, log_file, file_extension, max_depth, output_format, False, True
        )
        self.logger_thread = LoggerThread(self.logger)
        self.logger_thread.update_signal.connect(self.update_output)
        self.logger_thread.progress_signal.connect(self.update_progress)
        self.logger_thread.finished_signal.connect(self.on_logging_finished)
        self.logger_thread.start()

        # Start a timer to update progress
        self.progress_timer = QTimer(self)
        self.progress_timer.timeout.connect(self.update_progress)
        self.progress_timer.start(100)  # Update every 100ms

    def stop_logger(self):
        """
        Stop the ongoing logging process.
        """
        if self.logger:
            self.logger.stop()
        logging.info("Stopping logging process")
        self.update_output("Stopping logging process...")
        self.stop_button.setEnabled(False)

    def update_output(self, message):
        """
        Update the output text area with a new message.
        """
        self.output_area.append(message)
        logging.debug(f"GUI output: {message}")

    def update_progress(self):
        """
        Update the progress bar based on the current logging progress.
        """
        if self.logger:
            progress = self.logger.get_progress()
            self.progress_bar.setValue(int(progress))

    def on_logging_finished(self):
        """
        Handle the completion of the logging process.
        """
        self.run_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.progress_timer.stop()
        self.progress_bar.setValue(100)

    def save_configuration(self):
        """
        Save the current configuration to a JSON file.
        """
        file_name, _ = QFileDialog.getSaveFileName(
            self, "Save Configuration", "", "JSON Files (*.json)"
        )
        if file_name:
            config = {
                "directory": self.dir_input.text(),
                "logfile": self.log_input.text(),
                "extension": self.extension_input.text(),
                "max_depth": self.max_depth_input.value(),
                "format": self.format_combo.currentText(),
            }
            with open(file_name, "w") as f:
                json.dump(config, f, indent=4)
            self.update_output(f"Configuration saved to {file_name}")
            logging.info(f"Configuration saved to {file_name}")

    def load_configuration(self):
        """
        Load a configuration from a JSON file and update the UI accordingly.
        """
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Load Configuration", "", "JSON Files (*.json)"
        )
        if file_name:
            try:
                with open(file_name, "r") as f:
                    config = json.load(f)
                self.dir_input.setText(config.get("directory", ""))
                self.log_input.setText(config.get("logfile", ""))
                self.extension_input.setText(config.get("extension", ""))
                self.max_depth_input.setValue(config.get("max_depth", 0))
                self.format_combo.setCurrentText(config.get("format", "text"))
                self.update_output(f"Configuration loaded from {file_name}")
                logging.info(f"Configuration loaded from {file_name}")
            except Exception as e:
                QMessageBox.warning(
                    self, "Error", f"Error loading configuration: {str(e)}"
                )


if __name__ == "__main__":
    logging.info("Starting GUI application")
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
