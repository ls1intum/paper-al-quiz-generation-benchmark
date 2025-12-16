# Introduction to Python Programming

## Section 1: Functions

### Section 1.1: Defining Functions

In Python, functions are defined using the `def` keyword followed by the function name and parentheses. Functions allow you to encapsulate reusable blocks of code.

```python
def greet(name):
    return f"Hello, {name}!"
```

Functions can take parameters and return values. They are fundamental building blocks in Python programming.

### Section 1.2: Function Arguments

Functions can accept different types of arguments:
- Positional arguments
- Keyword arguments
- Default arguments
- Variable-length arguments (*args, **kwargs)

## Section 2: Data Types

### Section 2.1: Basic Data Types

Python has several built-in data types:
- Integers (int)
- Floating-point numbers (float)
- Strings (str)
- Booleans (bool)

### Section 2.2: Collection Types

Python provides several collection types:
- Lists: Ordered, mutable sequences
- Tuples: Ordered, immutable sequences
- Sets: Unordered collections of unique elements
- Dictionaries: Key-value pairs

### Section 2.3: Mutability

Understanding mutability is crucial in Python:

**Mutable types** can be changed after creation:
- Lists
- Dictionaries
- Sets

**Immutable types** cannot be changed after creation:
- Integers
- Floats
- Strings
- Tuples

When you assign a mutable object to a new variable, both variables reference the same object in memory. Changes made through one variable affect the other.

```python
x = [1, 2, 3]
y = x  # y references the same list as x
y.append(4)
print(x)  # Output: [1, 2, 3, 4]
```

## Section 3: Control Flow

### Section 3.1: Conditional Statements

Python uses `if`, `elif`, and `else` for conditional execution:

```python
if condition:
    # code block
elif another_condition:
    # code block
else:
    # code block
```

### Section 3.2: Loops and Control Statements

Python provides `for` and `while` loops for iteration. Control statements include:
- `break`: Exit the loop
- `continue`: Skip to next iteration
- `pass`: Do nothing (placeholder)

The `pass` statement is particularly useful when you need a syntactically correct placeholder for future code:

```python
def not_implemented_yet():
    pass  # TODO: implement this later
```

### Section 3.3: Loop Patterns

Common loop patterns in Python:
- Iterating over sequences
- Using range()
- List comprehensions
- Dictionary comprehensions

## Learning Objectives

By the end of this module, you should be able to:
1. Define and use functions effectively
2. Distinguish between mutable and immutable data types
3. Understand how variable assignment works with different types
4. Use control flow statements appropriately
5. Write clean, idiomatic Python code

## Practice Exercises

1. Write a function that reverses a string
2. Create a list of squares using list comprehension
3. Implement a function that checks if a number is prime
4. Use a dictionary to count word frequencies in a text
