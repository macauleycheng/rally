#!/bin/sh


RUN_PATH="t5k_test_case/neutron"

for i in $(ls $RUN_PATH);
do 
echo "rally task start" $RUN_PATH"/"$i
rally task start $RUN_PATH/$i
done

for id in $(rally task list --uuids); 
do 
rally task report $id --out $(pwd)/$RUN_PATH/output/$id.html
done

./t5k_test_case/clear.sh
