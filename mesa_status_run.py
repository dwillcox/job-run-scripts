#!/usr/bin/env python
"""
This script takes a MESA logfile as an argument and a set of success
termination codes and runs or restarts MESA as necessary.

Read a MESA log file (supplied as an argument) and determine
whether the run completed sucessfully based on the sucess termination
codes (supplied as arguments).

If the log file is not present and the argument --run_if_no_logfile
is passed, then go ahead and run MESA. Otherwise exit without running.

If the log file is present then look for 'termination code: ABCD' and
check if ABCD is one of the success termination codes. If there is a
termination code print the success status and exit.

If there is no termination code but the logfile is present then look
for the last entry of the form 'save photos/ABCD for model NNNN' and
restart MESA from the last photo. If there is no 'save photos...'
entry in the logfile then run MESA without a restart.

Donald E. Willcox
"""

import argparse
import re
from subprocess import Popen, PIPE

parser = argparse.ArgumentParser()
parser.add_argument('logfile', type=str, help='Name of the MESA logfile to check.')
parser.add_argument('-s', '--success', type=str, nargs='+', help='Success termination codes to look for.')
parser.add_argument('-rno', '--run_if_no_logfile', action='store_true', help='If the logfile cannot be found, then run MESA if this argument is present.')
parser.add_argument('-rlog', '--run_log', type=str, default='run_mesa.log', help='Name of logfile to redirect MESA output into when running or restarting.')
parser.add_argument('-dry', '--dry_run', action='store_true', help='If supplied, do not actually run MESA but do print status messages.')
args = parser.parse_args()

rephoto = re.compile('\Asave photos/([\w]+) for model ([\w]+)\Z')
reterminate = re.compile('\Atermination code:(.*)\Z')

def runcmd(cmd):
    proc = Popen(cmd, stdout=PIPE, stderr=PIPE, shell=True)
    out, err = proc.communicate()
    out_msg = out.decode('utf-8')
    err_msg = err.decode('utf-8')
    print('--------')
    print('Executed {} with output:'.format(cmd))
    print(out_msg)
    print('and error message:')
    print(err_msg)

def runmesa():
    cmd = './rn >> {}'.format(args.save_log)
    if not args.dry_run:
        runcmd(cmd)
    else:
        print(cmd)

def restartmesa(photo):
    cmd = './re {} >> {}'.format(photo, args.save_log)
    if not args.dry_run:
        runcmd(cmd)
    else:
        print(cmd)

def gettermination(lines):
    # Get termination status and code from logfile lines
    terminated = False
    code = None
    for l in lines:
        mt = reterminate.match(l)
        if mt:
            terminated = True
            code = mt.group(1).strip()
            break
    return terminated, code

def getrestartphoto(lines):
    # Get restart photo number from logfile lines
    photo = None
    for l in lines:
        mp = rephoto.match(l)
        if mp:
            photo = mp.group(1)
            break
    return photo

def processlog(logfile):
    lines = [l.strip() for l in logfile]
    logfile.close()
    if lines:
        # Reverse for the termination and photo loops
        lines.reverse()
        terminated, code = gettermination(lines)
        if terminated:
            # Check code to print status
            if not code:
                print('WARNING: Terminated with no code!')
            else:
                if args.success:
                    if code in args.success:
                        print('Successful termination with code {}'.format(code))
                    else:
                        print('Error termination with code {}'.format(code))
                else:
                    print('Terminated with code {}'.format(code))
        else:
            # Check for a photo to restart
            photo = getrestartphoto(lines)
            if photo:
                restartmesa(photo)
            else:
                runmesa()
    else:
        runmesa()
        
if __name__ == "__main__":
    # Check if the logfile exists and process accordingly
    try:
        flog = open(args.logfile, 'r')
    except FileNotFoundError:
        if args.run_if_no_logfile:
            runmesa()
        else:
            print('Logfile not found. Exiting.')
    else:
        processlog(flog)
