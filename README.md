# buildpy2
Simple Python-based build system, primarily for C and C++. Automatically
rebuilds files based on their dependencies like a Makefile, but provides a
more flexible syntax for creating build rules.

## Installation
* Clone this repository into your project directory or your Python
  installation's `site-packages` directory.

## Basic usage
* Create a Python script in your project directory and import buildpy2:
  ```python
  from buildpy2 import *

  def main():
      pass
      # ...
  
  if __name__ == "__main__":
      main()
  ```
* Add rules to your build file:
  ```python
  def main():
      # this is an example build script to compile a single C++ file
      rules = []
      build_dir = 'build'
      cpp_opts = ['-Wall', '-Wextra', '-g']
      link_opts = []
      
      rules.append(Target('all', [f'{build_dir}/main'], None, True))

      rules.append(CppRule(build_dir, '/usr/bin/g++', cpp_opts))

      sources = ['src/main.cpp']
      objs = [CppRule.gen_buildfile(f, build_dir) for f in sources]

      rules.append(ElfRule(executable, objs, '/usr/bin/g++', link_opts))
      
      run_build(rules, rules[0])
  ```

### Advanced usage
Refer to [MANUAL.md](MANUAL.md) for more information on how to use the
build system.

'Proper' Python documentation will likely be available some time in the
future.

## License
This project is licensed under the MIT license. See [LICENSE.txt](LICENSE.txt).


