#!/bin/bash


SIZE_SUFFIX="M"
SIZE_DIV_FACTOR="$((1024*1024)).0"

SCRIPT_DIR="$(dirname ${BASH_SOURCE})"

BIN_DIFF_SCRIPT="${SCRIPT_DIR}/arr_diff.py"

BIN="${SCRIPT_DIR}/../bin/convert_trans_to_bin32"
BUILD_SCRIPT="${SCRIPT_DIR}/../build.sh"

if [[ ! -f ${BIN} ]]; then
	echo "Cannot find binary at ${BIN}, must run build script at ${BUILD_SCRIPT}"
	${BUILD_SCRIPT}

	if [[ ! $? -eq 0 ]]; then
		echo "BUILD FAILED"
		exit 1
	fi
fi


test_file="${SCRIPT_DIR}/test_list.txt"
result_file="${test_file}.bin32"
expected_result_file="${SCRIPT_DIR}/test_expected_result.txt.bin32"



START_TIME=$(date -u +%s.%N)
total_size=$(du -bs "${test_file}" | cut -f1)

if [[ "${DEBUG}" == "TRUE" ]]; then 
	gdb  --batch -ex run --args ${BIN} "${test_file}" "${result_file}"
else
	${BIN} "${test_file}" "${result_file}"
fi

success="$?"

if [[ ! ${success} -eq 0 ]]; then
	break
fi


END_TIME=$(date -u +%s.%N)

elapsed_time=$(bc -l <<<"$END_TIME-$START_TIME")
bytes_per_time=$(bc -l <<<"${total_size}.0/(${elapsed_time}*${SIZE_DIV_FACTOR})")


echo "CONVERSION PERFORMED: Elapsed Time ${elapsed_time} Sec. Processed ${bytes_per_time} ${SIZE_SUFFIX}Bytes/Sec"

echo "CHECKING correspondence between result file and expected result file"
echo "    test file \"${test_file}\""
echo "    result file \"${result_file}\""
echo "    expected result file \"${expected_result_file}\""

diff_result=$(python3 ${BIN_DIFF_SCRIPT} ${result_file} ${expected_result_file})
echo "${diff_result}"

if [[ "inputs equal within error" == "${diff_result}" ]]; then
	echo "Result file IS identical to expected result file"
	echo "TEST PASS"
else
	echo "Result file IS NOT identical to expected result file."
	echo "TEST FAIL"
fi