import pandas as pd
import numpy as np
import datetime
from functools import partial
from datetime import datetime
from bokeh.plotting import figure
from bokeh.models import ColumnDataSource, Dropdown, DatePicker
from bokeh.models import HoverTool, FactorRange, Div, Select
from bokeh.models import Legend, CDSView, GroupFilter
from bokeh.models import BasicTicker, ColorBar, LinearColorMapper
from bokeh.layouts import row, column, layout
from bokeh.transform import dodge, transform
from bokeh.io import curdoc
from bokeh.palettes import colorblind, Turbo256, Greys256

from ccrb_utils import *

### TO RUN LOCALLY
# have bokeh 2.2.3 (newest) and pandas
# use the terminal in this directory and type:
# `bokeh serve --show main_pres.py`

# DATA PREP
# see ccrb_utils.py for details load_ccrb_data() function
colors = colorblind["Colorblind"][7]
git_file = "ccrb_clean"
ccrb_df = load_ccrb_data(git_file)

# Fill in the dates between complaints with zero values. 
start_date = ccrb_df.incident_date.min()
end_date = ccrb_df.incident_date.max()

idx = pd.date_range(start=start_date, 
                   end=end_date)

# Precinct list (added an Upper East Side station for reference)
# There is no 51 (riverdale) precinct - it merged with the 52nd.
command_list = ["NARCBBX", "WARRSEC", "013 PCT"]+ \
               [f"04{i} PCT" for i in range(10)]+ \
               [f"05{k} PCT" for k in [0,2]]   
menu_option = ["Narcotics BX","Warrant Service","13th Precinct (EV)"]+ \
              [f"4{i} Precinct" for i in range(10)]+ \
              [f"5{k} Precinct" for k in [0,2]]

# MENU FOR DROPDOWN
menu = [(i, k) for i, k in zip(menu_option, command_list)]
dropdown = Dropdown(label="Select Precinct",
                    button_type="warning",
                    menu=menu,
                    max_width=1000)

# Establish a plot prior to selection
pct = command_list[0]
for i in menu:
    if pct in i:
        pct_title = i[0]
# pct_title is the decoded command name. 
# Default is NARCBBX

# ALL CITY PLOT
# City wide trend for complaints
# make data source
all_city_df = format_groupby(ccrb_df, ["incident_date"])
all_city_df = make_rolling_sum(all_city_df, idx, drop_command=False)

all_city_source = ColumnDataSource(all_city_df)

a = figure(title = f"One Year Rolling Total City Wide",
           x_axis_label = "Date", 
           y_axis_label = "Cumulative Total Complaints", 
           x_axis_type='datetime', 
           plot_width = 1000,
           plot_height = 300,
           toolbar_location = 'above',
           tools='box_zoom, reset')
a.circle(x='Date', y='total', size=2,
       color=colors[4], 
       source=all_city_source)


# Create rolling total dataframe
groups = ["incident_date", "command"]
rolling_df = ccrb_df[ccrb_df['command'] == pct]
rolling_df = format_groupby(rolling_df,groups)
rolling_df = make_rolling_sum(rolling_df, idx, drop_command=True)

rolling_df['pct'] = pct
source= ColumnDataSource(rolling_df)

# FIGURE AND PLOT
b = figure(title = f"One Year Rolling Total for {pct_title}",
           x_axis_label = "Date", 
           y_axis_label = "Cumulative Total Complaints", 
           x_axis_type='datetime', 
           plot_width = 1000,
           plot_height = 400,
           toolbar_location = 'above',
           tools='pan, box_zoom, reset')
b.circle(x='Date', y='total', size=2,
             color=colors[4], 
             source=source)

# Make interaction
def update_plot(event):
    # Reform data for selection
    pct = event.item
    groups = ["incident_date", "command"]
    rolling_df = ccrb_df[ccrb_df['command'] == pct]
    rolling_df = format_groupby(rolling_df,groups)
    rolling_df = make_rolling_sum(rolling_df, idx, drop_command=True)
    new_df = rolling_df.loc[:, ['Date', "total"]]
    new_df['pct'] = pct
    source.data = new_df
    for i in menu:
        if pct in i:
            b.title.text = f"One Year Rolling Total for {i[0]}"

dropdown.on_click(update_plot)

