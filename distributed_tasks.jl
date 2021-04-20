using MPIClusterManagers, Distributed
using ArgParse

function parse_commandline()
    s = ArgParseSettings()
    @add_arg_table s begin
        "task"
            help = "Task template specifying the entry wildcard with '{entry}'"
            required = true
        "--entries"
            help = "List of entries to substitute into the task '{entry}' field to generate all tasks."
            required = true
            nargs = '+'
        "--nprocs"
            help = "Number of processes to use."
            arg_type = Int
            required = true
    end

    return parse_args(s)
end

function make_tasks(args)
    template = args["task"]
    tasks = [replace(template, "{entry}" => entry) for entry=args["entries"]]
    return tasks
end

@everywhere function execute_task(task)
    run(`sh -c $task`)
end

function main()
    args = parse_commandline()

    # setup parallelism
    manager = MPIManager(np=args.nprocs)
    addprocs(manager)

    # execute tasks in parallel
    tasks = make_tasks(args)
    pmap(execute_task, tasks)
end

main()
