#!/bin/bash
for p in $(ls -d sorted_*)
do
	cd $p
	cp ../ffmpeg_make_mp4 .
	./ffmpeg_make_mp4 $p
	cd ..
done
