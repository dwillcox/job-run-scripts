#!/bin/bash
for p in $(ls -d sorted_*)
do
	cd $p
	./ffmpeg_make_mp4 $p
	cd ..
done
