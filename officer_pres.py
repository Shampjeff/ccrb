import pandas as pd
import numpy as np
import datetime
#from functools import partial
from datetime import datetime
from bokeh.plotting import figure
from bokeh.models import ColumnDataSource,TextInput
from bokeh.models import HoverTool, FactorRange, Div, Select
from bokeh.models import Legend, CDSView, GroupFilter, MultiSelect
from bokeh.models import BasicTicker, ColorBar, LinearColorMapper
from bokeh.models import DataTable, TableColumn
from bokeh.layouts import row, column, layout
from bokeh.transform import dodge, transform, factor_cmap
from bokeh.io import curdoc
from bokeh.palettes import colorblind

from ccrb_utils import *

command_list = ["NARCBBX", "WARRSEC",]+ \
               [f"04{i} PCT" for i in range(10)]+ \
               [f"05{k} PCT" for k in [0,2]]   
menu_option = ["Narcotics BX","Warrant Service"]+ \
              [f"4{i} Precinct" for i in range(10)]+ \
              [f"5{k} Precinct" for k in [0,2]]
no_penalty_list = ["no disciplinary action-dup",
                   "no disciplinary action-dismissed",
                   "no disciplinary action-sol", "filed",
                   " retained, without discipline"]
other_list = ["retained, with discipline", " other",
              np.NaN, 0.0]
outcome_list = [np.NaN, "not guilty", 0.0]

# Should add these to the clean up file
# LOAD DATA
colors = colorblind["Colorblind"][7]
git_file = "ccrb_clean"
ccrb_df = load_ccrb_data(git_file)

ccrb_df.nypd_disposition = ccrb_df.nypd_disposition.apply(lambda x: make_nypd_bins(x,
                                    no_penalty_list,
                                    other_list))
ccrb_df.penalty = ccrb_df.penalty.apply(lambda x: make_penalty_bins(x,
                                       outcome_list))
ccrb_df.penalty = ccrb_df.penalty.apply(lambda x: make_condensed_penalty(x))
ccrb_df.penalty = ccrb_df.penalty.apply(lambda x: fix_instructions(x))
ccrb_df.full_name = ccrb_df.full_name.str.lower()
ccrb_df[["first", "last"]] = ccrb_df.full_name.str.split(" ",1, expand=True)
ccrb_df['year'] = ccrb_df.incident_date.dt.year
ccrb_df.shield_no = ccrb_df.shield_no.astype(int)

# NAME SUBSETTER - intital

first_input = TextInput(title="Officer Name", value="Dan Panta")
first_input.value = first_input.value.lower()
first,last = first_input.value.split(" ")

# filter data, prep titles

test_df = ccrb_df[(ccrb_df['first'].str.startswith(first)) & 
                    (ccrb_df['last'].str.startswith(last))]

refine_name = test_df.groupby(["full_name", 'shield_no']) \
                    .count()["rank"] \
                    .reset_index() \
                    .full_name \
                    .to_list()
shield_no = test_df.groupby(["full_name", 'shield_no']) \
                    .count()["rank"] \
                    .reset_index() \
                    .shield_no \
                    .to_list()

# name_options = [refine_name[i]+" "+str(shield_no[i]) 
#                 for i in range(len(refine_name))]
name_options = [(str(i),refine_name[i]+" "+str(shield_no[i])) 
                for i in range(len(refine_name))]


# SELECT TO REFINE

selected = MultiSelect(title="Refine Officer Search", options=name_options)

name_title = test_df.groupby("full_name") \
                    .count()["rank"] \
                    .reset_index() \
                    .full_name \
                    .to_list()[0]

name_dict = {"data": [name_title]}
name_source = ColumnDataSource(name_dict)


# MAKE INTERACTIONS

def update_name_options(attr, old, new):
    first_input.value = first_input.value.lower()
    new_first, new_last = first_input.value.split(" ")
    
    test_df = ccrb_df[(ccrb_df['first'].str.startswith(new_first)) & 
                    (ccrb_df['last'].str.startswith(new_last))]

    refine_name = test_df.groupby(["full_name", 'shield_no']) \
                    .count()["rank"] \
                    .reset_index() \
                    .full_name \
                    .to_list()
    shield_no = test_df.groupby(["full_name", 'shield_no']) \
                    .count()["rank"] \
                    .reset_index() \
                    .shield_no \
                    .to_list()

    name_options = [refine_name[i]+" "+str(shield_no[i]) 
                    for i in range(len(refine_name))]

    
    selected.options = [" "] + name_options
    
first_input.on_change("value", update_name_options)

# UPDATE NAME FOR REFINEMENT

first,last = first_input.value.split(" ")
test_df = ccrb_df[(ccrb_df['first'].str.startswith(first)) & 
                    (ccrb_df['last'].str.startswith(last))]


name_title = selected.value

# UPDATE PLOT FOR INTERACTION

