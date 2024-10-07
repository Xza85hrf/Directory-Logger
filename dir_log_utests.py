import unittest
import tempfile
import os
from pathlib import Path
from dir_log_gen import DirectoryLogger, DirectoryLoggerError
import logging


class TestDirectoryLogger(unittest.TestCase):
    """
    Test suite for the DirectoryLogger class.
    This class contains various test cases to ensure the correct functionality
    of the DirectoryLogger.
    """

    def setUp(self):
        """
        Set up the test environment before each test method.
        This method creates a temporary directory structure and initializes logging.
        """
        # Set up logging for tests
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s - %(levelname)s - %(message)s",
            filename="directory_log.log",
            filemode="a",
        )
        logging.info("Starting test setup")

        # Create a temporary directory for testing
        self.temp_dir = tempfile.mkdtemp()
        self.log_file = os.path.join(self.temp_dir, "test_log.txt")

        # Create a test directory structure
        os.makedirs(os.path.join(self.temp_dir, "dir1", "subdir1"))
        os.makedirs(os.path.join(self.temp_dir, "dir2"))

        # Create test files
        with open(os.path.join(self.temp_dir, "file1.txt"), "w") as f:
            f.write("Test file 1")
        with open(os.path.join(self.temp_dir, "dir1", "file2.txt"), "w") as f:
            f.write("Test file 2")
        with open(os.path.join(self.temp_dir, "dir1", "file3.py"), "w") as f:
            f.write("print('Test file 3')")

        logging.info("Test setup completed")

    def tearDown(self):
        """
        Clean up the test environment after each test method.
        This method removes the temporary directory and its contents.
        """
        logging.info("Starting test teardown")
        # Remove all files and directories in the temporary directory
        for root, dirs, files in os.walk(self.temp_dir, topdown=False):
            for name in files:
                os.remove(os.path.join(root, name))
            for name in dirs:
                os.rmdir(os.path.join(root, name))
        os.rmdir(self.temp_dir)
        logging.info("Test teardown completed")

    def test_log_directory_with_metadata(self):
        """
        Test the basic functionality of logging a directory with metadata.
        """
        logging.info("Running test_log_directory_with_metadata")
        logger = DirectoryLogger(self.temp_dir, self.log_file)
        logger.log_directory_with_metadata()

        # Check if the log file was created and contains expected content
        self.assertTrue(os.path.exists(self.log_file))
        with open(self.log_file, "r") as f:
            content = f.read()
            self.assertIn("dir1", content)
            self.assertIn("dir2", content)
            self.assertIn("file1.txt", content)
            self.assertIn("file2.txt", content)

        logging.info("test_log_directory_with_metadata completed")

    def test_file_extension_filter(self):
        """
        Test the file extension filter functionality.
        """
        logger = DirectoryLogger(self.temp_dir, self.log_file, file_extension=".txt")
        logger.log_directory_with_metadata()

        # Check if only .txt files are included in the log
        with open(self.log_file, "r") as f:
            content = f.read()
            self.assertIn("file1.txt", content)
            self.assertIn("file2.txt", content)
            self.assertNotIn("file3.py", content)

    def test_max_depth(self):
        logger = DirectoryLogger(self.temp_dir, self.log_file, max_depth=0)
        logger.log_directory_with_metadata()

        with open(self.log_file, "r") as f:
            content = f.read()
            self.assertIn("dir1", content)
            self.assertIn("dir2", content)
            self.assertIn("file1.txt", content)
            self.assertNotIn("subdir1", content)
            self.assertNotIn("file2.txt", content)
            self.assertNotIn("file3.py", content)

    def test_stop_logging(self):
        logger = DirectoryLogger(self.temp_dir, self.log_file)
        logger.stop()
        # We need to actually call the method that checks for stop_requested
        with self.assertRaises(DirectoryLoggerError):
            logger.process_directory(Path(self.temp_dir), [], [])

    def test_output_formats(self):
        for format in ["text", "json", "csv", "xml"]:
            log_file = os.path.join(self.temp_dir, f"test_log.{format}")
            logger = DirectoryLogger(self.temp_dir, log_file, output_format=format)
            logger.log_directory_with_metadata()
            self.assertTrue(os.path.exists(log_file))

    def test_output_format_json(self):
        logger = DirectoryLogger(self.temp_dir, self.log_file, output_format="json")
        logger.log_directory_with_metadata()

        with open(self.log_file, "r") as f:
            content = f.read()
            self.assertTrue(content.startswith("["))
            self.assertTrue(content.endswith("]"))
            self.assertIn("Directory", content)
            self.assertIn("Files", content)

    def test_output_format_csv(self):
        logger = DirectoryLogger(self.temp_dir, self.log_file, output_format="csv")
        logger.log_directory_with_metadata()

        with open(self.log_file, "r") as f:
            content = f.read().splitlines()
            self.assertEqual(content[0], "Directory,Type,Name,Size,Created,Modified")
            self.assertTrue(any("file1.txt" in line for line in content))

    def test_output_format_xml(self):
        logger = DirectoryLogger(self.temp_dir, self.log_file, output_format="xml")
        logger.log_directory_with_metadata()

        with open(self.log_file, "r") as f:
            content = f.read()
            self.assertTrue(content.startswith("<?xml"))
            self.assertIn("<DirectoryLog>", content)
            self.assertIn("<Directory ", content)
            self.assertIn("<File ", content)

    def test_verbose_mode(self):
        logger = DirectoryLogger(self.temp_dir, self.log_file, verbose=True)
        with self.assertLogs(level="DEBUG") as cm:
            logger.log_directory_with_metadata()
        self.assertTrue(any("DEBUG" in log for log in cm.output))

    def test_get_progress(self):
        """
        Test the progress tracking functionality.
        """
        logging.info("Running test_get_progress")
        logger = DirectoryLogger(self.temp_dir, self.log_file)
        self.assertEqual(logger.get_progress(), 0)
        logger.log_directory_with_metadata()
        # The progress should be very close to 100 after completion
        self.assertGreaterEqual(logger.get_progress(), 99.9)
        self.assertLessEqual(logger.get_progress(), 100)
        logging.info("test_get_progress completed")


if __name__ == "__main__":
    logging.info("Starting unit tests")
    unittest.main()
    logging.info("Unit tests completed")
