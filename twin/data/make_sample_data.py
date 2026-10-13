"""Creates a SAMPLE dataset so the project runs end-to-end if you don't have the real CSV yet.
Real hackathon file? Just put it in this folder as 06_employee_productivity_digital_twin.csv instead."""
import numpy as np, pandas as pd
rng = np.random.default_rng(42); n = 1000
df = pd.DataFrame({
    "Employee_ID": [f"E{1000+i}" for i in range(n)],
    "Age": rng.integers(21, 60, n),
    "Experience_Years": rng.integers(0, 30, n),
    "Attendance": rng.normal(90, 7, n).clip(55, 100).round(1),
    "Working_Hours": rng.normal(8, 1.2, n).clip(4, 12).round(1),
    "Tasks_Completed": rng.integers(1, 15, n),
    "Task_Delay_Count": rng.integers(0, 8, n),
    "Training_Hours": rng.integers(0, 20, n),
    "Meeting_Hours": rng.integers(0, 10, n),
    "Project_Count": rng.integers(1, 8, n),
    "Performance_Score": rng.normal(700, 150, n).clip(200, 1000).round(0),
    "Job_Satisfaction": rng.integers(1, 11, n),
})
s = (df.Tasks_Completed*0.5 + df.Performance_Score/200 + df.Attendance/25 + df.Job_Satisfaction*0.3
     - df.Task_Delay_Count*0.6 + rng.normal(0, 1, n))
df["Productivity_Level"] = pd.cut(s, [-99, s.quantile(.2), s.quantile(.8), 99], labels=["Low", "Moderate", "High"])
df.loc[rng.choice(n, 15, replace=False), "Training_Hours"] = np.nan
df.to_csv("06_employee_productivity_digital_twin.csv", index=False)
print("Sample dataset written:", df.shape)
