import pandas as pd
import numpy as np

class AIQualityEngine:

    def __init__(self, df):
        self.df = df

    def detect_missing_patterns(self):

        missing = self.df.isnull().sum()

        return missing.sort_values(ascending=False)

    def detect_duplicates(self):

        return self.df.duplicated().sum()

    def detect_outliers(self):

        numeric = self.df.select_dtypes(include=np.number)

        outliers = {}

        for col in numeric:

            q1 = numeric[col].quantile(0.25)
            q3 = numeric[col].quantile(0.75)

            iqr = q3 - q1

            lower = q1 - 1.5 * iqr
            upper = q3 + 1.5 * iqr

            outliers[col] = ((numeric[col] < lower) | (numeric[col] > upper)).sum()

        return outliers

    def generate_quality_report(self):

        report = {
            "rows": self.df.shape[0],
            "columns": self.df.shape[1],
            "missing_values": self.detect_missing_patterns(),
            "duplicates": self.detect_duplicates(),
            "outliers": self.detect_outliers()
        }

        return report