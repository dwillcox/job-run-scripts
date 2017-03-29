#!/bin/bash
htar -x -m -f /home/dwillcox/wdconvect_cburn_urca_Mconv-0.5_hot_VODE/wd_512_rhoc4-5_plt$1.tar
./central_angle_average.Linux.gfortran.exe -p wd_512_rhoc4-5_plt$1 -s wd_512_rhoc4-5_plt$1.caaprofile --rho_cutoff 1.0e5
htar_afile wd_512_rhoc4-5_plt$1.caaprofile
mv wd_512_rhoc4-5_plt$1.caaprofile plotfiles/.
mv wd_512_rhoc4-5_plt$1.tar plotfiles/.