# HPSS Plotfiles Notes

To make a list of plt files to get from HPSS:

- Gets you to HSI interface

```
$ hsi               
```

- Go to the directory where the *plt*.tar files are located

```
$ cd [directory]    
```

- Saves session output to a local file in the directory you were in
  before you started the HSI interface 

```
$ out hsi_plt_files
```

- List the plot files, one on each line, in hsi_plt_files

```
$ find . -name "*plt*.tar" 
```

- Return to local directory

```
$ exit
```

- List files

```
$ cat hsi_plt_files
```