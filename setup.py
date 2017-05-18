# !/usr/bin/env python3

# Copyright 2014-2017 Brockmann Consult GmbH
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import sys
import os
import os.path
import platform
import subprocess
import shutil
import glob
import unittest

from setuptools import setup
from setuptools.command.test import test
from setuptools.command.install import install
from setuptools.extension import Extension
from distutils.cmd import Command
from distutils import log

import jpyutil

base_dir = os.path.dirname(os.path.abspath(__file__))
src_main_c_dir = os.path.join(base_dir, 'src', 'main', 'c')
src_test_py_dir = os.path.join(base_dir, 'src', 'test', 'python')

import jpyutil

__author__ = jpyutil.__author__
__copyright__ = jpyutil.__copyright__
__license__ = jpyutil.__license__
__version__ = jpyutil.__version__

print('Using ' + jpyutil.__file__)

do_maven = False
if '--maven' in sys.argv:
    do_maven = True
    sys.argv.remove('--maven')
elif 'install' in sys.argv:
    do_maven = True
else:
    print('Note that you can use non-standard global option [--maven] '
          'to force a Java Maven build for the jpy Java API')

sources = [
    os.path.join(src_main_c_dir, 'jpy_module.c'),
    os.path.join(src_main_c_dir, 'jpy_diag.c'),
    os.path.join(src_main_c_dir, 'jpy_conv.c'),
    os.path.join(src_main_c_dir, 'jpy_compat.c'),
    os.path.join(src_main_c_dir, 'jpy_jtype.c'),
    os.path.join(src_main_c_dir, 'jpy_jarray.c'),
    os.path.join(src_main_c_dir, 'jpy_jobj.c'),
    os.path.join(src_main_c_dir, 'jpy_jmethod.c'),
    os.path.join(src_main_c_dir, 'jpy_jfield.c'),
    os.path.join(src_main_c_dir, 'jni/org_jpy_PyLib.c'),
]

headers = [
    os.path.join(src_main_c_dir, 'jpy_module.h'),
    os.path.join(src_main_c_dir, 'jpy_diag.h'),
    os.path.join(src_main_c_dir, 'jpy_conv.h'),
    os.path.join(src_main_c_dir, 'jpy_compat.h'),
    os.path.join(src_main_c_dir, 'jpy_jtype.h'),
    os.path.join(src_main_c_dir, 'jpy_jarray.h'),
    os.path.join(src_main_c_dir, 'jpy_jobj.h'),
    os.path.join(src_main_c_dir, 'jpy_jmethod.h'),
    os.path.join(src_main_c_dir, 'jpy_jfield.h'),
    os.path.join(src_main_c_dir, 'jni/org_jpy_PyLib.h'),
]

# Python unit tests that just use Java runtime classes (rt.jar)
python_java_rt_tests = [
    os.path.join(src_test_py_dir, 'jpy_rt_test.py'),
    os.path.join(src_test_py_dir, 'jpy_mt_test.py'),
    os.path.join(src_test_py_dir, 'jpy_diag_test.py'),
    # os.path.join(src_test_py_dir, 'jpy_perf_test.py'),
]

# Python unit tests that require jpy test fixture classes to be accessible
# via JRE system property '-Djava.class.path=target/test-classes'
python_java_jpy_tests = [
    os.path.join(src_test_py_dir, 'jpy_array_test.py'),
    os.path.join(src_test_py_dir, 'jpy_field_test.py'),
    os.path.join(src_test_py_dir, 'jpy_retval_test.py'),
    os.path.join(src_test_py_dir, 'jpy_exception_test.py'),
    os.path.join(src_test_py_dir, 'jpy_overload_test.py'),
    os.path.join(src_test_py_dir, 'jpy_typeconv_test.py'),
    os.path.join(src_test_py_dir, 'jpy_typeres_test.py'),
    os.path.join(src_test_py_dir, 'jpy_modretparam_test.py'),
    os.path.join(src_test_py_dir, 'jpy_gettype_test.py'),
]

