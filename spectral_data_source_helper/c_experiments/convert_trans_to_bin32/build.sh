#!/bin/bash


DEBUG="TRUE"
DEBUG="FALSE"

SCRIPT_DIR="$(dirname ${BASH_SOURCE})"

C_STD="gnu2x"

CFLAGS_COMMON=(
	"-std=gnu2x"
	"-flto"
)

CFLAGS_DEBUG=(
	"-g"
	"-Og"
)

CFLAGS_BIN=(
	"-Ofast"
	"-fomit-frame-pointer"
	"-march=native"
)

CFLAGS_SHARED_LIB=(
	"-Ofast" 
	"-flto" 
	"-fPIC"
	"-fvisibility=hidden" 
	"-shared"
)

BIN="${SCRIPT_DIR}/bin/convert_trans_to_bin32"
SHARED_LIB="${SCRIPT_DIR}/lib/convert_trans_to_bin32.so"

CFILES_COMMON=(
	"${SCRIPT_DIR}/src/ffi.c"
	"${SCRIPT_DIR}/src/impl.c"
	"${SCRIPT_DIR}/src/ascii_utils.c"
	"${SCRIPT_DIR}/src/binary_utils.c"
)

CFILES_BIN=(
	"${SCRIPT_DIR}/src/main.c"
)

if [[ "${DEBUG}" == "TRUE" ]]; then 
	unset DEBUGINFOD_URLS
	gcc ${CFLAGS_COMMON[@]} ${CFLAGS_DEBUG[@]} -o ${BIN} ${CFILES_BIN[@]} ${CFILES_COMMON[@]}
	if [[ ! $? -eq 0 ]]; then
		echo "DEBUG BINARY COMPILATION FAILED"
		exit 1
	fi
else
	gcc ${CFLAGS_COMMON[@]} ${CFLAGS_BIN[@]} -o ${BIN} ${CFILES_BIN[@]} ${CFILES_COMMON[@]}
	if [[ ! $? -eq 0 ]]; then
		echo "BINARY COMPILATION FAILED"
		exit 1
	fi
	gcc ${CFLAGS_COMMON[@]} ${CFLAGS_SHARED_LIB[@]} -o ${SHARED_LIB} ${CFILES_COMMON[@]}
	if [[ ! $? -eq 0 ]]; then
		echo "SHARED LIBRARY COMPILATION FAILED"
		exit 1
	fi
fi

echo "COMPILATION SUCCEEDED"

exit 0 # compiled successfully