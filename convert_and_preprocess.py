# Dependencies:
#  - dcm2niix
#  - pydicom
#  - nibabel
#  - pandas
#  - fsl
import os, re, pydicom, threading
import nibabel as nib
import pandas as pd

# variables - feel free to change
report  = "ct-report.csv" # name of the report csv 
to_scan = "/Users/gravo/Google Drive/MEIC-A/2° ANO/tese/data/TAC_gravo" # absolute path to the directory 
                                                                        # where the DICOM scans to be 
                                                                        # converted are

# constants - shouldn't need to change any of these variables
FLIRT       = "/usr/local/fsl/bin/flirt"
REF         = "/usr/local/fsl/data/standard/MNI152_T1_{}mm"
OPTIONS     = "-bins 256 -cost corratio -searchrx -90 90 -searchry -90 90 -searchrz -90 90 -dof 12  -interp trilinear"
INTENSITY   = 0.01


stop = False
def key_capture_thread():
    global stop
    input()
    stop = True


def is_CT(slice):
    '''
    Input:  slice, a pydicom.dataset.FileDataset object
    Output: boolean; True if the slice is from a NCCT or CTA scan; False otherwise
    Notes:  Scan options (0018,0022) equal to AXIAL MODE and HELICAL MODE have weird
            slice thicknesses like 0.625, 2.5 and 5mm. 
    '''
    return ((("0002","0002") in slice.file_meta) and (slice.file_meta["0002","0002"].value.name == "CT Image Storage") and
            (("0008","0008") in slice) and all([v in slice["0008","0008"].value for v in ("ORIGINAL", "AXIAL")]) and
            (("0028","0010") in slice) and (slice["0028","0010"].value == 512) and
            (("0028","0011") in slice) and (slice["0028","0011"].value == 512))

            
def is_CTA(slice):
    '''
    Input:  slice, a pydicom.dataset.FileDataset object
    Output: boolean; True if the slice is from a CTA scan; False otherwise
    Notes:  assumes the input is a CT, i.e. is_CT(slice) is True
    '''
    return ((("0018","0010") in slice) and
            (("0018","1040") in slice) and
            (("0018","1041") in slice) and
            (("0018","1046") in slice) and
            (("0018","1049") in slice))


expr = re.compile(r"^([A-Z0-9]+)$")
def list_content(path = None, cond = lambda x: expr.search(x)):
    '''
    Input:  path, a string
            cond, a function that takes a string and outputs a boolean
    Output: list with the files and directories of the path specified in the input, whose name 
            satisfy the condition specified by the cond function. By default, only
            sequences of numbers and capital letters are accepted.
    '''
    return [c for c in os.listdir(path) if cond(c)]

    
def init_dirs():
    '''
    Creates the folders where the processed scans and respective metadata will be stored
    '''
    if not os.path.isdir("NCCT"):
        os.mkdir("NCCT")
        os.mkdir("NCCT/metadata")
    if not os.path.isdir("CTA"):
        os.mkdir("CTA")
        os.mkdir("CTA/metadata")


def init_patient_list():
    '''
    Output: list with the ids of the patients whose scans have already been processed (and
            therefore will be skipped)
    '''
    if os.path.isfile(report):
        return [str(d) for d in pd.read_csv(report)["idProcessoLocal"].values]
    return []

    
def get_CT_paths(dir, cond = lambda x: expr.search(x)):
    '''
    Input:  dir, a string specifying a directory
    Output: dictionary with one entry with the list of the NCCT scans directories 
            (and their thickness) and another with the list of the CTA scans directories 
            (and their thickness), found inside the specified directory in the argument
    '''
    output = {"NCCT":[], "CTA":[], "notes": ""}
    for scan in list_content(dir, cond = cond):
        scan    = dir+"/"+scan
        slices  = list_content(scan, cond = cond)
        if len(slices) <= 10: continue # any scan with 10 slices or less can immediately discarded. 10 is an arbitraty threshold, increase it for more aggressive 
        slice = pydicom.dcmread(scan+"/"+slices[0]) 
        if is_CT(slice):
            thickness = slice["0018","0050"].value                
            if is_CTA(slice):
                if thickness > 2:
                    output["notes"] += f"CTA exists but thickness={thickness}mm. "
                else:
                    output["CTA"].append( (scan,thickness) )
            else:
                if thickness > 2:
                    output["notes"] += f"NCCT exists but thickness={thickness}mm. "
                else:
                    output["NCCT"].append( (scan,thickness) )
    return output

    
