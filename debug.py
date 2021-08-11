
# general
import argparse
import sys, os, re, platform
from os.path import isfile

print(f'Current dir: {os.getcwd()}')

print(f'\nTags:')
# azureml
from azureml.core import Run
run = Run.get_context()
if hasattr(run, 'get_tags'):
    for t, v in run.get_tags().items():
        print(f'TAG: {t}: {v}')

def getOsFullDesc():
    name = ''
    if isfile('/etc/lsb-release'):
        lines = open('/etc/lsb-release').read().split('\n')
        for line in lines:
            if line.startswith('DISTRIB_DESCRIPTION='):
                name = line.split('=')[1]
                if name[0]=='"' and name[-1]=='"':
                    return name[1:-1]
    if isfile('/suse/etc/SuSE-release'):
        return open('/suse/etc/SuSE-release').read().split('\n')[0]
    try:
        import platform
        return ' '.join(platform.dist()).strip().title()
        #return platform.platform().replace('-', ' ')
    except ImportError:
        pass
    if os.name=='posix':
        osType = os.getenv('OSTYPE')
        if osType!='':
            return osType
    ## sys.platform == 'linux2'
    return os.name

def get_shell_stdout(_com):
    import subprocess
    r = ''
    p = subprocess.Popen(_com, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    for line in p.stdout.readlines():
        r = r + line.decode("utf-8")
    _ret=p.wait()
    return f'{r.strip()}'

def get_linked_lib_fp(name):
    return get_shell_stdout(f"ldconfig -p | grep {name} | tr ' ' '\n' | grep /")

print(f'\nOS: {platform.platform()}')
print(f'OS release: {platform.release()}')
print(f'OS fd: {getOsFullDesc()}')

print(f'\nPython version: {sys.version}')
print(f'Python version (via shell): {get_shell_stdout("python -V")}')
print(f'Python sys.path: {sys.path}')

print(f'\nPip version (via shell): {get_shell_stdout("pip -V")}')

if '\nLD_LIBRARY_PATH' in os.environ:
    print(f'LD_LIBRARY_PATH: {os.environ["LD_LIBRARY_PATH"]}')

## check docker
# https://stackoverflow.com/a/48710609/1417396
def is_docker():
    path = '/proc/self/cgroup'
    return (
        os.path.exists('/.dockerenv') or
        os.path.isfile(path) and any('docker' in line for line in open(path))
    )
_is_docker = is_docker()
print(f'\nInside docker: {_is_docker}')

## Check for conda
# https://stackoverflow.com/questions/47608532/how-to-detect-from-within-python-whether-packages-are-managed-with-conda
_is_conda = os.path.exists(os.path.join(sys.prefix, 'conda-meta'))
print(f'\nInside conda: {_is_conda}')

## Conda env
# https://stackoverflow.com/questions/36539623/how-do-i-find-the-name-of-the-conda-environment-in-which-my-code-is-running
if 'CONDA_DEFAULT_ENV' in os.environ:
    print(f'Conda default env: {os.environ["CONDA_DEFAULT_ENV"]}')
if 'CONDA_PREFIX' in os.environ:
    print(f'Conda prefix: {os.environ["CONDA_PREFIX"]}')
print(f'\nConda info: {get_shell_stdout("conda info")}')

## look for aml
_aml = False
try:
    import azureml  
    _aml = True
except ImportError:
    pass
print(f'\nazureml installed and importable: {_aml}')
if _aml:
    import azureml
    try:
        print(f'azurml version: {azureml.core.VERSION}')
    except:
        print(f'ERROR: failed to get azureml.core.VERSION')
        
## look for johnnydep
# https://stackoverflow.com/questions/47608532/how-to-detect-from-within-python-whether-packages-are-managed-with-conda
_johnnydep = False
try:
    import johnnydep  
    _johnnydep = True
except ImportError:
    pass
print(f'\nJohnnydep installed and importable: {_johnnydep}')

## test ffi
def is_ffi():
    try:
        import cffi
        ffi = cffi.FFI()
        return True
    except ImportError:
        return False 

_cffi = is_ffi()
print(f'\ncffi installed and importable: {_cffi}')
if _cffi:
    import cffi
    print(f'cffi version: {cffi.__version__}')

def get_link_map(_python_script, _highlight=[]):
   
    print(f'Get link map for: {_python_script}')
    _ls = get_shell_stdout(f'LD_DEBUG=all python {_python_script}')
    for _l in _ls.splitlines():
        if 'generating link map' in _l:
            m=re.search("file=(.*)\s\[", _l)
            if m is not None:
                _l = m.group(1)

            hit = False
            for _h in _highlight:
                if _h in _l:
                    hit=True
                    break
            print(f'{"LIB: " if not hit else "*** LIB: "}{_l}')
            if hit:
                print(f'-> {get_linked_lib_fp(_l)}')

if _cffi:
    with open("_cffi_test.py", "w") as text_file:
        text_file.write("import cffi; ffi = cffi.FFI()")

    try:
        get_link_map('_cffi_test.py', ['libffi'])
    except Exception as ex:
        print(f'...failed: {ex}')

## env vars
print('\nEnv vars:')
for p in sorted([k, v] for (k, v) in os.environ.items()):
    print(f'{p[0]}: {p[1]}')

## packages
# https://stackoverflow.com/a/35120690/1417396
print('\nPip packages:')
from pip._internal.utils.misc import get_installed_distributions

for p in sorted([p.project_name, p.version, p.location] for p in get_installed_distributions()):
    print(f'{p[0]}\t{p[1]}')
    print(f'{p[2]}\n')

## create outputs folder
outputs = os.path.join(os.getcwd(), 'outputs')
os.makedirs(outputs, exist_ok=True)

## collect a numer of files
print('\nSpecific files:')
from shutil import copyfile
_files = ['/opt/piplist.log',
'/opt/miniconda/lib/python3.8/site-packages/azureml/core/workspace.py',
'/opt/miniconda/lib/python3.8/site-packages/azureml/core/__init__.py',
'/opt/miniconda/lib/python3.8/site-packages/azureml/core/authentication.py',
'/opt/miniconda/lib/python3.8/site-packages/cryptography/fernet.py',
'/opt/miniconda/lib/python3.8/site-packages/cryptography/hazmat/primitives/padding.py']
for _f in _files:
    if os.path.isfile(_f):
        print(f'Found: {_f}')
        _nf = _f.replace(os.path.sep, "__");
        try:
            copyfile(_f, os.path.join(outputs, _nf))
        except Exception as ex:
            print(f'...failed: {ex}')
    else:
        print(f'Not found: {_f}')
# loop if found write to: learn.save(os.path.join(outputs, 'pets' __ instead of /), overwrite)

## Find files in /
print('\nSearch file in root:')

root_search = [] # ['libffi.*?\.so']
if root_search is not None and len(root_search) > 0:
    from pathlib import Path
    p = Path('/')
    files = p.glob('**/*')
    while True:
        try:
            f = next(files)
            if not f.is_file():
                continue
            f = str(f)    

        except (KeyError, PermissionError, FileNotFoundError):
            continue
        except StopIteration:
            break

        _hit = False
        for _t in root_search:
            if re.search(_t, f) is not None:
                _hit = True
                break

        if _hit:
            print(f'Found: {f}')

print(f'Done searching.')

print(f'Final done.')
