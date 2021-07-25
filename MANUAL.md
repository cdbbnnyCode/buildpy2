# buildpy2 Documentation

*[for version 1.1.0]*

## How it works

buildpy2 generates files based on rules. Each rule has:
* A set of files that it is capable of creating
* A set of prerequisite files that are required in order to create a given
  file
* A function to create ('build') the file in question
* A 'phony' flag, which tells the system to always run the build function
  regardless of the state of the file or its prerequisites.

To build a given input file, the build system searches for the first rule
that can build that file. Unlike Make, the system only considers the first
rule that it finds. *This may change in the future*. 

If no rule is found to build the file, the system only checks if the file
already exists. If the file does not exist, the build exits with an error.

However, if a rule is found, the system checks all of the prerequisites that
the rule provides for the file and attempts to build them. Then it decides
whether to build the target file:
* If the rule is marked as 'phony', it is always rebuilt.
* If any of the prerequisites were rebuilt, the target file is also rebuilt.
* If the target file does not exist, it is rebuilt.
* If any of the prerequisites exist and have a newer modification time than
  the target file, it is rebuilt.

## Rules
Rules are defined as subclasses of the `Rule` class. Subclasses should
implement the following functions:
* `__init__`: 'Phony' rules should call `super().__init__` with the `phony`
  argument set to `True`.
* `can_build(self, file)`: This should return `True` if this rule can
  build the given input file regardless of its prerequisites.
* `get_prereqs(self, file)`: Takes an input file previously validated by
  `can_build` and returns a list of prerequisite files needed for that file.
* `build(self, file)`: This should run the build function for the given input
  file, which has previously been validated by `can_build`. Prerequisites for
  the file should exist at this point.

## Built-in rules

Since rules can be fairly bulky and complex, some built-in rules have been 
defined for convenience:

### `Target`
`Target` is a special type of rule that can only build a single specific
file. Its constructor takes several arguments:
* `file`: The specific target file
* `prerequisites`: A list of prerequisite files required to build the target
  file
* `build_func`: A function or lambda to build the input file. For
  convenience, the function is passed the input file and the list of
  prerequisites.  
  If the build function is `None`, no action is taken to build the file.
* `phony`: [optional] Set to `True` to mark this target as 'phony'. This is
  useful if the target file is not actually a file, or for targets such as
  'all', 'clean', 'install', etc.

Example: The `all` target
```python
# 'all' target builds the library and documentation
rules.append(Target('all', ['libthing.so', 'doc'], None, True))
```

### Built-in C/C++ build rules
#### `CppRule`
This rule can be used to compile C and C++ files. It manages dependency
files and file paths. Its constructor takes several arguments:
* `build_dir`: where to put build files. It is not recommended to set this
  to `'.'` or the current working directory.
* `compiler`: the path to the compiler executable.
* `options`: Compiler options in a list
* `src_ext`: [optional] Set the source file extension (`.cpp` by default)
* `out_ext`: [optional] Set the output file extension (`.o` by default)

`CppRule` will build any files with the extension `{src_ext}.{out_ext}` that
exist in `{build_dir}`. It reads prerequisites from the compiler-generated
dependency file, which is generated using the `-MMD` compiler option.

To convert a source file into an output file, a convenience function
`CppRule.gen_buildfile()` is provided. This function takes the source file
and build directory as parameters, and it returns a build file.

Example: Converting source files to object files
```python
sources = ['src/a.cpp', 'src/b.cpp', 'src/main.cpp']
objs = [CppRule.gen_buildfile(f) for f in sources]
```

Example: Creating rules for C and C++ files
```python
# convert .cpp -> .cpp.o
rules.append(CppRule('build/', '/usr/bin/g++', cxx_opts, '.cpp', '.o'))
# convert .c -> .c.o
rules.append(CppRule('build/', '/usr/bin/gcc', c_opts,   '.c',   '.o'))
```

#### `ElfRule`
This rule will compile an ELF file (shared library or executable) from
several object files and/or libraries. Its constructor takes the following
parameters:
* `file`: The output file to build
* `objs`: A list of object files to link
* `libs`: A list of (shared or static) library files to link. These library
  files must be named `lib{name}.a` or `lib{name}.so`.
* `compiler`: Path to the compiler
* `options`: Link options

#### `LibRule`
This rule builds a static library file from several object files. Its
constructor takes the following parameters:
* `file`: The output `.a` file to build
* `objs`: A list of object files to archive
* `archiver`: Path to the compiler toolchain's `ar` program

## Functions
The build system provides functions to build rules, run external code, and
check files.

* `run_build(rules, def_target)`: Build the file specified on the command
  line, or the target specified by `def_target` if nothing is given on
  the command line.
* `build(rules, rule, file)`: Build a file with the given rule.
* `run(args, pwd='.')`: Run an external program, blocking until it finishes.
  If the program returns a non-zero exit code, this function will forcibly
  quit the Python process.
* `exists(f)`: Shorthand for `os.path.exists(f)`
* `is_newer(f1, f2)`: Returns `True` iff `f1` was modified more recently
  than `f2`.
