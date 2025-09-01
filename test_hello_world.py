#!/usr/bin/env python3
"""
Unit tests for hello_world.py
"""

import unittest
from hello_world import greet


class TestHelloWorld(unittest.TestCase):
    """Test cases for the hello world functionality."""
    
    def test_default_greeting(self):
        """Test default greeting without parameters."""
        result = greet()
        self.assertEqual(result, "Hello, World!")
        
    def test_custom_greeting(self):
        """Test greeting with custom name."""
        result = greet("Barbossa")
        self.assertEqual(result, "Hello, Barbossa!")
        
    def test_empty_string_greeting(self):
        """Test greeting with empty string."""
        result = greet("")
        self.assertEqual(result, "Hello, !")
        
    def test_special_characters_greeting(self):
        """Test greeting with special characters."""
        result = greet("Captain Jack Sparrow")
        self.assertEqual(result, "Hello, Captain Jack Sparrow!")


if __name__ == "__main__":
    unittest.main()