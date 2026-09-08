
from pathlib import Path
from typing import Any, NamedTuple
import ctypes

_convert_trans_to_bin32 = ctypes.CDLL(Path(__file__).parent / "../c_experiments/convert_trans_to_bin32.so")
_convert_trans_to_bin32.main.argtypes = (ctypes.c_int, ctypes.POINTER(ctypes.c_char_p))
_convert_trans_to_bin32.ffi_run.argtypes = (ctypes.c_int, ctypes.POINTER(ctypes.c_char_p))


class FFI_TASK_INFO(ctypes.Structure):
	_fields_ = [
		('complete', ctypes.c_bool),
		('errnum', ctypes.c_int),
		('errmsg', ctypes.c_char*1024),
	]

FFI_TASK_INFO_TUPLE = NamedTuple('FFI_TASK_INFO_TUPLE', [('complete', bool), ('errnum', int), ('errmsg', str)])


def run_main(dll_path : Path | str, *args : tuple[Any,...]) -> int:
	dll = ctypes.CDLL(dll_path)
	dll.main.argtypes = (ctypes.c_int, ctypes.POINTER(ctypes.c_char_p))

	argc = len(args) + 1
	argv_t = ctypes.c_char_p * argc
	argv = argv_t(
		*(
			str(x).encode('ascii') if (type(x) is not bytes) else x for x in [
				f'{dll_path}::main', # argv[0] is name of the 'program' being called
				*args
			]
		)
	)
	
	result = dll.main(argc, argv)
	if result != 0:
		print(f'ERROR: {dll_path}::main returned {result}')
	return result

class ConvertTransToBin32:
	_dll = ctypes.CDLL(Path(__file__).parent / "../c_experiments/convert_trans_to_bin32.so")
	
	class FFI_IN(ctypes.Structure):
		_fields_= [
			('input_file', ctypes.c_char_p),
			('output_file', ctypes.c_char_p),
		]
	
	class FFI_OUT(ctypes.Structure):
		_fields_ = [
			('task_info', FFI_TASK_INFO),
			('n_bytes', ctypes.c_uint64),
			('n_entries', ctypes.c_uint64),
			('bytes_sec', ctypes.c_double),
			('entries_sec', ctypes.c_double),
			('elapsed_time', ctypes.c_double),
		]
	
	_dll.ffi_run.argtypes = (FFI_IN, ctypes.POINTER(FFI_OUT))
	_FFI_OUT_TUPLE = NamedTuple('FFI_OUT_TUPLE', [
		('task_info', FFI_TASK_INFO_TUPLE),
		('n_bytes', int),
		('n_entries', int),
		('bytes_sec', float),
		('entries_sec', float),
		('time_elapsed_sec', float),
	])
	
	@classmethod
	def run(cls, input_file, output_file) -> NamedTuple:
		ffi_in = cls.FFI_IN(
			str(input_file).encode('ascii'), 
			str(output_file).encode('ascii')
		)
		
		# All these will be overwritten
		ffi_out = cls.FFI_OUT(FFI_TASK_INFO(False, 0, b"\0"), 0, 0, -1, -1, -1)
		
		cls._dll.ffi_run(ffi_in, ctypes.byref(ffi_out))
		
		# Pack result
		result = cls._FFI_OUT_TUPLE(*(getattr(ffi_out, k) for k in (x[0] for x in cls.FFI_OUT._fields_)))
		if not result.task_info.complete:
			print(f'ERROR :: ERRNO: {result.task_info.errnum} MSG: {result.task_info.errmsg}')
			exit()
		return result

		