# TOOLTIPS and HOVERTOOL
hover_glyph = b.circle(x='Date', y='total',
                       source=source,
                       size=5, alpha=0,
                       hover_fill_color='red',
                       hover_alpha=0.9)

tooltips = [('Total', '@total'),
            ('Date', "@Date{%Y-%m-%d}")]

b.add_tools(HoverTool(tooltips=tooltips,
                       mode='mouse',
                       renderers=[hover_glyph],
                       formatters={'@Date':'datetime', }))

## FADO BREAKDOWN
# Establish non-select plot
fado_list = ccrb_df.fado_type.unique()
rolling_list = []
fado_groups = ['incident_date','command','fado_type']
# Data source creation with rolling total

for fado in fado_list:
    rolling_fado = ccrb_df[ccrb_df['command'] == pct]
    rolling_fado = format_groupby(rolling_fado,fado_groups)
    rolling_fado = rolling_fado[(rolling_fado['command'] == pct) & \
                            (rolling_fado['fado_type'] == fado)]
    rolling_fado = make_rolling_sum(rolling_fado, idx)
    rolling_fado['fado'] = fado
    rolling_list.append(rolling_fado)
fado_df = pd.concat(rolling_list, axis=0) 
fado_source = ColumnDataSource(fado_df)

# Figure
c = figure(title = f"Complaint Breakdown for {pct_title}",
           x_axis_label = "Date", 
           y_axis_label = "Cumulative Total Complaints", 
           x_axis_type='datetime', 
           plot_width = 1000,
           plot_height = 400,
           toolbar_location = 'above',
           tools='pan, box_zoom, reset')

# Filter view for multiple plots
for fado in range(4):
    view=CDSView(source=fado_source,
                 filters=[GroupFilter(column_name='fado',
                                      group=fado_list[fado])])
    c.circle(x='Date', y='total', 
             size=2,
             color=colors[fado],
             legend_label=fado_list[fado],
             source=fado_source,
             view=view)
    # add hover tools for each fado type
    hover_glyph = c.circle(x='Date',y='total',
                       source=fado_source,
                       size=5, alpha=0,
                       hover_fill_color='red',
                       hover_alpha=0.9)
c.legend.location = "top_left"
c.legend.click_policy="hide"

# Make interaction  
def update_plot_fado(event):
    pct = event.item
    rolling_list = []
    # re compile data for precinct selection
    for fado in fado_list:
        rolling_fado = ccrb_df[ccrb_df['command'] == pct]
        rolling_fado = format_groupby(rolling_fado,fado_groups)
        rolling_fado = rolling_fado[(rolling_fado['command'] == pct) & \
                                (rolling_fado['fado_type'] == fado)]
        rolling_fado = make_rolling_sum(rolling_fado, idx)
        rolling_fado['fado'] = fado
        rolling_list.append(rolling_fado)
    fado_df = pd.concat(rolling_list, axis=0)
    fado_source.data = fado_df
    for i in menu:
        if pct in i:
            c.title.text = f"Complaint Breakdown for {i[0]}"

dropdown.on_click(update_plot_fado)

# HOVER AND TOOLTIPS
tooltips = [('Date', '@Date{%Y-%m-%d}'),
            ('Type', '@fado'),
            ('Total', '@total')]

c.add_tools(HoverTool(tooltips=tooltips,
                       mode='mouse',
                       renderers=[hover_glyph],
                       formatters={'@Date':'datetime', }))


## ALLEGATION BAR PLOTS
# Make Data Source
groups = ['command','fado_type','allegation']
alleg_type = ccrb_df[(ccrb_df['incident_date']>= start_date) & \
                     (ccrb_df['incident_date']<= end_date)]
alleg_type = format_groupby(alleg_type, groups)

# Set single data source for both bars
source_bars = ColumnDataSource(alleg_type)

# Data for both bar plots
bar_force= alleg_type[(alleg_type["fado_type"]=="Force") & \
              (alleg_type["command"]==pct)] \
                .sort_values("count")
bar_abuse= alleg_type[(alleg_type["fado_type"]=="Abuse of Authority") & \
              (alleg_type["command"]==pct)] \
                .sort_values("count")

