#!/bin/sh -f

if [ ! "$1" ]; then
  echo "usage: chainqsub.sh jobid number script"
  exit -1
fi

if [ ! "$2" ]; then
  echo "usage: chainqsub.sh jobid number script"
  exit -1
fi

if [ ! "$3" ]; then
  echo "usage: chainqsub.sh jobid number script"
  exit -1
fi

echo chaining $2 jobs starting with $1

oldjob=$1
script=$3

for count in `seq 1 1 $2`
do
  echo starting job $count to depend on $oldjob
  aout=`qsub -W depend=afterany:${oldjob} ${script}`
  nout=`echo $aout | sed 's/.sn-mgmt.cm.cluster//'`
  echo "   " jobid: $nout
  echo " "
  oldjob=$nout
done
