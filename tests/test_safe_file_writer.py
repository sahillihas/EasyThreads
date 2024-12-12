import unittest
import os
from easythreads import SafeFileWriter

class TestSafeFileWriter(unittest.TestCase):
    def setUp(self):
        self.file_path = "test_output.txt"

    def tearDown(self):
        if os.path.exists(self.file_path):
            os.remove(self.file_path)

    def test_write(self):
        """Test if data is written safely."""
        writer = SafeFileWriter(self.file_path)
        writer.write("Hello")
        writer.write("World")

        with open(self.file_path, 'r') as f:
            lines = f.read().splitlines()

        self.assertCountEqual(lines, ["Hello", "World"])