# filter the data source with Views
view_force = CDSView(source=source_bars,
                 filters=[GroupFilter(column_name='fado_type',
                                      group="Force"), 
                         GroupFilter(column_name='command', 
                                     group=pct)])

# Force allegation plot calls
# Make x ranges for allegation types
x_range = bar_force.allegation.unique()
d = figure(x_range=x_range,
           plot_width=500, plot_height=500,
           title=f"Force Allegations {pct_title}",
           toolbar_location=None, tools="") 
d.vbar(x='allegation',
       top='count',
       source=source_bars,
       view=view_force,
       color=colors[4],
       line_color = 'white',
       hover_fill_color='red',
       hover_alpha=1.0,
       hover_line_color='gray')

d.xaxis.major_label_orientation = 1.1

# tooltips and hovertool
tooltips = [('Count', '@count'),
           ('Type', '@allegation')]
d.add_tools(HoverTool(tooltips = tooltips))


# Abuse of Authority Bar
x_range = bar_abuse.allegation.unique()
view_abuse = CDSView(source=source_bars,
                 filters=[GroupFilter(column_name='fado_type',
                                      group="Abuse of Authority"), 
                         GroupFilter(column_name='command', 
                                     group=pct)])
e = figure(x_range=x_range,
           plot_width=500, plot_height=500,
           title="Abuse of Authority Allegations",
           toolbar_location=None, tools="") 
e.vbar(x='allegation',
       top='count',
       source=source_bars,
       view=view_abuse,
       color=colors[4],
       line_color = 'white',
       hover_fill_color='red',
       hover_alpha=1.0,
       hover_line_color='gray')
e.xaxis.major_label_orientation = 1.1

# tooltips and hovers
tooltips = [('Count', '@count'), 
           ('Type', '@allegation')]
e.add_tools(HoverTool(tooltips = tooltips))

# Date Range Picker

date_pick_1 = DatePicker(title="Start Date",
                        value=start_date.date(),
                        max_width=200)
date_pick_2 = DatePicker(title="End Date",
                        value=end_date.date(),
                        max_width=200)

# Make interactions - precinct and date update
def update_plot_bar(event):
    pct = event.item
    view_abuse.filters[1] = GroupFilter(column_name='command', 
                                     group=pct)
    view_force.filters[1] = GroupFilter(column_name='command', 
                                     group=pct)
    for i in menu:
        if pct in i:
            d.title.text = f"Force Allegations {i[0]}"
            
dropdown.on_click(update_plot_bar)

def update_bar_date(attr, old, new):
    # Change start and end date based on selection
    new_start = date_pick_1.value
    new_end = date_pick_2.value
    # re-filter for new dates
    alleg_type = ccrb_df[(ccrb_df['incident_date'] >= new_start) & \
                         (ccrb_df['incident_date'] <= new_end)]
    alleg_type = format_groupby(alleg_type, groups)

    source_bars.data = alleg_type
    
date_pick_1.on_change("value", update_bar_date)
date_pick_2.on_change("value", update_bar_date)


## GROUPED BAR PLOT COMPLAINT LIFECYCLE
# A series of bar plots for city wide and bronx ccrb dispositions

# Bin categorical values for x range simplicity
leaves_list = ["subject retired", "subject resigned", "subject terminated"]
unident_list = ["complainant uncooperative", "complainant unavailable",
                "alleged victim unavailable", "victim unidentified",
                "officer(s) unidentified", "witness uncooperative",
                "alleged victim uncooperative"]
no_penalty_list = ["no disciplinary action-dup",
                   "no disciplinary action-dismissed",
                   "no disciplinary action-sol", "filed",
                   " retained, without discipline"]
other_list = ["retained, with discipline", " other", np.NaN, 0.0]
outcome_list = [np.NaN, "not guilty", 0.0]


pct_df = ccrb_df[ccrb_df['command'].isin(command_list)]

# Make the bins in disposition types see ccrb_utils.py for functions
pct_df.board_disposition = pct_df['board_disposition'] \
    .apply(lambda x: make_board_bins(x,
                                    leaves_list,
                                    unident_list))
pct_df.nypd_disposition = pct_df['nypd_disposition'] \
    .apply(lambda x: make_nypd_bins(x,
                                    no_penalty_list,
                                    other_list))
pct_df.penalty = pct_df['penalty'] \
    .apply(lambda x: make_penalty_bins(x,
                                       outcome_list))

