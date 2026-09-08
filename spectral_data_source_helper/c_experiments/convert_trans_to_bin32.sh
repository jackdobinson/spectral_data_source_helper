#!/bin/bash


SIZE_SUFFIX="M"
SIZE_DIV_FACTOR="$((1024*1024)).0"

DEBUG="TRUE"
DEBUG="FALSE"

if [[ "${DEBUG}" == "TRUE" ]]; then 
	unset DEBUGINFOD_URLS
	gcc -g -O1 -o convert_trans_to_bin32 convert_trans_to_bin32.c
else
	gcc -O3 -o convert_trans_to_bin32 convert_trans_to_bin32.c
	gcc -O3 -fPIC -shared -o convert_trans_to_bin32.so convert_trans_to_bin32.c
fi

#exit # ONLY COMPILE

if [[ ! $? -eq 0 ]]; then
	echo "COMPILATION FAILED"
	exit
fi

START_TIME=$(date -u +%s.%N)
total_size=0

files=~/data/linedata_test_storage/cache/exomol.com/db/CH4/12C-1H4/YT10to10/12C-1H4__YT10to10__*.trans.bz2

for file in ${files[@]}; do
	transfile=${file%%.bz2}
	
	if [[ ! -f ${transfile} ]]; then
		SPLIT_TIME_0=$(date -u +%s.%N)
		
		filesize=$(du -bs "${file}" | cut -f1)
		total_size=$((total_size+filesize))
		
		echo "UNZIPPING ${file}"
		#bunzip2 -k ${file}
		lbzip2 -dk ${file}
	
	
		SPLIT_TIME_1=$(date -u +%s.%N)

		split_time=$(bc -l <<<"$SPLIT_TIME_1-$SPLIT_TIME_0")
		bytes_per_split_time=$(bc -l <<<"${filesize}.0/(${split_time}*${SIZE_DIV_FACTOR})")
		echo "UNZIP: Split Time ${split_time} Sec. Processed ${bytes_per_split_time} ${SIZE_SUFFIX}Bytes/Sec"
	fi
done

END_TIME=$(date -u +%s.%N)

if [[ ${total_size} -gt 0 ]]; then
	elapsed_time=$(bc -l <<<"$END_TIME-$START_TIME")
	bytes_per_time=$(bc -l <<<"${total_size}.0/(${elapsed_time}*${SIZE_DIV_FACTOR})")
	echo "UNZIP PERFORMED: Elapsed Time ${elapsed_time} Sec. Processed ${bytes_per_time} ${SIZE_SUFFIX}Bytes/Sec"
fi


START_TIME=$(date -u +%s.%N)
total_size=0

for file in ${files[@]}; do
	
	SPLIT_TIME_0=$(date -u +%s.%N)
	transfile=${file%%.bz2}
	
	filesize=$(du -bs "${transfile}" | cut -f1)
	total_size=$((total_size+filesize))
	echo "CONVERTING ${transfile}"
	
	if [[ "${DEBUG}" == "TRUE" ]]; then 
		gdb  --batch -ex run --args ./convert_trans_to_bin32 "${transfile}" "${transfile}.bin32"
	else
		./convert_trans_to_bin32 "${transfile}" "${transfile}.bin32"
	fi
	
	SPLIT_TIME_1=$(date -u +%s.%N)
	
	split_time=$(bc -l <<<"$SPLIT_TIME_1-$SPLIT_TIME_0")
	bytes_per_split_time=$(bc -l <<<"${filesize}.0/(${split_time}*${SIZE_DIV_FACTOR})")
	echo "CONVERSION: Split Time ${split_time} Sec. Processed ${bytes_per_split_time} ${SIZE_SUFFIX}Bytes/Sec"
	
	#break
done

END_TIME=$(date -u +%s.%N)

elapsed_time=$(bc -l <<<"$END_TIME-$START_TIME")
bytes_per_time=$(bc -l <<<"${total_size}.0/(${elapsed_time}*${SIZE_DIV_FACTOR})")


echo "CONVERSION PERFORMED: Elapsed Time ${elapsed_time} Sec. Processed ${bytes_per_time} ${SIZE_SUFFIX}Bytes/Sec"