def dcm_to_nii(path, ct_type, patient, scan_id):
    '''
    Input:  path, a string with the absolute path to the DICOM directory where the 
            scan slices to be converted to a single NIfTI file are
            ct_type, a string, either "NCCT" or "CTA", specifying the type of the
            scan that will be converted
            patient, a string with the patient id (i.e. idProcessoLocal)
            scan_id, a string with the scan id
    Output: string with the relative path to the newly created NIfTI file
    Notes:  Conversion is done with dcm2niix. The used flags are:
                -v n = no verbose
                -o output dir
                -z n = no compress
                -f output filename
                last argument = path to DICOM
            See more here: https://manpages.ubuntu.com/manpages/bionic/man1/dcm2niix.1.html
    '''
    outfile = f"{patient}-{scan_id}"
    os.system(f'dcm2niix    -v n    -o {ct_type}    -z n    -f "{outfile}"    "{path}"')
    outfile = outfile.replace(" ", "_")
    os.system(f'mv "{ct_type}/{outfile}".json {ct_type}/metadata/{outfile}.json')
    return f"{ct_type}/{outfile}.nii"

    
def process_scans(paths, patient, ct_type):
    '''
    Behaviour:  processes the scans of a given type of a given patient. Some patients
                may have two or more NCCTs, for example
    Input:      paths, a dictionary with the structure described in the get_CT_paths' output
                patient, a string with the patient id (i.e. idProcessoLocal)
                ct_type, a string, either "NCCT" or "CTA", specifying the type of the scans
    Output:     a string with the scan ids processed and their respective original and 
                current slice thickness. This string will be added to the report csv
    '''
    if len(paths[ct_type]) == 0:
        return ","
    ids         = '"'
    thicc       = '"'
    for path,thickness in paths[ct_type]:
        scan_id   = path.split("/")[-1]
        new_thicc = get_normalized_thickness(thickness)
        ids      += scan_id + ","
        thicc    += str(thickness) + "->" + str(new_thicc) + ","
        nii       = dcm_to_nii(path, ct_type, patient, scan_id)
        normalize_nii(nii, ct_type, new_thicc)
    return ids[:-1] + '",' + thicc[:-1] + '"'

    
def normalize_nii(nii_file, ct_type, thickness):
    '''
    Input:  nii_file, a string with the absolute path to the NIfTI file to be normalized
            ct_type, a string, either "NCCT" or "CTA", specifying the type of the
            thickness
            thickness, a float or string with a number in {0.5, 1, 2}
    '''
    fix_rotation(nii_file, thickness)
    skull_strip(nii_file, ct_type)
    
    
def get_normalized_thickness(thickness):
    '''
    Input:  float with the original thickness of a given scan
    Output: the highest thickness available in the MNI152_T1 spaces closest to the
            specified original thickness
    '''
    if thickness <= 0.5:    # shape = (364, 436, 364)
        return 0.5
    elif thickness <= 1:    # shape = (182, 218, 182)
        return 1
    elif thickness <= 2:    # shape = (91, 109, 91)
        return 2
    assert False, "No scan should have a slice thickness higher than 2mm"

    
def fix_rotation(nii_file, thickness):
    '''
    Behaviour:  if the file has more than 500 slices, it is truncated to only have
                500 slices. Then the scan is registered in a MNI152_T1 space using
                the FLIRT tool from FSL. Learn more about this tool here:
                https://fsl.fmrib.ox.ac.uk/fsl/fslwiki/FLIRT
    Input:      nii_file, a string with the absolute path to the NIfTI file
                thickness, a float or string with a number in {0.5, 1, 2}
    '''
    img = nib.load(nii_file)
    if img.shape[-1] > 500:
        img_array   = img.get_fdata()[:,:,-500:]
        img         = nib.Nifti1Image(img_array, affine = img.affine)
        os.system(f"rm {nii_file}")
        nib.save(img, nii_file)
    ref     = REF.format(thickness)
    outfile = f"{nii_file[:-4]}-fixed"
    os.system(f"{FLIRT} -in {nii_file} -ref {ref} -out {outfile}.nii -omat tmp.mat {OPTIONS}")
    os.system("rm tmp.mat")                     # delete mat file produced by the tool
    os.system(f"rm {nii_file}")                 # deletes the original NIfTI file
    os.system(f"gzip -d {outfile}.nii.gz")      # unzips the rotated NIfTI
    os.system(f"mv {outfile}.nii {nii_file}")   # renames the rotated NIfTI with the original name
    
    
