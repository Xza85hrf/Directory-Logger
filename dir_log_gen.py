import os
import time
import argparse
import json
import csv
import configparser
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Union, Callable
from pathlib import Path
import logging


# Custom exception for more granular error handling
class DirectoryLoggerError(Exception):
    """Custom exception for DirectoryLogger errors."""
    pass


class DirectoryLogger:
    """
    A class to log directory contents with metadata.

    This class traverses a directory structure, collects information about files and
    subdirectories, and outputs the data in various formats.
    """

    def __init__(
        self,
        path: str,
        log_file: str,
        file_extension: Optional[str] = None,
        max_depth: Optional[int] = None,
        output_format: str = "text",
        to_console: bool = False,
        verbose: bool = False,
    ):
        """
        Initialize the DirectoryLogger with the given parameters.

        :param path: The root directory to start logging from.
        :param log_file: The file to write the log output to.
        :param file_extension: Optional file extension to filter files.
        :param max_depth: Optional maximum depth for directory traversal.
        :param output_format: The format of the output log (text, json, csv, or xml).
        :param to_console: Whether to also print the output to console.
        :param verbose: Whether to enable verbose logging.
        """
        self.path = Path(path)
        self.log_file = log_file
        self.file_extension = file_extension
        self.max_depth = max_depth
        self.output_format = output_format
        self.to_console = to_console
        self.verbose = verbose
        self.log_data = []
        self.total_items = 0
        self.processed_items = 0
        self.stop_requested = False
        self.setup_logging()

    def setup_logging(self) -> None:
        """Set up logging configuration based on verbosity level."""
        level = logging.DEBUG if self.verbose else logging.INFO
        logging.basicConfig(
            level=level,
            format="%(asctime)s - %(levelname)s - %(message)s",
            filename="directory_log.log",
            filemode="a"
        )
        # Add a stream handler for console output if verbose is True
        if self.verbose:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.DEBUG)
            formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
            console_handler.setFormatter(formatter)
            logging.getLogger().addHandler(console_handler)

    def get_file_info(self, file_path: Path) -> Dict[str, Union[str, int]]:
        """
        Get metadata for a single file.

        :param file_path: Path to the file.
        :return: Dictionary containing file metadata.
        """
        try:
            stats = file_path.stat()
            return {
                "Name": file_path.name,
                "Size": stats.st_size,
                "Created": time.ctime(stats.st_ctime),
                "Modified": time.ctime(stats.st_mtime),
            }
        except Exception as e:
            logging.error(f"Error processing file {file_path}: {e}")
            return {}

    def process_directory(
        self, root: Path, dirs: List[str], files: List[str]
    ) -> Dict[str, Union[str, List[Union[str, Dict[str, Union[str, int]]]]]]:
        """
        Process a single directory, collecting information about its files and subdirectories.

        :param root: Path to the current directory.
        :param dirs: List of subdirectory names in the current directory.
        :param files: List of file names in the current directory.
        :return: Dictionary containing information about the directory.
        """
        if self.stop_requested:
            raise DirectoryLoggerError("Logging process stopped by user.")
        
        directory_info = {"Directory": str(root), "Directories": dirs, "Files": []}

        with ThreadPoolExecutor() as executor:
            future_to_file = {
                executor.submit(self.get_file_info, root / file_name): file_name
                for file_name in files
                if not self.file_extension or file_name.endswith(self.file_extension)
            }
            for future in as_completed(future_to_file):
                if self.stop_requested:
                    raise DirectoryLoggerError("Logging process stopped by user.")
                file_info = future.result()
                if file_info:
                    directory_info["Files"].append(file_info)
                # Remove this line: self.processed_items += 1

        return directory_info

    def log_directory_with_metadata(self) -> None:
        """
        Main method to traverse the directory structure and log metadata.

        This method walks through the directory tree, processes each directory,
        and writes the output in the specified format.
        """
        self.setup_logging()
        self.log_data = []
        self.total_items = 0
        self.processed_items = 0

        try:
            # Count total items for progress
            for root, dirs, files in os.walk(self.path):
                self.total_items += len(dirs) + len(files)

            for root, dirs, files in os.walk(self.path):
                if self.stop_requested:
                    raise DirectoryLoggerError("Logging process stopped by user.")

                root_path = Path(root)
                current_depth = len(root_path.relative_to(self.path).parts)

                if self.max_depth is not None and current_depth > self.max_depth:
                    continue

                logging.debug(f"Processing directory: {root}")
                directory_info = self.process_directory(root_path, dirs, files)
                self.log_data.append(directory_info)
                self.processed_items += len(dirs) + len(files)  # Update processed items

            # Ensure processed_items matches total_items at the end
            self.processed_items = self.total_items

            output_handlers = {
                "json": self.write_json_output,
                "csv": self.write_csv_output,
                "text": self.write_text_output,
                "xml": self.write_xml_output,
            }

            output_handler = output_handlers.get(
                self.output_format, self.write_text_output
            )
            output_handler()

            if self.to_console:
                print(
                    json.dumps(self.log_data, indent=4)
                    if self.output_format == "json"
                    else self.log_data
                )

        except DirectoryLoggerError as e:
            logging.error(str(e))
        except Exception as e:
            logging.exception(f"An unexpected error occurred: {e}")

    def write_json_output(self) -> None:
        """Write the log data to a JSON file."""
        with open(self.log_file, "w") as f:
            json.dump(self.log_data, f, indent=4)

    def write_csv_output(self) -> None:
        """Write the log data to a CSV file."""
        with open(self.log_file, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(
                ["Directory", "Type", "Name", "Size", "Created", "Modified"]
            )
            for entry in self.log_data:
                for dir_name in entry["Directories"]:
                    writer.writerow([entry["Directory"], "D", dir_name, "", "", ""])
                for file_info in entry["Files"]:
                    writer.writerow(
                        [
                            entry["Directory"],
                            "F",
                            file_info["Name"],
                            file_info["Size"],
                            file_info["Created"],
                            file_info["Modified"],
                        ]
                    )

    def write_text_output(self) -> None:
        """Write the log data to a plain text file."""
        with open(self.log_file, "w") as f:
            for entry in self.log_data:
                f.write(f"Directory: {entry['Directory']}\n")
                for dir_name in entry["Directories"]:
                    f.write(f"  [D] {dir_name}\n")
                for file_info in entry["Files"]:
                    f.write(
                        f"  [F] {file_info['Name']} - Size: {file_info['Size']} bytes, Created: {file_info['Created']}, Modified: {file_info['Modified']}\n"
                    )
                f.write("\n")

    def write_xml_output(self) -> None:
        """Write the log data to an XML file."""
        root = ET.Element("DirectoryLog")
        for entry in self.log_data:
            dir_elem = ET.SubElement(root, "Directory", path=entry["Directory"])
            for dir_name in entry["Directories"]:
                ET.SubElement(dir_elem, "Subdirectory", name=dir_name)
            for file_info in entry["Files"]:
                file_elem = ET.SubElement(dir_elem, "File", name=file_info["Name"])
                ET.SubElement(file_elem, "Size").text = str(file_info["Size"])
                ET.SubElement(file_elem, "Created").text = file_info["Created"]
                ET.SubElement(file_elem, "Modified").text = file_info["Modified"]

        tree = ET.ElementTree(root)
        tree.write(self.log_file, encoding="unicode", xml_declaration=True)

    def get_progress(self) -> float:
        """
        Calculate the current progress of the logging process.

        :return: Percentage of items processed.
        """
        return (
            (self.processed_items / self.total_items) * 100
            if self.total_items > 0
            else 0
        )

    def stop(self) -> None:
        """Set the stop flag to interrupt the logging process."""
        self.stop_requested = True


def load_config(config_file: str) -> Dict[str, str]:
    """
    Load configuration from a file.

    :param config_file: Path to the configuration file.
    :return: Dictionary containing configuration options.
    """
    config = configparser.ConfigParser()
    config.read(config_file)
    return dict(config["DEFAULT"])


def main() -> None:
    """
    Main function to parse command-line arguments and run the directory logger.

    This function sets up the argument parser, processes command-line arguments,
    loads configuration (if specified), and initializes the DirectoryLogger.
    """
    parser = argparse.ArgumentParser(
        description="Log directory contents with metadata."
    )
    parser.add_argument("directory", help="The directory path to log.")
    parser.add_argument("logfile", help="The log file name.")
    parser.add_argument(
        "--extension", help="Filter files by extension (e.g., .txt).", default=None
    )
    parser.add_argument(
        "--max-depth",
        type=int,
        help="Maximum depth of directory traversal.",
        default=None,
    )
    parser.add_argument(
        "--format",
        choices=["text", "json", "csv", "xml"],
        default="text",
        help="Output format of the log.",
    )
    parser.add_argument("--console", action="store_true", help="Print log to console.")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose mode.")
    parser.add_argument("--config", help="Path to configuration file.", default=None)
    args = parser.parse_args()

    if args.config:
        config = load_config(args.config)
        directory = config.get("directory", args.directory)
        logfile = config.get("logfile", args.logfile)
        extension = config.get("extension", args.extension)
        max_depth = (
            int(config.get("max_depth", str(args.max_depth)))
            if config.get("max_depth")
            else args.max_depth
        )
        output_format = config.get("format", args.format)
        to_console = config.get("console", str(args.console)).lower() == "true"
        verbose = config.get("verbose", str(args.verbose)).lower() == "true"
    else:
        directory, logfile, extension, max_depth, output_format, to_console, verbose = (
            args.directory,
            args.logfile,
            args.extension,
            args.max_depth,
            args.format,
            args.console,
            args.verbose,
        )

    logging.info("Starting directory logging process")
    logger = DirectoryLogger(
        directory, logfile, extension, max_depth, output_format, to_console, verbose
    )
    logger.log_directory_with_metadata()
    logging.info(f"Directory log with metadata saved to {logfile}")
    logging.info("Directory logging process completed")

if __name__ == "__main__":
    main()
