#!/usr/bin/env python3
"""
Uses MPI to execute a set of tasks in parallel, provided in a taskfile.

Written for Python 3.

Donald E. Willcox
"""

import argparse
import shlex
import os
import re
from itertools import cycle
from subprocess import Popen, PIPE
from mpi4py import MPI
from time import sleep

parser = argparse.ArgumentParser()
parser.add_argument('--taskfile', type=str,
                    help=('Input file containing command-line tasks to execute, ' +
                          'one per line.\n' +
                          'A sequence of dependent commands may be concatenated on ' +
                          'the same line by triple ampersands &&&.'))
parser.add_argument('-t', '--task_template', type=str,
                    help="String specifying the task template, specifying file template with '{file}' in which case --files should also be passed.")
parser.add_argument('-r', '--file_regexp', type=str,
                    help="Python regular expression matching the files to insert in the template for the '{file}' substring.")
parser.add_argument('-chk', '--checkpoint', type=str,
                    help='(Optional) Checkpoint file to restart from.')
parser.add_argument('-bchk', '--base_checkpoint', type=str,
                    help='(Optional) Base name for saving checkpoints. Defaults to no checkpointing.')
parser.add_argument('-nchk', '--num_checkpoints', type=int, default=2,
                    help=('(Optional) Number of most recent checkpoint files to keep.\n' +
                          'By default, two checkpoint files will be carried.\n' +
                          'To keep no checkpoints, use -nchk 0\n' +
                          'To keep all checkpoints, use -nchk -1'))
args = parser.parse_args()

# Global MPI information
mpi_comm = MPI.COMM_WORLD
mpi_size = mpi_comm.Get_size()
mpi_rank = mpi_comm.Get_rank()

class Task(object):
    def __init__(self, cmd=None):
        self.cmd = cmd.strip()
        self.done = False
        self.out = ''
        self.err = ''

    def __eq__(self, other):
        return self.cmd == other.cmd
        
    def mark_done(self):
        self.done = True

    def is_done(self):
        return self.done

    def get_cmd(self):
        return self.cmd

    def get_output(self):
        return self.out

    def get_error(self):
        return self.err

    def execute(self):
        try:
            # First, facilitate shell=False by passing cmd
            # through shlex.split()
            # cmd_lex = shlex.split(self.cmd)
            # Execute cmd by supplying it to Popen

            # Use shell=True to allow chaining multiple commands
            # into one command using double ampersands (&&)
            proc = Popen(self.cmd, stdout=PIPE, stderr=PIPE, shell=True)
            out, err = proc.communicate()
            # Decode out and err and return (stdout, stderr)
            try:
                out_str = out.decode('utf-8')
            except:
                out_str = 'OUTPUT DECODE EXCEPTION FOR COMMAND {}'.format(self.cmd)
            try:
                err_str = err.decode('utf-8')
            except:
                err_str = 'ERROR DECODE EXCEPTION FOR COMMAND {}'.format(self.cmd)
        except:
            err_str = 'UNKNOWN ERROR EXECUTING CMD: {}'.format(self.cmd)
            out_str = err_str
        self.out = out_str
        self.err = err_str

class DependentTasks(object):
    def __init__(self, commands=None):
        # Initialize tasks with a set of commands
        self.tasks = []
        self.command_sequence = []
        if commands:
            self.tasks = [Task(cmd) for cmd in commands.split('&&&')]
        self.tag_from_root = -1
        self.tag_to_root = -1
        self.index = -1

    def get_command_sequence(self):
        if not self.command_sequence:
            self.command_sequence = [t.get_cmd() for t in self.tasks]
        return self.command_sequence

    def set_all_done(self):
        # Set all these dependent tasks done
        for t in self.tasks:
            t.mark_done()

    def has_undone_task(self):
        # Return True if there remains an undone task
        # Return False otherwise
        for t in self.tasks:
            if not t.is_done():
                return True
        return False

    def gen_next_todo(self):
        # Get the next undone dependent task index or return None
        for t in self.tasks:
            if not t.is_done():
                yield t

    def get_done_string(self):
        # Get the string of commands already done
        cstring = ''
        for t in self.tasks:
            if t.is_done():
                if cstring:
                    cstring += ' &&& ' + t.get_cmd()
                else:
                    cstring += t.get_cmd()
        if not cstring:
            cstring = '#undone'
        return cstring

