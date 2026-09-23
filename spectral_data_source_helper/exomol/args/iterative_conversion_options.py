
import dataclasses as dc
from typing import Self, Literal, Any, ClassVar




@dc.dataclass
class IterativeConversionOptions:
	enabled : bool = False
	delete_intermediate_files_after_use : bool = True
	delete_final_files_after_use : bool = False
	compress_and_save_fastest_format : bool = False
	conversion_chain : tuple[str] = ('.trans', '.bin32')
	compression_fmt : Literal['.bz2','.xz'] = '.xz'
	
	_arg_prefix : ClassVar[str] = 'ic'
	_arg_short : ClassVar[str] = 'C'

	@classmethod
	def add_argument_group(
			cls, 
			parser, 
	):
		grp = parser.add_argument_group(
			"Iterative Conversion Options", 
			description="If enabled, iterative conversion will convert files as they are requested. Often, reading after conversion to a faster format is much more efficient than reading the original format (even with the conversion overhead)."
		)
		
		assert (cls._arg_short is None) or (len(cls._arg_short) == 1), "If `arg_short` is not None, it must be a single character long."
		
		field_defaults = dict(
			(field.name, field.default) for field in dc.fields(cls)
		)
		
		
		grp.add_argument(
			*((f'-{cls._arg_short}', f'--{cls._arg_prefix}.enabled') if cls._arg_short is not None else (f'--{cls._arg_prefix}.enabled',)),
			action='store_true',
			help='Enables iterative conversion (default: disabled)',
			default=False
		)
		
		grp.add_argument(
			f'--{cls._arg_prefix}.no_delete_intermediate_files_after_use',
			action='store_true',
			help='If present, will not delete intermediate converted and downloaded files after they are used. (default=False)',
			default=False
		)
		
		grp.add_argument(
			f'--{cls._arg_prefix}.delete_final_files_after_use',
			action='store_true',
			help='If present, will delete final converted files after they are used. (default=False)',
			default=False
		)
		
		grp.add_argument(
			f'--{cls._arg_prefix}.compress_and_save_fastest_format',
			action='store_true',
			help='If present, will compress and save the data in the fastest format, assumed to be the format at the end of the conversion chain. (default=False)',
			default=False
		)
		
		grp.add_argument(
			f'--{cls._arg_prefix}.conversion_chain',
			type=str,
			metavar='FMT',
			help=f'Set the chain of formats to convert data to, use a comma-separated list with no spaces (default={",".join(field_defaults['conversion_chain'])})',
			default=",".join(field_defaults['conversion_chain']),
		)
		
		grp.add_argument(
			f'--{cls._arg_prefix}.compression_fmt',
			type=str,
			metavar='FMT',
			help=f'Set the compression format to use if `--no_compress_and_save_fastest_format` is not present (default={field_defaults['compression_fmt']})',
			default=field_defaults['compression_fmt'],
		)
		
		return grp
		
	
	
	@classmethod
	def from_args(
			cls,
			arg_dict : dict[str,Any],
	) -> Self:
		field_names = [field.name for field in dc.fields(cls)]
		
		parameters = dict()
		for field_name in field_names:
			arg_string = f"{cls._arg_prefix}.{field_name}"
			parameters[field_name] = arg_dict.pop(arg_string, dc.MISSING)
		
		for k,v in parameters.items():
			if v is dc.MISSING:
				arg_string = f"{cls._arg_prefix}.no_{k}"
				parameters[k] = not arg_dict.pop(arg_string, False)
		
		for delete_key in (k for k,v in parameters.items() if v==dc.MISSING):
			del parameters[delete_key]
		
		instance = cls(**parameters)
		instance.conversion_chain = instance.conversion_chain.split(',')
		
		return instance
		
		

	def copy(self, **attrs : dict[str,Any]) -> Self:
		field_names = tuple(f.name for f in dc.fields(self))
		raw_copy = self.__class__()
		for field_name in field_names:
			setattr(raw_copy, field_name, attrs.get(field_name, getattr(self, field_name)))
		
		return raw_copy