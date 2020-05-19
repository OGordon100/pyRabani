import pandas as pd
from tensorflow.python.keras.models import load_model

from Filters.screening import FileFilter
import glob
from tqdm import tqdm

# image_dir = "/home/mltest1/tmp/pycharm_project_883/Images/Parsed Dewetting 2020 for ML/thres_img"
image_dir = "/media/mltest1/Dat Storage/Manu AFM CD Box"
cnn_dir = "/home/mltest1/tmp/pycharm_project_883/Data/Trained_Networks/2020-03-30--18-10/cnn_model.h5"
denoiser_dir = "/home/mltest1/tmp/pycharm_project_883/Data/Trained_Networks/2020-03-30--18-10/cnn_model.h5"

model = load_model(cnn_dir)
search_recursive = True

df_summary = pd.DataFrame(columns=["File Path", "Resolution", "Fail Reasons", "CNN Classification", "Euler Classification"])

all_files = [f for f in glob.glob(f"{image_dir}/**/*.ibw", recursive=search_recursive)]
t = tqdm(total=len(all_files), smoothing=True)
for i, file in enumerate(all_files):
    t.update(1)
    t.set_description(file[len(image_dir):])

    filter = FileFilter()
    filter.assess_file(filepath=file, cnn_model=model, plot=False, savedir="/home/mltest1/tmp/pycharm_project_883/Images/testfilter")

    df_summary.loc[i, ["File Path"]] = [file]
    df_summary.loc[i, ["Resolution"]] = [filter.image_res]
    df_summary.loc[i, ["Fail Reasons"]] = [filter.fail_reasons]
    df_summary.loc[i, ["CNN Classification"]] = [filter.CNN_classification]
    df_summary.loc[i, ["Euler Classification"]] = [filter.euler_classification]

df_summary.to_csv("/home/mltest1/tmp/pycharm_project_883/Images/BigParse.csv")