class TaskCollection(object):
    def __init__(self, args, checkpoint_file=None):
        self.num_itasks = 0
        self.primary = []
        self.checkpoint_files = []
        
        if args.checkpoint:
            self.load_task_file(args.checkpoint)
        elif args.taskfile:
            self.load_task_file(args.taskfile)
        elif args.task_template and args.file_regexp:
            self.make_tasks_from_regexp(args)
        else:
            raise NotImplementedError("Neither a taskfile nor template/regexp pair were supplied.")

    def load_task_file(self, taskfile):
        # Get the list of tasks to execute
        # Lines beginning with '#' are comments
        tasks = []
        ftasks = open(taskfile, 'r')
        for l in ftasks.readlines():
            ls = l.strip()
            if ls and ls[0] != '#':
                tasks.append(ls)
        ftasks.close()

        self.init_task_list(tasks)

    def make_tasks_from_regexp(self, args):
        # build tasks from task template and file regular expression
        assert(args.task_template is not None and args.file_regexp is not None)
        assert("{file}" in args.task_template)

        # compile the re
        regexp = re.compile(args.file_regexp)

        # get list of files in current working directory
        # matching the regular expression
        cwd_files = os.listdir()
        task_files = [f for f in cwd_files if regexp.match(f) and not f+".skip" in cwd_files]

        # combine task template and task files to get tasks
        tasks = [args.task_template.replace("{file}", f) for f in task_files]

        self.init_task_list(tasks)

    def init_task_list(self, tasks):
        self.primary = [DependentTasks(t) for t in tasks]
        self.num_itasks = len(self.primary)

    def set_dep_done(self, j):
        # Set the jth dependent task complete
        self.primary[j].set_all_done()

    def num_idep_done(self):
        # Get the number of independent tasks completed
        ndone = 0
        for td in self.primary:
            if not td.has_undone_task():
                ndone += 1
        return ndone

    def refresh_from_checkpoint(self, args):
        tchk = TaskCollection(args)
        for id, tdchk in enumerate(tchk.primary):
            tdslf = self.primary[id]
            for j, tc in enumerate(tdchk.tasks):
                if tc == tdslf.tasks[j]:
                    tdslf.tasks[j].mark_done()
                    
    def save_to_checkpoint(self, checkfile_base='mpiproc', num_checkpoints=2):
        if num_checkpoints == 0:
            return
        
        num_idone = self.num_idep_done()
        checkfile = '{}_chk{:06}'.format(checkfile_base, num_idone)
        fchk = open(checkfile, 'w')
        
        # Write commented header indicating the status
        fchk.write('# CHECKPOINT STATUS\n')
        fchk.write('# TOTAL     INDEPENDENT TASKS: {}\n'.format(self.num_itasks))
        fchk.write('# COMPLETED INDEPENDENT TASKS: {}\n'.format(num_idone))
        
        # Save progress for each DependentTask on its own line
        for dt in self.primary:
            st = dt.get_done_string()
            fchk.write(st + '\n')
        fchk.close()
        
        # Cull obsolete checkpoint files if applicable
        if num_checkpoints != -1:
            # Keep track of current checkpoint file name
            self.checkpoint_files.append(checkfile)
            if len(self.checkpoint_files) > num_checkpoints and num_checkpoints > 0:
                cull_chk = self.checkpoint_files[:-num_checkpoints]
                for chk in cull_chk:
                    os.remove(chk)
                    self.checkpoint_files.pop(0)

    def note_if_finished(self, notefile_base='mpiproc'):
        if (self.num_idep_done() == self.num_itasks):
            notefile = '{}_finished'.format(notefile_base)
            fnote = open(notefile, 'w')
            fnote.write('# MPIPROC FINISHED WITH TASKS\n')
            fnote.close()

    def get_undone_tasks(self):
        undone = []
        for dt in self.primary:
            if dt.has_undone_task():
                undone.append(dt)
        return undone

    def gen_next_todo(self):
        # Get the next independent task
        for dt in self.primary:
            if dt.has_undone_task():
                yield dt        

