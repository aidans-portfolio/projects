
# Aidan's Map App 
# Web App to highlight my favorite locations in DC, using Shiny for Python to display a map and table with filter options
# Nav menu with SQLalchemy adjustments


from shiny import App, render, ui, reactive
from shinywidgets import output_widget, render_widget
import pandas as pd
from ipyleaflet import Map, Marker, AwesomeIcon
from ipywidgets import HTML
import shinyswatch
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, DECIMAL, select
import pandas as pd
import shiny.experimental as x


#Create connection to Amazon RDS and pull table name

DB_URL = 'not-for-you'

engine = create_engine(DB_URL)

# Create metadata object to hold the table
metadata_obj = MetaData()

table_name = "cityName_table"


city_table = Table(
    table_name,
    metadata_obj,
    Column("loc_name", String(60), primary_key=True),
    Column("city_name", String(30), nullable=False),
    Column("loc_type", String(30), nullable=False),
    Column("type_special", String(30), nullable=False),
    Column("loc_address", String(120), nullable=False),
    Column("loc_vibe", String(30), nullable=False),
    Column("loc_rating", String(60), nullable=False),
    Column("latitude", DECIMAL(precision=16, scale=13), nullable=False),
    Column("longitude", DECIMAL(precision=16, scale=13), nullable=False),
    Column("loc_tags", String(60)),
    Column("loc_descr", String(50), nullable=False),
)


pull_table = city_table

# Create a select statement to query all data from the table
stmt = select([pull_table])


with engine.connect() as connection:
    result = connection.execute(stmt)
    query_results = result.fetchall()


df = pd.DataFrame(query_results, columns=result.keys())

#just a list of the column names, for reference and maybe future use
col_names = ['loc_name', 'city_name', 'loc_type', 'type_special', 'loc_address',
       'loc_vibe', 'loc_rating', 'latitude', 'longitude', 'loc_neighbor',
       'loc_tags', 'loc_descr']


#template for the html popup of the marker
html_temp="""
        <h3> {loc_name} </h3><br>
        Type: {loc_type}<br>
        Address: {address}<br>
        Tags: {tags}<br>
        Rating: {rate}<br>
        <i>{description}</i>
        """

#function to filter the dataframe by a keyword in a column
def Filter_DF(filt_by, dataframe, col_name):
    filter_word = filt_by.title()
    filt_df = dataframe[dataframe[col_name]==filter_word].reset_index()
    return(filt_df)
#end def

def create_map(dataframe):

    start_lat = (dataframe.latitude).mean()
    start_long = (dataframe.longitude).mean()
    start_coords = list([start_lat]+[start_long])

    #Create the map
    my_map = Map(center=start_coords, zoom=12)
    #use a for loop to go through the filtered DF and create a popup for each location
    for i in range(len(dataframe)):
        loc_lat = float(dataframe.latitude[i])
        loc_long = float(dataframe.longitude[i])
        loc_coords = tuple(list([loc_lat] + [loc_long]))
        
        #use html template created at the top and fill it with information from the dataframe
        html=html_temp.format(loc_name=dataframe.loc_name[i], loc_type = dataframe.loc_type[i],
                              address=dataframe.loc_address[i],tags=dataframe.loc_tags[i],
                              rate=dataframe.loc_rating[i], description=dataframe.loc_descr[i])
        #check to see what type of location, change icons to better match. Uses Font Awesome icons 
        if dataframe.loc_type[i]=="Bar":
            loc_icon = "fa-glass"
            loc_color = "blue"
        elif dataframe.loc_type[i]=="Food":
            loc_icon = "fa-cutlery"
            loc_color = "gray"
        else:
            loc_icon = "fa-globe"
            loc_color = "green"
            
        icon1 = AwesomeIcon(
            name=loc_icon,
            marker_color=loc_color,
            icon_color='white',
            spin=False
            )
        
        #create the marker and add it as a layer to the map
        marker = Marker(icon=icon1, location=loc_coords, draggable=False, title=dataframe.loc_name[i])
        message = HTML(html)
        marker.popup = message
        my_map.add_layer(marker);

    #Display the map
    return(my_map)