# e.g. jdk_home_dir = '/home/marta/jdk1.7.0_15'
jdk_home_dir = jpyutil.find_jdk_home_dir()
if jdk_home_dir is None:
    log.error('Error: environment variable "JAVA_HOME" must be set to a JDK (>= v1.7) installation directory')
    exit(1)

log.info('Building a %s-bit library for a %s system with JDK at %s' % (
    '64' if jpyutil.PYTHON_64BIT else '32', platform.system(), jdk_home_dir))

jvm_dll_file = jpyutil.find_jvm_dll_file(jdk_home_dir)
if not jvm_dll_file:
    log.error('Error: Cannot find any JVM shared library')
    exit(1)

lib_dir = os.path.join(base_dir, 'lib')
jpy_jar_file = os.path.join(lib_dir, 'jpy.jar')
jvm_dll_dir = os.path.dirname(jvm_dll_file)

include_dirs = [src_main_c_dir, os.path.join(jdk_home_dir, 'include')]
library_dirs = [jvm_dll_dir]
libraries = [jpyutil.JVM_LIB_NAME]
define_macros = []
extra_link_args = []
extra_compile_args = []

if platform.system() == 'Windows':
    define_macros += [('WIN32', '1')]
    include_dirs += [os.path.join(jdk_home_dir, 'include', 'win32')]
    library_dirs += [os.path.join(jdk_home_dir, 'lib')]
elif platform.system() == 'Linux':
    include_dirs += [os.path.join(jdk_home_dir, 'include', 'linux')]
    libraries += ['dl']
    extra_link_args += ['-Xlinker', '-rpath', jvm_dll_dir]
elif platform.system() == 'Darwin':
    include_dirs += [os.path.join(jdk_home_dir, 'include', 'darwin')]
    library_dirs += [os.path.join(sys.exec_prefix, 'lib')]
    extra_link_args += ['-Xlinker', '-rpath', jvm_dll_dir]

with open('README.md') as file:
    long_description = file.read()

with open('CHANGES.md') as file:
    changelog = file.read()

dist = setup(name='jpy',
             description='Bi-directional Python-Java bridge',
             long_description=long_description + '\n\n' + changelog,
             version=__version__,
             platforms='Windows, Linux, Darwin',
             author=__author__,
             author_email='norman.fomferra@brockmann-consult.de',
             maintainer='Brockmann Consult GmbH',
             maintainer_email='norman.fomferra@brockmann-consult.de',
             license=__license__,
             url='https://github.com/bcdev/jpy',
             download_url='https://pypi.python.org/pypi/jpy/' + __version__,
             py_modules=['jpyutil'],
             package_data={'': [jpy_jar_file]},
             ext_modules=[Extension('jpy',
                                    sources=sources,
                                    depends=headers,
                                    include_dirs=include_dirs,
                                    library_dirs=library_dirs,
                                    libraries=libraries,
                                    extra_link_args=extra_link_args,
                                    extra_compile_args=extra_compile_args,
                                    define_macros=define_macros),
                          Extension('jdl',
                                    sources=[os.path.join(src_main_c_dir, 'jni/org_jpy_DL.c')],
                                    depends=[os.path.join(src_main_c_dir, 'jni/org_jpy_DL.h')],
                                    include_dirs=include_dirs,
                                    library_dirs=library_dirs,
                                    libraries=libraries,
                                    extra_link_args=extra_link_args,
                                    extra_compile_args=extra_compile_args,
                                    define_macros=define_macros),
                          ],
             classifiers=[
                 # How mature is this project? Common values are
                 #   3 - Alpha
                 #   4 - Beta
                 #   5 - Production/Stable
                 'Development Status :: 4 - Beta',

                 # Indicate who your project is intended for
                 'Intended Audience :: Developers',

                 # Pick your license as you wish (should match "license" above)
                 'License :: OSI Approved :: Apache 2 License',

                 # Specify the Python versions you support here. In particular, ensure
                 # that you indicate whether you support Python 2, Python 3 or both.
                 'Programming Language :: Python :: 2',
                 'Programming Language :: Python :: 2.7',
                 'Programming Language :: Python :: 3',
                 'Programming Language :: Python :: 3.3',
                 'Programming Language :: Python :: 3.4',
                 'Programming Language :: Python :: 3.5',
             ]
             )

