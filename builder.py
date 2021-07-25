import sys
import os
import subprocess
import re
import pathlib

DRY_RUN = 0
VERSION = '1.1.0'

def exists(f: str) -> bool:
    return os.path.exists(f)

def is_newer(f1: str, f2: str) -> bool:
    # is f1 newer than f2?
    m1 = os.path.getmtime(f1)
    m2 = os.path.getmtime(f2)
    # print("%s modified @ %f" % (f1, m1))
    # print("%s modified @ %f" % (f2, m2))
    return m1 > m2

def run(args, pwd='.'):
    print(args)
    if not DRY_RUN:
        res = subprocess.run(args, cwd=pwd)
        if res.returncode != 0:
            print("process exited with code %d\n" % res.returncode)
            sys.exit(1)

class Rule:
    def __init__(self, phony: bool=False):
        self.phony = phony

    def can_build(self, file: str) -> bool:
        return False

    def get_prereqs(self, file: str) -> list:
        return []

    def build(self, file: str):
        pass

# explicit target
class Target(Rule):
    def __init__(self, file: str, prerequisites: list, build_func, phony: bool=False):
        super().__init__(phony)
        self.file = file
        self.prereqs = prerequisites
        self.build_func = build_func

    def can_build(self, file: str) -> bool:
        return file == self.file

    def get_prereqs(self, file: str) -> list:
        return self.prereqs

    def build(self, file: str):
        if self.build_func == None: return
        self.build_func(file, self.prereqs)

def build(rules, rule, file):
    print("build %s with %s" % (file, rule))
    # if the rule is phony, always build it
    build_this = rule.phony

    for pr in rule.get_prereqs(file):
        # print("pr: %s" % pr)
        built = False
        for r in rules:
            if r == rule: continue
            if r.can_build(pr):
                if build(rules, r, pr):
                    print("prereq updated; build %s" % file)
                    build_this = True
                built = True
                break
        if not built and not exists(pr):
            print("prerequisite %s of %s does not exist and has no rule to build it" \
                % (pr, file))
            sys.exit(1)
        
        if not build_this and exists(pr) and (not exists(file) or is_newer(pr, file)):
            print("prereq newer; build %s" % file)
            build_this = True

    if build_this:     
        rule.build(file)
    else:
        print("Nothing to do for %s" % file)
    return build_this

# build a cpp file into an object file
class CppRule(Rule):
    def __init__(self, build_dir: str, compiler: str, 
            options: list, src_ext: str='.cpp', out_ext: str='.o'):
        super().__init__(False)
        self.build_dir = build_dir
        self.compiler = compiler
        self.options = options
        self.src_ext = src_ext
        self.out_ext = out_ext

    def can_build(self, file: str) -> bool:
        return file.startswith(self.build_dir) \
            and file.endswith(self.src_ext + self.out_ext)

    def get_prereqs(self, file: str) -> list:
        depfile = os.path.splitext(file)[0] + '.d'

        path = pathlib.Path(file)
        # build/src/.../thing.cpp.o -> src/.../thing.cpp
        srcfile = str(pathlib.Path(*path.parts[1:]))
        srcfile = os.path.splitext(srcfile)[0]
        srcfile = srcfile.replace('__/', '../')

        deps = [srcfile]
        if exists(depfile):
            with open(depfile, 'r') as f:
                full = ''
                for line in f:
                    if line.endswith('\\\n'):
                        line = line[:-2]
                    line = line.strip()
                    full += line + ' '
                deps = full.split(':')[1].strip().split(' ')
                # print(deps)

        return deps

    def build(self, file: str):
        file = os.path.relpath(file)
        fdir = os.path.dirname(file)
        run(['mkdir', '-p', fdir])

        srcfile = self.get_prereqs(file)[0]
        depfile = os.path.splitext(file)[0] + '.d'

        cmd = [self.compiler]
        cmd.extend(self.options)
        cmd.extend(['-MMD', '-MF', depfile])
        cmd.extend(['-c', srcfile, '-o', file])
        run(cmd)

    @staticmethod
    def gen_buildfile(file: str, build_dir: str='build') -> str:
        buildfile = build_dir + '/' + os.path.relpath(file) + '.o'
        buildfile = buildfile.replace('../', '__/')
        return buildfile

# build an ELF file from several object/archive files
class ElfRule(Target):
    def __init__(self, file: str, objs: list, libs: list, compiler: str, options: list):
        super().__init__(file, objs + libs, None)
        self.objs = objs
        self.libs = libs
        self.compiler = compiler
        self.options = options

    def build(self, file: str):
        cmd = [self.compiler]
        cmd.extend(self.options)
        linkpaths = []
        cmd.extend(self.objs)
        for lib in self.libs:
            libdir = os.path.relpath(os.path.dirname(lib))
            if not libdir in linkpaths:
                linkpaths.append(libdir)

            m = re.fullmatch(r'lib(\w+)\.a', os.path.basename(lib))
            if m is None:
                # try matching for a shared library
                m = re.fullmatch(r'lib(\w+)\.so', os.path.basename(lib))
            if m is None:
                print('%s is not a properly named library' % lib)
                sys.exit(1)
            libname = m.group(1)
            cmd.append('-l' + libname)
        cmd.extend(['-L' + p for p in linkpaths])
        cmd.extend(['-o', file])
        run(cmd)

# build a static library archive from several object files
class LibRule(Target):
    def __init__(self, file: str, objs: list, archiver: str):
        super().__init__(file, objs, None)
        self.archiver = archiver

    def build(self, file: str):
        cmd = [self.archiver, '-rcs', file]
        cmd.extend(self.prereqs)
        run(cmd)

def run_build(rules, def_target):
    if len(sys.argv) > 1:
        target = Target('__main', [sys.argv[1]], None, True)
    else:
        target = def_target
    build(rules, target, None)

# def main():
#     rules = []
#     build_dir = 'build'
#     executable = f'{build_dir}/main'
#     all = Target('all', [executable], None, True)

#     # general compiling
#     rules.append(CppRule(build_dir, '/usr/bin/g++', 
#         ['-Wall', '-Wextra', '-g', '-Og', '-Isrc']))

#     sources = ['src/main.cpp']
#     objs = [CppRule.gen_buildfile(f) for f in sources]

#     # main executable
#     rules.append(ElfRule(executable, objs, '/usr/bin/g++', []))
#     rules.append(all)
#     rules.append(Target('clean', [], lambda f,p: ['rm', '-r', build_dir], True))

#     run_build(rules, all)    

# if __name__ == "__main__":
#     main()
