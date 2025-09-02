import argparse
import os
from time import time

t0 = time()
parser = argparse.ArgumentParser(description='Create a minimal installation environment.')
parser.add_argument('jcm_root', help='Path to JCMsuite installation. E.g. $JCMROOT')
parser.add_argument('tarfile', help='Path to a tarfile. If the file exists it will be overwritten.')
parser.add_argument('--include_python', action='store_true', help='Adds python libraries to installation ' +
                    'to use python within solver (default:false).')

args = parser.parse_args()

if os.name == 'nt':
    raise EnvironmentError('This script only minifies the Linux version of JCMsuite.')

#Delete existing tar file
if os.path.exists(args.tarfile): os.remove(args.tarfile)

#Create tar file
with open(args.tarfile, 'w'): pass

tar_file = os.path.abspath(args.tarfile)
current_dir = os.getcwd()
os.chdir(args.jcm_root)

fileList = [
    dict(dir = 'bin', pattern = 'JCMsolve*'),
    dict(dir = 'bin', pattern = 'JCMdaemon*'),
    dict(dir = 'bin', pattern = 'JCMgeo*'),
    dict(dir = 'lib', pattern = 'lib[^Q]*')
]

if args.include_python:
    fileList.append(
        dict(dir = 'ThirdPartySupport/Python/lib', pattern = '*'),
    )

tar_cmd = 'find {dir} -name "{pattern}" | tar -rf {tarfile} -T -'
gz_cmd = 'gzip -f --fast {tarfile}; mv {tarfile}.gz {tarfile}'
    
for info in fileList:
    info['tarfile'] = tar_file
    thistar = tar_cmd.format(**info)
    print('Adding {dir}/{pattern} to {tarfile}'.format(**info))
    os.system(thistar)

    
print('Collected files to tar archive after {}s'.format(int(time()-t0)))
print('Compressing tar archive.')
os.system(gz_cmd.format(tarfile = tar_file))
os.chdir(current_dir)
print('Operation completed after {}s'.format(int(time()-t0)))