#import pprint
#pprint.pprint(dist)
#pprint.pprint(dist.__dict__)
#pprint.pprint(dist.commands)
#pprint.pprint(dist.command_obj)
#pprint.pprint(dist.command_obj['build'].__dict__)
#pprint.pprint(dist.command_obj['install'].__dict__)
#pprint.pprint(dist.command_obj['install_lib'].__dict__)
#pprint.pprint(dist.command_obj['bdist_egg'].__dict__)
#pprint.pprint(dist.command_obj['egg_info'].__dict__)


#
# Continue with custom setup if 'build' step is included in commands
#

if dist.commands and len(dist.commands) > 0 \
        and dist.command_obj and len(dist.command_obj) > 0 \
        and 'clean' not in dist.command_obj \
        and 'build' in dist.command_obj:

    #
    # Get build directory (whose content we'll zip and in which we test)
    #

    build_dir = dist.command_obj['build'].build_lib
    if not os.path.exists(build_dir):
        log.error("Missing build directory '" + build_dir + "'")
        exit(1)

    #
    # Get install directory
    #

    install_dir = None
    if 'install' in dist.command_obj:
        install_dir = dist.command_obj['install'].install_lib
        if not os.path.exists(install_dir):
            log.warn("Missing install directory '" + install_dir + "'")
            install_dir = None

    #
    # Get egg (archive/directory) name
    #

    egg_name = None
    if 'bdist_egg' in dist.command_obj:
        egg_output = dist.command_obj['bdist_egg'].egg_output
        if egg_output:
            egg_name = os.path.basename(dist.command_obj['bdist_egg'].egg_output)

    #
    # Write jpy configuration files to target directories
    #

    mvn_goal = 'package'
    log.info("Executing Maven goal '" + mvn_goal + "'")
    code = subprocess.call(['mvn', 'clean', mvn_goal, '-DskipTests'],
                           shell=platform.system() == 'Windows')
    if code:
        exit(code)

    #
    # Copy JAR results to lib/*.jar
    #

    if not os.path.exists(lib_dir):
        os.mkdir(lib_dir)
    target_dir = os.path.join(base_dir, 'target')
    jar_files = glob.glob(os.path.join(target_dir, '*.jar'))
    jar_files = [f for f in jar_files
                 if not (f.endswith('-sources.jar')
                         or f.endswith('-javadoc.jar'))]
    if not jar_files:
        log.error('Maven did not generate any JAR artifacts')
        exit(1)
    for jar_file in jar_files:
        log.info("Copying " + jar_file + " -> " + lib_dir + "")
        shutil.copy(jar_file, lib_dir)


def _read(filename):
    """ Helper function for reading in project files """
    with open(filename) as file:
        return file.read()

def _build_dir():
    # TODO: figure out logic for dynamically getting this at runtime
    return os.path.join(base_dir, 'build/lib.macosx-10.12-x86_64-3.6')

def test_python_java_rt():
    """ Run Python test cases against Java runtime classes. """
    sub_env = {'PYTHONPATH': _build_dir()}

    log.info('Executing Python unit tests (against Java runtime classes)...')
    return jpyutil._execute_python_scripts(python_java_rt_tests,
                                           env=sub_env)

def test_python_java_classes():
    """ Run Python tests against JPY test classes """
    sub_env = {'PYTHONPATH': _build_dir()}

    log.info('Executing Python unit tests (against Java runtime classes)...')
    return jpyutil._execute_python_scripts(python_java_jpy_tests,
                                            env=sub_env)
    
def test_maven():
    jpy_config = os.path.join(_build_dir(),'jpyconfig.properties')
    mvn_args = '-DargLine=-Xmx512m -Djpy.config=' + jpy_config + ' -Djpy.debug=true'
    log.info("Executing Maven goal 'test' with arg line " + repr(mvn_args))
    code = subprocess.call(['mvn', 'test', mvn_args], shell=platform.system() == 'Windows')
    return code == 0