# Define lists for iteration in plotting
dispositions = ['board_disposition', 'nypd_disposition', 'penalty']
new_start = date_pick_1.value
new_end = date_pick_2.value
date_range = new_start, new_end

sources = []
x_ranges = []

penalties = pct_df[pct_df.board_disposition == "substantiated"] \
                .nypd_disposition \
                .unique()
pen_menu = [i.strip(" ") for i in penalties]
menu_2 = [(i, k) for i, k in zip(pen_menu, penalties)]

penalty_drop = Select(title="Select NYPD Disposition",
                    value="guilty",
                    options=pen_menu,
                    max_width=1000)

# Make Data Sources for each disposition type
# stores x ranges and data sources for updaing
for dispo in dispositions:
    if dispo == "nypd_disposition":
        substan = True
        _pct = make_pct_outcome(pct_df, date_range,
                            disposition=dispo,
                            filter_substan=substan)
        _bx = make_agg_outcome(pct_df, date_range,
                            disposition=dispo,
                            view="Bronx",
                            filter_substan=substan)
    if dispo == "penalty":
        nypd_dispo = "guilty"
        penalty_df = pct_df[(pct_df.board_disposition == "substantiated") & \
                           (pct_df.nypd_disposition == nypd_dispo)]
        _pct = make_pct_outcome(penalty_df, date_range,
                               disposition=dispo)
        _bx = make_agg_outcome(penalty_df, date_range,
                              disposition=dispo,
                              view="Bronx")
    if dispo == "board_disposition": 
        _pct = make_pct_outcome(pct_df, date_range,
                            disposition=dispo)
        _bx = make_agg_outcome(pct_df, date_range,
                            disposition=dispo,
                            view="Bronx")
        
    df= pd.concat([_bx, _pct], axis=0)
    x_ranges.append(sorted(pct_df[dispo].unique()))
    sources.append(ColumnDataSource(df))

# Define data filters for plots based on the disposition type
# as well as precinct and bronx wide views. 
bx_views = [
    CDSView(source=sources[i], 
            filters=[GroupFilter(column_name='command',
                                group="Bronx Wide")])
    for i in range(len(dispositions))
]
pct_views = [
    CDSView(source=sources[i], 
            filters=[GroupFilter(column_name='command',
                                group=pct)])
    for i in range(len(dispositions))
]


# MAKE INTERACTIONS
def update_penalty(attr, old, new):
    new_start = date_pick_1.value
    new_end = date_pick_2.value
    date_range = new_start, new_end
    
    # recalculate the "penalty" data source given a NYPD disposition.
    # Values are calculated for all precincts
    nypd_dispo = new
    penalty_df = pct_df[(pct_df.board_disposition == "substantiated") & \
                           (pct_df.nypd_disposition == nypd_dispo)]
    _pct = make_pct_outcome(penalty_df, date_range,
                               disposition=dispo)
    _bx = make_agg_outcome(penalty_df, date_range,
                              disposition=dispo,
                              view="Bronx")
    new_dispo= pd.concat([_bx, _pct],
                          axis=0)
    sources[2].data = new_dispo
    
penalty_drop.on_change('value', update_penalty)

def update_dispo_pct(event):
    pct = event.item
    # make legend and title proper name i.e., 44 Precinct
    for i in menu:
        if pct in i:
            pct_title = i[0]
    # update filter views for selected precinct. 
    for i in range(len(dispositions)):
        pct_views[i].filters[0] = GroupFilter(column_name='command',
                                             group=pct)
        pct_views[i].filters[0] = GroupFilter(column_name='command',
                                             group=pct)
    # change legend label
    for i, j in enumerate(figures):
        j.legend.items[1].label = {'value': pct_title}

dropdown.on_click(update_dispo_pct)


