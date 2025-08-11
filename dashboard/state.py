import param
import pandas as pd

class DashboardState(param.Parameterized):
    # Data
    daily_df: pd.DataFrame = param.Parameter()
    monthly_df: pd.DataFrame = param.Parameter()
    dividends_df: pd.DataFrame = param.Parameter()
    metadata_df: pd.DataFrame = param.Parameter()
    kpis: dict = param.Dict(default={})

    # Reactive parameters
    symbols = param.ListSelector(default=[], objects=[])
    date_range = param.Tuple()
    heatmap_palette = param.ObjectSelector(default="imola", objects=[])

    def set_defaults(self):
        idx = self.daily_df.index
        self.date_range = (idx.min(), idx.max())
        all_symbols = sorted([c.replace("val_", "") for c in self.daily_df.columns if c.startswith("val_")])
        self.param['symbols'].objects = all_symbols
        self.symbols = all_symbols[:5]
        # heatmap palette options filled by widgets.py (depends on config.CRAMERI)

        # Provide a minimal allowed set for heatmap_palette so direct use is safe.
        if not self.param['heatmap_palette'].objects:
            self.param['heatmap_palette'].objects = ["imola"]
            self.heatmap_palette = "imola"