def _write_jpy_config(target_dir=None):
    """
    Write out a well-formed jpyconfig.properties file for easier Java
    integration in a given location.
    """
    if not target_dir:
        target_dir = _build_dir()
    log.info('Writing jpy configuration to ' + target_dir)
    return subprocess.call([sys.executable,
                            os.path.join(target_dir, 'jpyutil.py'),
                            '--jvm_dll', jvm_dll_file,
                            '--java_home', jdk_home_dir,
                            '--log_level', 'DEBUG',
                            '--req_java',
                            '--req_py'])

def _copy_jpyutil():
    src = os.path.abspath(jpyutil.__file__)
    dest = _build_dir()
    log.info('Copying %s to %s' % (src, dest))
    shutil.copy(src, dest)

def _build_jpy():
    package_maven()
    _copy_jpyutil()
    _write_jpy_config()
    

def test_suite():
    suite = unittest.TestSuite()
    
    def test_python_with_java_runtime(self):
        assert 0 == test_python_java_rt()
        
    def test_python_with_java_classes(self):
        assert 0 == test_python_java_classes()

    def test_java(self):
        assert test_maven()

    suite.addTest(test_python_with_java_runtime)
    suite.addTest(test_python_with_java_classes)
    suite.addTest(test_java)

    return suite

class MavenBuildCommand(Command):
    """ Custom JPY Maven builder command """
    description = 'run Maven to generate JPY jar'
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        self.announce('Building JPY')
        _build_jpy()
        

class JpyBuildBeforeTest(test):
    """ Customization of SetupTools Install command for JPY """

    def run(self):
        self.run_command('build')
        self.run_command('maven')
        
        test.run(self)


class JpyInstall(install):
    """ Custom install command to trigger Maven steps """
    
    def run(self):
        self.run_command('build')
        self.run_command('maven')
        install.run(self)


setup(name='jpy',
      description='Bi-directional Python-Java bridge',
             long_description=_read('README.rst') + '\n\n' + _read('CHANGES.txt'),
             version=__version__,
      platforms='Windows, Linux, Darwin',
      author=__author__,
      author_email='norman.fomferra@brockmann-consult.de',
      maintainer='Brockmann Consult GmbH',
      maintainer_email='norman.fomferra@brockmann-consult.de',
      license=__license__,
      url='https://github.com/bcdev/jpy',
      download_url='https://pypi.python.org/pypi/jpy/' + __version__,
      py_modules=['jpyutil'],
      package_data={'': [jpy_jar_file]},
      ext_modules=[Extension('jpy',
                             sources=sources,
                             depends=headers,
                             include_dirs=include_dirs,
                             library_dirs=library_dirs,
                             libraries=libraries,
                             extra_link_args=extra_link_args,
                             extra_compile_args=extra_compile_args,
                             define_macros=define_macros),
                   Extension('jdl',
                             sources=[os.path.join(src_main_c_dir, 'jni/org_jpy_DL.c')],
                             depends=[os.path.join(src_main_c_dir, 'jni/org_jpy_DL.h')],
                             include_dirs=include_dirs,
                             library_dirs=library_dirs,
                             libraries=libraries,
                             extra_link_args=extra_link_args,
                             extra_compile_args=extra_compile_args,
                             define_macros=define_macros),
      ],
      test_suite='setup.test_suite',
      cmdclass={
          'maven': MavenBuildCommand,
          'test': JpyBuildBeforeTest,
          'install': JpyInstall
      },
      classifiers=['Development Status :: 4 - Beta',
                   # Indicate who your project is intended for
                   'Intended Audience :: Developers',

                   # Pick your license as you wish (should match "license" above)
                   'License :: OSI Approved :: Apache 2 License',

                   # Specify the Python versions you support here. In particular, ensure
                   # that you indicate whether you support Python 2, Python 3 or both.
                   'Programming Language :: Python :: 2',
                   'Programming Language :: Python :: 2.7',
                   'Programming Language :: Python :: 3',
                   'Programming Language :: Python :: 3.3',
                   'Programming Language :: Python :: 3.4'])

