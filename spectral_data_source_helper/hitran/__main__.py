
import sys
import argparse as ap


from spectral_data_source_helper.dataset_selector import DatasetSelector, ALL_DATASET_SELECTOR, dataset_selector_factory
from spectral_data_source_helper.cfg.log import pkg_logger#, progress_lgr
from spectral_data_source_helper.cfg.const import (
	REPO_LOCAL,
	T_ref,
)

from .hitran import HITRAN_INDEX
#from .hitran import fetch_all_data


def select_datasets(
		dataset_selector : DatasetSelector,
):
	selected_dataset_holders = []
	for mol, isos in HITRAN_INDEX.items():
		for iso, dataset_holder in isos.items():
			if dataset_selector(mol, iso, 'HITRAN'):
				selected_dataset_holders.append(dataset_holder)
	return selected_dataset_holders

def action_index(
		dataset_selector : DatasetSelector,
		indent_0 : str = ' |  ',
		indent_1 : str = ' |- ',
):
	print('### HITRAN INDEX ###')
	msg = ''
	iso_msg = ''
	for mol, isos in HITRAN_INDEX.items():
		msg += f'{mol}\n'
		for iso, dataset_holder in isos.items():
			iso_msg += f'{indent_1}{iso}\n'
			iso_msg += f'{indent_0}{indent_1}PARTITION FUNCTION URL:\n'
			iso_msg += f'{indent_0}{indent_0}{indent_1}{dataset_holder.pf_data_url}\n'
			iso_msg += f'{indent_0}{indent_1}LINE DATA URL:\n'
			iso_msg += f'{indent_0}{indent_0}{indent_1}{dataset_holder.linedata_url}\n'
			iso_msg += f'{indent_0}{indent_1}BROADENER URLs:\n'
			for broadener, broad_url in dataset_holder.broadener_urls:
				iso_msg += f'{indent_0}{indent_0}{indent_1}{broadener:<8} : {broad_url}\n'
			
			if dataset_selector(mol, iso, 'HITRAN'):
				print(msg + iso_msg, end='')
				msg = ''
			iso_msg = ''
		msg = ''

	print('### END OF INDEX ###')
	return


def action_download(
		dataset_selector : DatasetSelector,
		refresh : bool
):
	dataset_holders = select_datasets(dataset_selector)
	n_datasets = len(dataset_holders)
	
	for i, dataset_holder in enumerate(dataset_holders):
		print(f'Downloading dataset [{i+1}/{n_datasets}]...')
		dataset_holder.cache_data(refresh=refresh)
		print(f'Dataset {i+1} downloaded.')
	
	return

if __name__=='__main__':

	parser = ap.ArgumentParser()
	
	parser.add_argument('-d', '--dataset_selector', type=dataset_selector_factory, metavar='<Dataset Selector>', help='String that selects dataset to operate upon. Format: "<mol>/<iso>/<dataset_name>", "*" can be used as a wild card, | can be use as alternation, spaces can separate multiple full selectors', default=ALL_DATASET_SELECTOR)
	
	
	subparsers = parser.add_subparsers(required=True)
	
	index_parser = subparsers.add_parser('index', help='Display the index of available datasets')
	index_parser.set_defaults(func = action_index)
	
	download_parser = subparsers.add_parser('download', help='Download the specified datasets')
	download_parser.set_defaults(func = action_download)
	download_parser.add_argument('-r', '--refresh', action='store_true', help='Refresh the cached data')

	
	args = parser.parse_args(sys.argv[1:])
	arg_dict = vars(args)
	
	
	# Deal with any arguments that should have default values but
	# are not playing nice.
	arg_not_present_sentinel = 'NOT_PRESENT'
	arg_defaults = {
		'temperature' : [T_ref],
	}
	
	
	for k,v in arg_defaults.items():
		if arg_dict.get(k, arg_not_present_sentinel) is None:
			arg_dict[k] = v
	
	func = arg_dict.pop('func')
	
	pkg_logger.info('## ARGUMENTS ##')
	for k,v in arg_dict.items():
		pkg_logger.info(f'    {k} : {v}')
	pkg_logger.info('##-----------##')
	
	
	func(**arg_dict)



