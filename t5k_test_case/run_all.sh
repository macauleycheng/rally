#!/bin/sh

./t5k_test_case/neutron_run.sh
./t5k_test_case/nova_run.sh
./t5k_test_case/cinder_run.sh
./t5k_test_case/vm_operation.sh
./t5k_test_case/clear.sh
