# Head CT preprocess

This is a pipeline for preprocessing computed tomography (CT) head scans. It converts them from DICOM format to NIfTI, **corrects their orientation and position, removes non brain tissue and performs HU windowing**.

![img1](https://user-images.githubusercontent.com/25433159/153930752-90bdc79c-2caa-4d47-8f72-a5d421a17547.png)

This pipeline **works for NCCT** (non contrast computed tomography) **and CTA** (computed tomography angiography) scans both.

## `test.py`

Don't now where to start? Try downloading and unziping the `Patient_Reports_16.zip` from [*The UCLH Stroke EIT Dataset*]( https://zenodo.org/record/1199398). Then, try to run the simple `test.py` script (don't forget to update de `to_scan` variable first). This will perform the preprocessing you see on the example images above and below.
![img2](https://user-images.githubusercontent.com/25433159/153930811-a30b02d5-3650-46fd-b880-5e8ba379c8c5.png)

These examples images are from the *Series 005 [CT - Thin Bone 1 0 Bone Sharp]* DICOM directory from the *UCLH Stroke EIT Dataset* (Goren, Nir; Dowrick, Thomas, Avery, James; Holder, David).

## `convert_and_preprocess.py`

This program is responsible for the following:

1. Conversion from DICOM to NIfTI, using [dcm2niix](https://github.com/rordenlab/dcm2niix).
2. Registration to a common brain atlas. This step normalizes the scans so they have the same position and orientation of a brain scan given as refference, using the [FLIRT tool from FSL](https://fsl.fmrib.ox.ac.uk/fsl/fslwiki/FLIRT). The refferences used are the `MNI152_T1` with a thickness that depends on the thickness of the input scan.
3. Remove non brain tissue. This step is done using an adapted version of the [algoritm](https://github.com/muschellij2/CT_BET/blob/master/Skull_Strip_Paper/CT_Skull_Strip_Example.sh) proposed in *Validated automatic brain extraction of head ct images*, NeuroImage (2015) by Muschelli, Ullman, Mould, et al. that uses the [BET tool from FSL](https://fsl.fmrib.ox.ac.uk/fsl/fslwiki/BET/FAQ). The algorithm proposed in this article was designed for NCCTs only. To apply it to CTA images, the first windowing step was updated to use a window in the range of [-75, 425]. 

You need to change the variable `to_scan` to specify the source DICOMs directory. This directory should have a layout similar to this:

```
to_scan
├── idProcessoLocal-1
│   ├── DICOM
│   │   └── 0000662F
│   │       └── AA923232
│   │           └── AA331FC9
│   │               ├── 00001AFC    # DICOM dir 1 of patient idProcessoLocal-1
│   │               │   ├── EE00D32D
│   │               │   ├── EE01CD46
│   │               │  ...
│   │               ├── 000031E3    # DICOM dir 2 of patient idProcessoLocal-1
│   │               │   ├── EE011BBA
│   │               │   ├── EE0CFE6F
......             ... ...
│   ├── README.TXT
│   └── SECTRA
│       └── CONTENT.XML
...
└── idProcessoLocal-N
    ├── DICOM
    │   └── 00002B78
    │       └── AAA1DB91
    │           └── AAFA3E4F
    │               ├── 00003FA1    # DICOM dir 1 of patient idProcessoLocal-N
    │               │   ├── EE02CAD0
    │               │   ├── EE036E90
   ...             ... ...
    ├── README.TXT
    └── SECTRA
        └── CONTENT.XML
```

**Note:** the `convert_and_preprocess.py` requires this very specific directory structure because this is the structure of the DICOM files I exported from a [SECTRA](https://sectra.com/) software program. If you have a different file structure, take a look at the script `test.py`.

## `cta_bet.py`

Further CTA skull strip. Some CTAs had some non brain tissue that persisted after step 3. These exams can be further cleaned by using a brain mask provided by the NCCT exam of the same patient. 

## `window_HU.py`

HU range windowing. NCCTs are normalized to be in the range [0,100] and CTAs to be in the range [0,200].

## Disclaimer

I am not an expert in medical imaging. From what I understand, DICOM headers vary from brand to brand, so the `is_CT` and `is_CTA` functions may not work as intended for your scans. 

For the CT images I had, 2mm thickness for the NCCT scans and 1mm thickness for the CTA scans worked the best. I am not sure if this pipeline produces decent results for other thickness values.

The pipeline is not perfect: sometimes the scans end up in the wrong orientation or with holes. 

## License

These programs are licensed under the MIT License - see the [LICENSE](https://github.com/GravO8/CT-preprocess/blob/master/LICENSE) file for details.