def update_plots(attr, old, new):
    name_shield = selected.value.split(" ")
    new_name = name_shield[0]+" "+name_shield[1]
    shield = int(name_shield[2])
    
    # Data
    df = ccrb_df[(ccrb_df.full_name == new_name) &
                 (ccrb_df.shield_no == shield)]
    
    group1 = df.groupby(by=['fado_type','allegation']) \
                .count()["rank"] \
                .sort_values(ascending=False) \
                .reset_index()
    group1_source.data = group1
    
    x_tab = pd.crosstab(df.board_disposition, df.allegation)
    data1 = pd.DataFrame(x_tab.stack(), columns=['rate']).reset_index()
    heat_source_1.data = data1
    
    x_tab = pd.crosstab(df.penalty, df.allegation)
    data2 = pd.DataFrame(x_tab.stack(), columns=['rate']).reset_index()
    heat_source_2.data = data2
    
    line_plot = df.groupby(['year','allegation']).count()["rank"].reset_index()
    line_source.data = line_plot
    
    dt_test = df[(df.full_name == new_name)&
                (df.shield_no == shield)] \
                [["full_name", "shield_no", "rank", "command"]][:1] \
                .rename(columns={"full_name":"Officer Name",
                                 "shield_no": "Shield",
                                 "rank": "Rank",
                                 "command":"Precinct"})
    dt_source.data = dt_test
    
    # Titles and formatting
    b.title.text = f"{new_name}: Distribution of Allegations"
    b.x_range.factors = np.unique(group1_source.data['allegation']).tolist()
    
    c.title.text = f"{new_name}: Allegation and CCRB Disposition Co-occurrences"
    c.x_range.factors = np.unique(heat_source_1.data['board_disposition']).tolist()
    c.y_range.factors = np.unique(heat_source_1.data['allegation']).tolist()
    
    d.title.text = f"{new_name}: Allegation and Penalty Co-occurrences"
    d.x_range.factors = np.unique(heat_source_2.data['penalty']).tolist()
    d.y_range.factors = np.unique(heat_source_2.data['allegation']).tolist()
    
    e.title.text = f"{new_name}: Yearly Totals of Complaints"

    
selected.on_change("value", update_plots)

# Officer INFO

dt_test = test_df[(test_df.full_name == refine_name[0])&
        (test_df.shield_no == shield_no[0])] \
        [["full_name", "shield_no", "rank", "command"]][:1] \
        .rename(columns={"full_name":"Officer Name",
                        "shield_no": "Shield",
                        "rank": "Rank",
                        "command":"Precinct"})
dt_source = ColumnDataSource(dt_test)
columns = [
        TableColumn(field="Officer Name",),
        TableColumn(field="Shield"),
        TableColumn(field="Rank"),
        TableColumn(field="Precinct")
    ]
data_table = DataTable(source=dt_source, columns=columns, width=400, height=100)



# Allegations by FADO type

group1 = test_df.groupby(by=['fado_type','allegation']) \
                .count()["rank"] \
                .sort_values(ascending=False) \
                .reset_index()
index_cmap = factor_cmap('fado_type',
                         palette=colors, 
                         factors=group1.fado_type.unique(),
                         end=1)
group1_source = ColumnDataSource(group1)


b = figure(plot_width=800,
           plot_height=500, 
           title=f"{name_source.data['data'][0]}: Distribution of Allegations",
           y_axis_label ="Count",
           x_range=np.unique(group1_source.data["allegation"]),
           toolbar_location=None,
           tooltips=[("allegation", "@allegation"),
                     ("count", "@rank"),
                     ("FADO","@fado_type")])

b.vbar(x='allegation',
       top='rank',
       width=1,
       source=group1_source,
       line_color="white",
       fill_color=index_cmap,
       legend_field='fado_type')

b.y_range.start = 0
b.xgrid.grid_line_color = None
b.xaxis.axis_label = None
b.xaxis.major_label_orientation = 1.25
b.outline_line_color = None


# HEAT MAP - CCRB/ALLEGATION

x_tab = pd.crosstab(test_df.board_disposition, test_df.allegation)
data1 = pd.DataFrame(x_tab.stack(), columns=['rate']).reset_index()
heat_source_1 = ColumnDataSource(data1)
  
mapper = LinearColorMapper(palette=colors,
                           low=heat_source_1.data['rate'].min(),
                           high=heat_source_1.data['rate'].max())

c = figure(plot_width=800,
           plot_height=500, 
           title=f"{name_source.data['data'][0]}: Allegation and CCRB Disposition Co-occurrences",
           x_axis_label="CCRB Disposition",
           y_axis_label="Allegation",
           x_range=np.unique(heat_source_1.data['board_disposition']),
           y_range=np.unique(heat_source_1.data['allegation']),
           toolbar_location=None,
           tools="",
           x_axis_location="below",
           y_axis_location="left")

c.rect(x="board_disposition",
       y="allegation",
       width=1, height=1,
       source=heat_source_1,
       line_color="white",
       fill_color=transform('rate', mapper))

color_bar = ColorBar(color_mapper=mapper,
                     ticker=BasicTicker(desired_num_ticks=10),
                     label_standoff=7)

#c.add_layout(color_bar, "right")
c.xaxis.major_label_orientation = 0.5