def update_dispo_date(attr, old, new, disposition):
    new_start = date_pick_1.value
    new_end = date_pick_2.value
    date_range = new_start, new_end
    
    # re tabluate for updated plots based on date selection
    if disposition == "nypd_disposition":
        substan = True
        _pct = make_pct_outcome(pct_df, date_range,
                                disposition=disposition,
                                filter_substan=substan)
        _bx = make_agg_outcome(pct_df, date_range,
                               disposition=disposition,
                               filter_substan=substan,
                               view="Bronx")
    if disposition == "penalty":
        nypd_dispo = penalty_drop.value
        penalty_df = pct_df[(pct_df.board_disposition == "substantiated") & \
                           (pct_df.nypd_disposition == nypd_dispo)]
        _pct = make_pct_outcome(penalty_df, date_range,
                               disposition=dispo)
        _bx = make_agg_outcome(penalty_df, date_range,
                              disposition=dispo,
                              view="Bronx")
    if disposition == "board_disposition": 
        _pct = make_pct_outcome(pct_df, date_range,
                                disposition=disposition)
        _bx = make_agg_outcome(pct_df, date_range,
                               disposition=disposition,
                               view="Bronx")
    
    new_dispo= pd.concat([_bx, _pct],
                          axis=0)
    # update source data
    if disposition == "board_disposition":
        sources[0].data = new_dispo
    if disposition == "nypd_disposition":
        sources[1].data = new_dispo
    if disposition == "penalty":
        sources[2].data = new_dispo

# run the interaction for all disposition types and 
# reversable date selection
for dispo in dispositions:
    date_pick_1.on_change("value", partial(update_dispo_date,
                                      disposition=dispo))
    date_pick_2.on_change("value", partial(update_dispo_date,
                                      disposition=dispo))
    
# Grouped plotting calls
# list iterables for options
views_list = [bx_views, pct_views]
range_align = [-0.3, 0, 0.3]
legend_lables = ["Bronx Wide", pct_title]
title_labels = ["CCRB Disposition for Selected Date Range",
                "NYPD Disposition on Substantiated Claims",
                "Penalty for above Subtantiated Claims"]
width=0.3

# Generate three plots for each disposition
# each plot has three bar types
figures = []
for i, dispo in enumerate(dispositions):
    figure_ = figure(x_range=x_ranges[i],
                   plot_width=1000, plot_height=500,
                   title=title_labels[i],
                   toolbar_location = 'above',
                   tools='pan, box_zoom, reset')
    figures.append(figure_)

for i, j in enumerate(figures):
    for k in range(2):
        j.vbar(x=dodge(dispositions[i],
                       range_align[k],
                       range=j.x_range),
           top='count',
           source=sources[i],
           view=views_list[k][i],
           width=width,
           legend_label=legend_lables[k],
           line_color = 'white',
           hover_fill_color='red',
           hover_alpha=1.0,
           hover_line_color='gray',
           color=colors[k])
    
    j.xaxis.major_label_orientation = 0.5
    j.legend.location = "top_left"
    j.legend.click_policy="hide"

    # Hover and Tooltips
    disposition_tool = f'@{dispositions[i]}'
    tooltips = [('', '@command'),
                ('Total', '@count'),
                ('Disposition', disposition_tool)]

    j.add_tools(HoverTool(tooltips=tooltips,
                              mode='mouse'))

## HEAT MAP
# For all data across the city to give some view to the total pathways 
# to potential outcomes. 


x_tab = pd.crosstab(ccrb_df.nypd_disposition, ccrb_df.penalty)
data = pd.DataFrame(x_tab.stack(), columns=['rate']).reset_index()
heat_source = ColumnDataSource(data)
    
mapper = LinearColorMapper(palette=Turbo256,
                           low=data.rate.min(),
                           high=data.rate.max())

q = figure(plot_width=1000,
           plot_height=800, 
           title="Penalty and NYPD Disposition Co-occurrences",
           x_axis_label="NYPD Disposition",
           y_axis_label="Final Penalty",
           x_range=data.nypd_disposition.unique(),
           y_range=data.penalty.unique(),
           toolbar_location=None,
           tools="",
           x_axis_location="below",
           y_axis_location="right")

q.rect(x="nypd_disposition",
       y="penalty",
       width=1, height=1,
       source=heat_source,
       line_color=None,
       fill_color=transform('rate', mapper))

color_bar = ColorBar(color_mapper=mapper,
                     ticker=BasicTicker(desired_num_ticks=10),
                     label_standoff=7)

q.add_layout(color_bar, "left")
q.xaxis.major_label_orientation = 1.0

# Hover and Tooltips
tooltips = [('NYPD', '@nypd_disposition'),
            ('Penalty', '@penalty'),
            ('Count', '@rate')]

