from dataclasses import dataclass, field
from abc import ABC, abstractmethod

import pandas as pd


@dataclass
class TransformResult:
    df: pd.DataFrame
    uploaded_rows: int
    processed_rows: int
    dropped_rows: int
    duplicate_rows: int
    quality_metrics: dict = field(default_factory=dict)


class BaseTransformer(ABC):
    @abstractmethod
    def transform(self, df: pd.DataFrame) -> TransformResult:
        ...
