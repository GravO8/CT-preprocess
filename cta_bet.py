from tensorflow.keras.layers import UpSampling3D
import nibabel as nib
import pandas as pd
import os

def remove_extra_skull(patient):
    # get scan file names
    print(f"PATIENT {patient}")
    nccts       = ["/"+file for file in os.listdir("NCCT")]
    cta         = ["/"+file for file in os.listdir("CTA")]
    nccts       = [file for file in nccts if f"/{patient}-" in file]
    ctas        = [file for file in cta if f"/{patient}-" in file]
    if len(nccts) > 1:
        print("  more than 1 NCCT (ambiguity)")
    if len(ctas) > 1:
        print("  more than 1 CTA (ambiguity)")
    elif len(nccts) < 1:
        print("  no ref NCCT")
        return
    if (len(nccts) > 1) or (len(ctas) > 1): return
    NCCT_file   = f"NCCT/{nccts[0][1:]}"
    CTA_file    = ctas[0][1:]
    # get NCCT mask
    ncct_array              = nib.load(NCCT_file).get_fdata()
    shp                     = ncct_array.shape
    ncct_array.shape        = (1, shp[0], shp[1], shp[2], 1) # (batch size, dim1, dim2, dim3, channels)
    ncct_upsampled          = UpSampling3D(size = 2)(ncct_array).numpy()
    ncct_upsampled.shape    = (shp[0]*2, shp[1]*2, shp[2]*2)
    non_brain_mask          = ncct_upsampled <= 0
    # apply NCCT mask to the CTA
    cta_nii                     = nib.load(os.path.join("CTA",CTA_file))
    cta_array                   = cta_nii.get_fdata()
    cta_array[non_brain_mask]   = 0
    cta_clean                   = nib.Nifti1Image(cta_array, affine = cta_nii.affine)
    nib.save(cta_clean, os.path.join("CTA_clean",CTA_file))
    
def list_scans(path = None):
    return [os.path.join(path,scan) for scan in os.listdir(path) if scan.endswith(".nii")]
    
    
if __name__ == "__main__":
    if not os.path.isdir("CTA_clean"):
        os.mkdir("CTA_clean")
    
    patient_list = [] # list of patients whose CTA needs further cleaning
    for patient in patient_list:
        remove_extra_skull( patient )