q.add_tools(HoverTool(tooltips=tooltips,
                      mode='mouse'))

    
    
# EXPLANATORY SECTIONS

div_title = Div(text="""<h1>CCRB Complaint Dashboard</h1>
NYCLU released complaints from 1985-2020""",
width=1000, height=100)

div_all_city= Div(text="""<br>
This is a view of the overall trend for complaints across the city.""",
width=250, height=300)

div_all_pct= Div(text="""<br>
The one year running total of complaints for the selected precinct.<br>
Use the box zoom tool on the upper right of the figure to narrow results.<br>
Hover over a point to see the running total for a given date.<br><br>
It is recommended to narrow the results before inspecting specific dates as <br>
every day is represented.""",
width=250, height=400)

div_pct_bdown= Div(text="""<br>
One year running total for each major complaint type.<br>
Click the legend to mute/unmute the complaint type.<br>
Use the toolbar to narrow results.""",
width=250, height=400)

div_alleg_types= Div(text="""<br>
Distribution of allegation types as described in the complaint<br>
for the selected date range and precinct.<br><br>
Use the date slider to narrow results and examine trends.""",
width=250, height=400)

div_alleg_details= Div(text= """<h2>Allegation Details</h2>
Distribution of offending practices.<br>
Use the date selection to narrow results for all following graphs""",
width=1000, height=100)

div_outcome_span= Div(text="""<h2>Complaint Lifecycle and Outcomes</h2>
Complaints come to the CCRB for investigation. The CCRB can make several determinations, including substantiating the claim. Once a claim is substantiated, the NYPD gets to weigh in on the case and make a recommendation for penalty. Penalties are decided by the Police Commissioner after the commissioner reviews the case.""",
width=1000, height=100)

div_board= Div(text="""<br>
The CCRB board has a disposition on the complaint after investigating the claim.<br>
<b>Key Terms</b><br>
Substantiated: The claim was determined to have a perponderance of evidence in support.<br>
Unsubstantiated: The claim did not have a perponderance of evidence in support.<br>
Unfounded: A perponderance of evidences supports that the claim did not occur.<br>
Exonerated: The claim did occur but was not improper.<br>
Unidentified: Either the officer or claimant were unable to be identified.<br>
Officer Departure: The officer in question resigns, retires, or is terminated prior to board finding.<br>
Complanit Withdrawn: The individual making the complaint withdraws the claim.<br><br>
Use the box zoom and pan tools to narrow results and legend to mute views.""",
width=250, height=400)

div_nypd= Div(text="""<br>
The NYPD disposition on the complaint.<br>
The NYPD performs its own investigation of the claim and makes a recommendation for outcome. This can be simply a guilty or not guilty disposition or they can make specific penalty recommendations.<br><br>
Use the box zoom and pan tools to narrow results and legend to mute views.""",
width=250, height=400)

div_penalty_span = Div(text="""<h3>Final Penalty</h3>
Once the CCRB substantiated a claim and the NYPD investigates and determines a disposition, the Police Commissioner determines the penalty, if any.<br>

Use the selection dropdown to see final penalty results in conjunction with NYPD dispositions on CCRB substantiated claims. Use the box zoom and pan tools to narrow results and legend to mute views.
""",
width = 1000, height=130)

div_penalty= Div(text="""<br>
The penalty as a result of the complaint.<br>
The distribution of outcomes includes city, bronx only, and precinct values.<br><br>
Use the box zoom and pan tools to narrow results and legend to mute views.""",
width=250, height=400)

# LAYOUT
title = row([div_title])
row1 = row([a,div_all_city])
row2 = row([b, div_all_pct])
row3 = row([c, div_pct_bdown])
row4 = row([d, e, div_alleg_types])
row5 = row([figures[0], div_board])
row6 = row([figures[1], div_nypd])
row7 = row([figures[2], div_penalty])
row8 = row([q])

picker_row = row([date_pick_1, date_pick_2])

layout = column([title,dropdown, row1, row2,
                 row3, div_alleg_details,
                 picker_row, row4, div_outcome_span, 
                 row5, row6, div_penalty_span,
                 penalty_drop, row7,row8],
                margin=(0,0,0,20))
curdoc().add_root(layout)
