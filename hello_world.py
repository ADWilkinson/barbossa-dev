#!/usr/bin/env python3
"""
Simple Hello World Python script for testing purposes.
Created as part of Barbossa autonomous engineer testing.
"""


def greet(name: str = "World") -> str:
    """
    Return a greeting message.
    
    Args:
        name (str): Name to greet. Defaults to "World".
        
    Returns:
        str: Greeting message.
    """
    return f"Hello, {name}!"


def main() -> None:
    """Main function to execute the hello world greeting."""
    print(greet())
    print(greet("Barbossa"))


if __name__ == "__main__":
    main()