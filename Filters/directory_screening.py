import pandas as pd
from tensorflow.python.keras.models import load_model

from Filters.screening import FileFilter
import glob
from tqdm import tqdm

root_dir = "/home/mltest1/tmp/pycharm_project_883/Images/Parsed Dewetting 2020 for ML/thres_img"
model_dir = "/home/mltest1/tmp/pycharm_project_883/Data/Trained_Networks/2020-03-30--18-10/model.h5"
model = load_model(model_dir)
search_recursive = True

df_summary = pd.DataFrame(columns=["File Path", "Resolution", "Fail Reason", "Classification"])

all_files = [f for f in glob.glob(f"{root_dir}/**/*.ibw", recursive=search_recursive)]
for i, file in enumerate(tqdm(all_files)):
    filter = FileFilter()
    filter.assess_file(filepath=file, model=model, plot=False)

    df_summary.loc[i, ["File Path"]] = [file]
    df_summary.loc[i, ["Resolution"]] = [filter.image_res]
    df_summary.loc[i, ["Fail Reason"]] = [filter.fail_reason]
    df_summary.loc[i, ["Classification"]] = [filter.classification]


