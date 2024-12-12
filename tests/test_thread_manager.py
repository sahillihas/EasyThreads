import unittest
from easythreads import ThreadManager

class TestThreadManager(unittest.TestCase):
    def test_threads_execution(self):
        """Test if threads execute correctly."""
        results = []

        def sample_function(index):
            results.append(index)

        manager = ThreadManager()
        for i in range(5):
            manager.add_thread(target=sample_function, args=(i,))

        manager.start_all()
        manager.join_all()

        self.assertEqual(sorted(results), [0, 1, 2, 3, 4])