from convert_and_preprocess import get_CT_paths, process_scans, init_dirs
import os

to_scan = "/Users/gravo/Downloads/P_10/20160530 232112 [ - CT head]"
paths   = get_CT_paths(to_scan, lambda x: not x.startswith("."))

init_dirs()
process_scans(paths, "", "NCCT")
process_scans(paths, "", "CTA")