def print_out_err(jtask, cmds, out, err):
    print('######################################################################')
    print('Task: {}\n'.format(jtask))
    print('COMMANDS:')
    for cmd in cmds:
        print(cmd + '\n')
    print('STDOUT:')
    try:
        for oi in out:
            print(oi + '\n')
    except:
        print('OUTPUT PRINT EXCEPTION!\n')
    print('STDERR:')
    try:
        for ei in err:
            print(ei + '\n')
    except:
        print('ERROR PRINT EXCEPTION!\n')
    print('######################################################################\n')

if __name__ == '__main__':
    if mpi_size == 1:
        # Run tasks serially
        # Open the inputs file
        tc = TaskCollection(args)
        
        # Restart from the checkpoint file, if supplied
        if args.checkpoint:
            tc.refresh_from_checkpoint(args)

        for idx, tdep in enumerate(tc.gen_next_todo()):
            outs = []
            errs = []
            for t in tdep.gen_next_todo():
                t.execute()
                outs.append(t.get_output())
                errs.append(t.get_error())
            cmds = tc.primary[idx].get_command_sequence()
            print_out_err(idx, cmds, outs, errs)
            tc.set_dep_done(idx)
            if args.base_checkpoint:
                tc.save_to_checkpoint(checkfile_base=args.base_checkpoint,
                                      num_checkpoints=args.num_checkpoints)
    else:
        if mpi_rank == 0:
            # Open the inputs file
            tc = TaskCollection(args)

            # Restart from the checkpoint file, if supplied
            if args.checkpoint:
                tc.refresh_from_checkpoint(args)

            pid_pool = list(range(1, mpi_size))

            # Container for currently queued tasks
            irecv_pid = []

            outs = []
            errs = []

            nfin = 0
            nerr = 0

            finished_with_tasks = False
            jdep = 0

            undone_tasks = tc.get_undone_tasks()

            while not finished_with_tasks:
                if tc.num_itasks == tc.num_idep_done():
                    print("Finished with all tasks")
                    finished_with_tasks = True
                    break

                while (undone_tasks and len(irecv_pid) < mpi_size - 1):
                    tdep = undone_tasks.pop(0)
                    pid = pid_pool.pop()
                    isend = 2*jdep + 1
                    irecv = 2*jdep + 2
                    tdep.tag_from_root = isend
                    tdep.tag_to_root   = irecv
                    tdep.index         = jdep
                    print(f"Assigning job {jdep} to process {pid}")
                    jsend_request = mpi_comm.isend(tdep, dest=pid, tag=isend)
                    jrecv_request = mpi_comm.irecv(source=pid, tag=irecv)                    
                    irecv_pid.append((pid, jrecv_request))
                    jdep += 1

                assign_new_task = False
                while not assign_new_task:
                    for j, (pid, jrecv_request) in enumerate(irecv_pid):
                        jrecv_status = jrecv_request.Get_status()
                        if jrecv_status:
                            print(f"Process {pid} finished its task.")
                            # Successful receive, task is completed
                            idx, out, err = jrecv_request.wait()
                            cmds = tc.primary[idx].get_command_sequence()
                            print_out_err(idx, cmds, out, err)                
                            if any(err):
                                nerr += 1
                            nfin += 1
                            irecv_pid.pop(j)
                            pid_pool.append(pid)
                            tc.set_dep_done(idx)
                            if args.base_checkpoint:
                                tc.save_to_checkpoint(checkfile_base=args.base_checkpoint,
                                                      num_checkpoints=args.num_checkpoints)
                            assign_new_task = True
                            break

            # Print result summary
            print("Result Summary:")
            print(f"{nfin} of {tc.num_itasks} Tasks Completed")
            print(f"{nerr} Tasks Wrote to STDERR")

            tc.note_if_finished(notefile_base="mpiproc_exec")

            # Program is terminating, send termination and finalize MPI
            continue_running = False
            for pid in range(1, mpi_size):
                mpi_comm.send(continue_running, dest=pid)
            MPI.Finalize()
        else:
            while True:
                dependent_tasks = mpi_comm.recv(source=0, tag=MPI.ANY_TAG)
                if dependent_tasks:
                    outs = []
                    errs = []
                    for t in dependent_tasks.gen_next_todo():
                        t.execute()
                        outs.append(t.get_output())
                        errs.append(t.get_error())
                    ioutserrs = (dependent_tasks.index, outs, errs)
                    sreq = mpi_comm.isend(ioutserrs, dest=0, tag=dependent_tasks.tag_to_root)
                    sreq.wait()
                else:
                    break
