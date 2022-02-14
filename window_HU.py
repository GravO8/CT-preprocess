import os
import nibabel as nib

def list_scans(path = None):
    return [os.path.join(path,scan) for scan in os.listdir(path) if scan.endswith(".nii")]

def normalize_HU(range, ct_type):
    min_, max_ = range
    for scan_id in list_scans(ct_type):
        print(f"NORMALIZING {scan_id}")
        scan_nii                        = nib.load(scan_id)
        scan_array                      = scan_nii.get_fdata()
        scan_array[scan_array <= min_]  = min_
        scan_array[scan_array >= max_]  = max_
        tmp                             = nib.Nifti1Image(scan_array, affine = scan_nii.affine)
        os.system(f"rm {scan_id}")
        nib.save(tmp, scan_id)
        
if __name__ == "__main__":
    print(f" ======================= NCCT =========================")
    normalize_HU((0,100), "NCCT")
    print(f" ======================= CTA =========================")
    normalize_HU((0,200), "CTA")
