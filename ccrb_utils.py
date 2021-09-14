import pandas as pd
import numpy as np
import datetime
from datetime import datetime

##############################
# Back-end file for data processing, manipulation,
# and segmentation for the ccrb bokeh data visualzation


def load_ccrb_data(file):
    ccrb_df = pd.read_csv(file, parse_dates=["Incident.Date"])
    ccrb_df = ccrb_df.drop(['Unnamed: 0', 'AsOfDate', 'Unique.Id',
                            'First.Name', 'Last.Name'],
                           axis=1)
    ccrb_df.columns = ccrb_df.columns.str.replace(".","_")
    ccrb_df.rename(columns={"NYPDDisposition":"NYPD_disposition", 
                            "PenaltyDesc":"Penalty", 
                           "ShieldNo":"Shield_No"}, 
                  inplace=True)
    ccrb_df.columns = ccrb_df.columns.str.lower()
    ccrb_df.dropna(subset=['incident_date'], inplace=True)
    ccrb_df.incident_date = pd.to_datetime(ccrb_df.incident_date,
                                           format='%Y-%m-%d')

    # There is one typo in the set (I assume) that is labeled
    # as the date 1900-02-01
    ccrb_df= ccrb_df[ccrb_df["incident_date"]>"1984-01-01"]
    return ccrb_df

# Format groupby objects
def format_groupby(df, groups_list):
    df= df.groupby(groups_list) \
        .count()['complaint_id'] \
        .reset_index() \
        .rename(columns={"complaint_id":"count"})
    return df

# Make a one-year rolling total for complaints
def make_rolling_sum(df, idx, drop_command=True):
    if drop_command:
        df = df.set_index('incident_date') \
            .drop('command', axis=1) \
            .reindex(idx, fill_value=0) \
            .rolling(window=365) \
            .sum() \
            .reset_index()
        df.rename(columns={"count":'total', "index":"Date"},
                       inplace=True)
        return df
    else:
        df = df.set_index('incident_date') \
            .reindex(idx, fill_value=0) \
            .rolling(window=365) \
            .sum() \
            .reset_index()
        df.rename(columns={"index":'Date', "count":"total"},
                       inplace=True)
        return df

# function to identify when an officer leaves
def make_officer_depart(row, depart_list, time, remain=False):
    if row in depart_list:
        label = f"departure {time}"
    elif remain: 
        label = row
    else: label = "remain"
    return label

def make_pct_outcome(df, date_range, disposition, filter_substan=False):
    new_start, new_end = date_range
    groups = ['command', disposition]
    
    if filter_substan:
        df = df[df.board_disposition == "substantiated"]
        
    substan_pct = df[(df['incident_date'] >= new_start) & \
                     (df['incident_date'] <= new_end)]
    substan_pct = format_groupby(substan_pct, groups)
    
    return substan_pct

def make_agg_outcome(df, date_range, disposition, view, filter_substan=False):
    view = view.title()
    new_start, new_end = date_range
    groups = [disposition]
    
    if filter_substan:
        df = df[df.board_disposition == "substantiated"]
    
    substan_agg = df[(df['incident_date'] >= new_start) & \
                     (df['incident_date'] <= new_end)]
    substan_agg = format_groupby(substan_agg, groups)
    
    substan_agg['command'] = f"{view} Wide"
    return substan_agg

def make_board_bins(row, depart_list, unident_list):
    if row in depart_list:
        label = f"officer departure"
    elif row in unident_list: 
        label = f"unavailable/unidentified"
    else: label = row
    return label

def make_nypd_bins(row, no_penalty_list, other_list):
    if row in no_penalty_list:
        label = "no penalty"
    elif row in other_list:
        if str(row).lower() == 'nan':
            label = "unknown"
        else:
            label = "other/no recommendation"
    else: label = row
    return label

def make_penalty_bins(row, outcome_list):
    if row in outcome_list:
        if row == 'no penalty':
            label = "no penalty"
        else: label = "unknown"
    else: label = row
    return label

################################ Matplotlib Helpers #############
# Below are functions that help with visualizing this data using
# Matplotlib and Seaborn. The functions handle more data clean up
# as well as back-end functions for formatting plots in a meaningful
# way since plt/sns require so much low-level interaction to make 
# plots informative to no techincal folks. 

def fix_instructions(row):
    if "instruction" in row:
        return "instructions"
    else: return row
    
def make_condensed_penalty(row):
    if 'nan' in row:
        return "unknown"
    if "not guilty" in row:
        return "no penalty"
    if "charges terminated - dct" in row:
        return "no penalty"
    else: return row

def strip_sexual_harass(row):
    if "sexually harass - " in row:
        return row.lstrip("$sexually harass^").strip("-")
    else: return row
    
def make_bar_annotation(ax, **kwargs):
    """
    Function to add bar plot annotations. 
    Agruements: 
        ax: axis plot in seaborn of matplotlib

    Returns: None
    """
    for rect in ax.patches:
        y_value = rect.get_height()
        x_value = rect.get_x() + rect.get_width() / 2

        va = 'bottom'
        spacing=2

        label = make_annotation_format(y_value, **kwargs)

        ax.annotate(
            label,                      
            (x_value, y_value),         
            xytext=(0, spacing),          
            textcoords="offset points", 
            ha='center',                
            va=va, 
            fontsize=12)    
        
def make_annotation_format(y_value, **kwargs):
    """        
    Function to format annotations for plots

    Arguements: None

    Returns: label, formatted using kwargs
    """

    formats = ['money', 'int', 'round_0', 'round_1', 'round_2']
    if not any(style in kwargs for style in formats):
        raise Exception(f'annotation formats must be one of {formats}')

    if 'money' in kwargs:
        label = f"${int(y_value):,}"

    if 'int' in kwargs:
        label = f"{float(y_value):.0f}"
        if 'money' in kwargs:
            label = f"${int(label):,}"

    if 'round_0' in kwargs:
        label = f"{y_value:.1f}"
        if 'money' in kwargs:
            label = f"${float(label):,}"

    if 'round_2' in kwargs:
        label = f"{y_value:.2f}"
        if 'money' in kwargs:
            label = f"${float(label):,}"
    return label


def make_annots(ax, hue=None, annot_labels=None, 
                annot_values=None, annot_x_value=None, **kwargs):
    """
    Function to make an x,y line plot from a pandas dataframe.

    Arguments: 
        hue: string, categorical fields associated with x,y data.
        annot_labels: list of string, categorical labels to display
        annot_values: list of floats, categorical values to display

    Returns: None
    """
    
    if annot_labels != None:
        for i in range(len(annot_labels)):
            ax.annotate(
            s=(f"{annot_labels[i].title()}:" \
                f"{make_annotation_format(annot_values[i],**kwargs)}"), 
                xy=(annot_x_value, annot_values[i]), 
                fontsize=12,
                xytext=(10,7),         
                textcoords="offset points"
                        )
# Add captioning function if desired.
#     if 'caption' in kwargs:
#         self._make_caption(**kwargs)

#     plt.legend(loc='upper left')
#     self._add_labels(ax)