# Hover and Tooltips
tooltips = [('CCRB', '@board_disposition'),
            ('Allegation', '@allegation'),
            ('Count', '@rate')]

c.add_tools(HoverTool(tooltips=tooltips,
                      mode='mouse'))



# HEAT MAP - PENALTY/ALLEGATION

x_tab = pd.crosstab(test_df.penalty, test_df.allegation)
data2 = pd.DataFrame(x_tab.stack(), columns=['rate']).reset_index()
heat_source_2 = ColumnDataSource(data2)
    
mapper = LinearColorMapper(palette=colors,
                           low=heat_source_2.data['rate'].min(),
                           high=heat_source_2.data['rate'].max())

d = figure(plot_width=800,
           plot_height=500, 
           title=f"{name_source.data['data'][0]}: Allegation and Final Penalty Co-occurrences",
           x_axis_label="Final Penalty",
           y_axis_label="Allegation",
           x_range=data2.penalty.unique(),
           y_range=data2.allegation.unique(),
           toolbar_location=None,
           tools="",
           x_axis_location="below",
           y_axis_location="left")

d.rect(x="penalty",
       y="allegation",
       width=1, height=1,
       source=heat_source_2,
       line_color="white",
       fill_color=transform('rate', mapper))

color_bar = ColorBar(color_mapper=mapper,
                     ticker=BasicTicker(desired_num_ticks=10),
                     label_standoff=7)

#d.add_layout(color_bar, "right")
d.xaxis.major_label_orientation = 0.5

# Hover and Tooltips
tooltips = [('Penalty', '@penalty'),
            ('Allegation', '@allegation'),
            ('Count', '@rate')]

d.add_tools(HoverTool(tooltips=tooltips,
                      mode='mouse'))



# YEARLY COUNT PLOT

line_plot = test_df.groupby(['year','allegation']).count()["rank"].reset_index()
line_source = ColumnDataSource(line_plot)

e = figure(title = f"{name_source.data['data'][0]}: Yearly Totals of Complaints",
           x_axis_label = "Year", 
           y_axis_label = "Count", 
           #x_axis_type='datetime', 
           plot_width = 800,
           plot_height = 500,
           toolbar_location = 'above',
           tools='box_zoom, reset')

e.vbar(x='year', top='rank',
       source=line_source,
       line_color="white")

# Hover and Tooltips
tooltips = [('Allegation', '@allegation'),
            ('Count', '@rank'),
            ('Year', '@year')]

e.add_tools(HoverTool(tooltips=tooltips,
                      mode='mouse'))

# TEXT SECTIONS

div_title = Div(text="""<h1>Officer Level CCRB Complaints</h1>
NYCLU released complaints from 1985-2020""",
width=1000, height=100)

div_search= Div(text="""<br>
Search by first and last name. <br>
<b>Tip 1: </b> Less is more when searching. <br>
<b>Tip 2: </b> Use capitals for proper nouns. <br>
The CCRB database may differ from other data sources. Officer names may not be consistent. <br>
<b>For example:</b> for Christopher McCormick search, 'Chris Mcc' then refine by name and/or shield number.""",
width=500, height=300)

div_yearlys= Div(text="""<br>
Yearly totals for complaints. <br> 
Hover over the bars for allegation details and specific year.""",
width=300, height=400)

div_fado_distrib= Div(text="""<br>
Distribution of allegations by FADO type. <br>
Hover over the bars for allegation details.""",
width=300, height=400)

div_board= Div(text="""<br>
The CCRB disposition and allegation co-occurences.<br>
<b>Key Terms</b><br>
<b>Substantiated:</b> The claim was determined to have a perponderance of evidence in support.<br>
<b>Unsubstantiated:</b> The claim did not have a perponderance of evidence in support.<br>
<b>Unfounded: </b> A perponderance of evidences supports that the claim did not occur.<br>
<b>Exonerated: </b>The claim did occur but was deemed within police guidelines.<br>
<b>Unidentified:</b> Either the officer or claimant were unable to be identified.<br>
<b>Officer Departure:</b> The officer in question resigns, retires, or is terminated prior to board finding.<br>
<b>Complaint Withdrawn: </b> The individual making the complaint withdraws the claim.<br><br>
Hover over the boxes for allegation details.""",
width=300, height=400)


div_penalty= Div(text="""<br>
The final penalty and allegation co-occurences.<br>
Penalties are ultimately determined by the police commissioner. <br>
<b> Unknown</b> is likely to be no penalty. All unsubstantiated claims have a blank (unknown) penalty fields. Some substantiated claims also have blank penalty fields. Claims with an explicit 'no penalty' where entered in the dataset as such. <br><br>
Hover over the boxes for allegation details
""",
width=300, height=400)


# LAYOUT

title = row([div_title])
row1 = row([e, div_yearlys])
row2 = row([b, div_fado_distrib])
row4 = row([c, div_board])
row5 = row([d, div_penalty])


name_picker_col = column([first_input, selected, data_table])
names_row = row([name_picker_col, div_search])

layout = column([title, names_row, row1, row2, row4, row5],
                margin=(50,0,0,50))
curdoc().add_root(layout)
#