#themes I enjoy:
#cerulean, darkly, journal, sketchy, superhero, vapor

#beginning of shiny framework
#this creates the UI, and in order contains:
# ui.page_fluid() - makes a fluid page that resizes to browser size
# shinyswatch.theme.sketchy() - creates the theme, "sketchy" can be replaced with those I mentioned above
# ui.h2() - HTML header, sized to 2
# ui.input_radio_buttons() - create first filter options input, radio buttons to select All, Food, Bar, or Activity. Saves choice as string named input.select_type()
# ui.unput_text() - create second filter option input with a search bar. Creates string named input.text_search()
# ui.hr() - HTML line break, creates a thin line separating above and below UI objects
# output_widget() - output element of UI that shows the map created from the output_map function in the server section of app
# ui.hr() - same HTML line break as before
# ui.output_table() - outputs the table creates from out_table function in server section of app


temp_h2DC = ui.tags.h2("DC Favorites")
temp_h2Lon = ui.tags.h2("Other Favorites")

app_ui = ui.page_navbar(
    shinyswatch.theme.superhero(),
    #ui.nav_spacer(),
    ui.nav_menu(
            "Maps",
            ui.nav("DC", temp_h2DC),
            ui.nav("More to Come!", temp_h2Lon),
            "----",
            ui.nav_control(
                ui.a(
                    "Email Me",
                    href="mailto:aidan.olander@gmail.com",
                    target="_blank",
                )
            ),
            align='right',
        ),
    title="Aidan's Favorites",
    bg="#0062cc",
    inverse=True,
    id="navbar_id",
    
    footer=ui.div(
        ui.row(
        ui.column(9, ui.input_radio_buttons(
        id="select_type", label="What are you looking for?", choices={"All": "All", "Bar": "Bar", "Food": "Food", "Activity": "Activity"})),
        ui.column(3, ui.input_text("text_search", "Search locations", placeholder="Enter name, tags, etc.")),
    ),
        output_widget("output_map"),
        ui.hr(),
        ui.output_table(id="out_table")

    )
)


def server(input, output, session):

    #reactive calculation to create filtered dataframe to feed into each output
    @reactive.Calc
    def react_filter():
        if input.select_type() == "All":
            filtered_df = df
            is_present = filtered_df.apply(lambda row: any(input.text_search().lower() in str(value).lower() for value in row.values), axis=1)
            filtered_df = filtered_df[is_present]
        else:
            filtered_df = Filter_DF(input.select_type(), df, "loc_type")
            is_present = filtered_df.apply(lambda row: any(input.text_search().lower() in str(value).lower() for value in row.values), axis=1)
            filtered_df = filtered_df[is_present]
        return filtered_df
    
    
    #map output, done in a few steps. Eventually I want to clean this and make it into a a simple function above like Filter_DF
    @output
    @render_widget
    def output_map():
        if input.navbar_id() == "DC":
            map_df = react_filter().reset_index()
            m = create_map(map_df)
            return m
        else:
            center_cord = (51.505781880507335, -0.11670485073523044)
            m = Map(center=center_cord, zoom=12)
            return m

    


    @output
    @render.table
    def out_table():
        out_DF = react_filter()
        columns_to_drop = ['loc_vibe', 'city_name','type_special', 'latitude', 'longitude']
        out_DF = out_DF.drop(columns=columns_to_drop)
        out_DF.rename(columns={'loc_name': 'Name', 'loc_type': 'Type', 'loc_address': 'Address',
                                    'loc_rating': 'Rating', 'loc_descr': 'Description','loc_tags': 'Tags' }, inplace=True)
        return out_DF

#last part is connecting the server and UI, creating the app
app = App(app_ui, server)