def skull_strip(nii_file, ct_type):
    '''
    Behaviour:  removes the skull from the specified NIfTI file, using a algorithm
                adapted from Validated automatic brain extraction of head ct images,
                NeuroImage (2015) by Muschelli, Ullman, Mould, et al.
                WARNING: this function assumes the input NIfTI file was previously
                registered into a MNI152_T1 space (using the fix_rotation function, for example)
                and hasn't been tested when that's not the case.
    Input:      nii_file, a string with the absolute path to the NIfTI file
                ct_type, a string, either "NCCT" or "CTA", specifying the type of the scan
    '''
    outfile = f"{nii_file[:-4]}-ss" # ss = skull stripped
    if ct_type == "NCCT":
        os.system(f"fslmaths {nii_file} -thr 0.000000 -uthr 100.000000 {outfile}") # Thresholding Image to [0,100]
    else:
        os.system(f"fslmaths {nii_file} -thr -75.000000 -uthr 425.000000 {outfile}") # Thresholding Image to [-75,425]
    # Creating 0 - 100 mask to remask after filling
    os.system(f"fslmaths {outfile}  -bin   tmp")
    os.system("fslmaths tmp.nii.gz -bin -fillh tmp") 
    # Presmoothing image
    os.system(f"fslmaths {outfile}  -s 1 {outfile}")
    # Remasking Smoothed Image
    os.system(f"fslmaths {outfile} -mas tmp  {outfile}")
    # Running bet2
    os.system(f"bet2 {outfile} {outfile} -f {INTENSITY} -v")
    # Using fslfill to fill in any holes in mask 
    os.system(f"fslmaths {outfile} -bin -fillh {outfile}_mask")
    # Using the filled mask to mask original image
    os.system(f"fslmaths {nii_file} -mas {outfile}_mask  {outfile}")
    # cleanup
    os.system("rm tmp.nii.gz")
    os.system(f"rm {outfile}_mask.nii.gz")
    os.system(f"gzip -d {outfile}.nii.gz")
    os.system(f"rm {nii_file}")
    os.system(f"mv {outfile}.nii {nii_file}")
    

def init_report_csv(patients):
    '''
    Behaviour:  If there's a file already created with the scans report, this
                function opens it in append mode. Otherwise creates and opens 
                this report file
    Input:      The list of patients already processed
    Output:     The file opened
    '''
    if len(patients) == 0:
        f = open(report, "w+")
        f.write("idProcessoLocal,NCCT,NCCT thick,CTA,CTA thick,NCCT problems,CTA problems,notes\n")
    else:
        f = open(report, "a")
    return f
    
    
def process_dicom_dir(dir, patient, f):
    '''
    Behaviour:  Calls the other functions that actually parse the DICOM folder
                scans (get_CT_paths) and process their scans (process_scans). Also
                writes the info related to this processing in the report file.
    Input:      dir, an absolute path to a path to a DICOM folder
                patient, the identifier of the patient whose scans are in said DICOM folder
                f, the report file file
    '''
    for i in range(3):
        content = list_content(dir)
        assert len(content) == 1, f"This dir is weird: {dir}"
        dir += "/" + content[0]
    paths = get_CT_paths(dir)
    f.write(patient)
    f.write(",")
    f.write( process_scans(paths, patient, "NCCT") )
    f.write(",")
    f.write( process_scans(paths, patient, "CTA") )
    f.write(f",,,{paths['notes']}\n")


if __name__ == "__main__":
    print(" -== PRESS ENTER TO STOP THIS PROGRAM ==- ")
    print("It will stop as soon as it terminates the processing of the scan it is currently processing.")
    print("Afterwards you can restart the scan preprocessing at any time by simply calling this program again.\n")
    threading.Thread(target = key_capture_thread, args=(), name = "key_capture_thread", daemon = True).start()
    
    init_dirs()
    patients    = init_patient_list()
    f           = init_report_csv(patients)
        
    for patient in list_content(to_scan):
        print(f"\nPATIENT {patient}")
        if patient in patients:
            print("Skipped because already converted")
            continue
        dir = f"{to_scan}/{patient}/DICOM"
        if os.path.isdir(dir):
            process_dicom_dir(dir, patient, f)
        else:
            f.write(f"{patient},,,,,,,no DICOM folder\n")
        f.flush()
        print("----------------------------------------------------------------------------------------------------")
        if stop:
            break
    f.close()
    
