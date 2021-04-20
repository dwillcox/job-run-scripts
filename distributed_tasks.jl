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

    parse_args(s)
end

function main()
    args = parse_commandline()

    # setup parallelism
    manager = MPIManager(np=args["nprocs"])
    addprocs(manager)

    # make tasks
    tasks = [replace(args["task"], "{entry}" => entry) for entry=args["entries"]]

    # execute tasks in parallel
    @sync @distributed for task in tasks
        run(`sh -c $task`)
    end

    println("Completed all tasks.")
end

main()
