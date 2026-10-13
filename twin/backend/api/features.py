"""Shared by training and the API (so the pickled pipeline can be loaded by Django)."""
import numpy as np
from sklearn.base import BaseEstimator, TransformerMixin

TARGET = "Productivity_Level"
ID_COL = "Employee_ID"
KNN_WEIGHTS = {"Attendance": 1.2, "Tasks_Completed": 1.5, "Task_Delay_Count": 1.3,
               "Training_Hours": 1.1, "Performance_Score": 1.5, "Job_Satisfaction": 1.2}

def add_features(df):
    df = df.copy()
    if {"Tasks_Completed", "Working_Hours"} <= set(df.columns):
        df["Task_Efficiency"] = df["Tasks_Completed"] / df["Working_Hours"].replace(0, np.nan)
    if {"Training_Hours", "Meeting_Hours"} <= set(df.columns):
        df["Training_Ratio"] = df["Training_Hours"] / (df["Training_Hours"] + df["Meeting_Hours"]).replace(0, np.nan)
    return df

class FeatureWeighter(BaseEstimator, TransformerMixin):
    """Multiplies scaled columns by weights (used by KNN). Works with one-hot columns too."""
    def __init__(self, weights=None):
        self.weights = weights
    def fit(self, X, y=None):
        w = self.weights or {}
        self.w_ = np.array([w.get(str(c).split("__", 1)[-1], 1.0) for c in X.columns])
        return self
    def transform(self, X):
        return np.asarray(X, dtype=float) * self.w_
