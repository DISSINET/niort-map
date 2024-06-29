import json
import os, socket
import re
import streamlit as st
import sys

import pickle

import folium
import folium.plugins as fplugins
from streamlit_folium import st_folium, folium_static


import pandas as pd
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)
pd.options.mode.chained_assignment = None  # standard value is "warn"

import os, time, json
from tqdm import tqdm
from py2neo import Graph

# from loguru import logger
# https://github.com/Delgan/loguru ?
import logging
from streamlit.logger import get_logger
class StreamlitHandler(logging.Handler):
    def emit(self, record):
        try:
            msg = self.format(record)
            st.write(msg)  # Display log messages in Streamlit UI
            self.flush()
        except Exception:
            self.handleError(record)

logger = get_logger(__name__)
logger.handlers = [StreamlitHandler()]
logger.setLevel(logging.INFO)

# *************************************************************************************************************************

# basic data
sheet_url = "https://docs.google.com/spreadsheets/d/19uUtffNcSeYXw7kkocArkbfn_mRmTSsivpXUqkNo0-Y"
sheet_name = "persons_play"  # persons play contains "allegiation mood"

#data = d.load_df_from_gsheet("niort_projection", sheet_url, sheet_name, cleanByColumn="uuid", clean=True, fillna=True, )
data = pd.read_csv("Niort projections from ddb1-_neo4j - persons_play.csv")

# suspect
sheet_url = "https://docs.google.com/spreadsheets/d/19uUtffNcSeYXw7kkocArkbfn_mRmTSsivpXUqkNo0-Y"
sheet_name = "persons_play_suspects"  # persons play contains "allegiation mood"

#data_suspects = d.load_df_from_gsheet("niort_projection", sheet_url, sheet_name, cleanByColumn="uuid", clean=True, fillna=True, )

data_suspects = pd.read_csv("Niort projections from ddb1-_neo4j - persons_play_suspects.csv")


data = data.astype(str)
data_suspects = data_suspects.astype(str)

#st.dataframe(data)
#st.dataframe(data_suspects)
#st.stop()

def create_apattern(row, n):
    apattern = ""
    apattern += row[n + "_direct"][0]
    apattern += row[n + "_inherited"][0]
    apattern += row[n + "_direct_allegation"][0]
    apattern += row[n + "_inherited_allegation"][0]
    return apattern.replace("N","-")

data_suspects['charge1_s_pattern'] = data_suspects.apply(lambda x: create_apattern(x, "1"), axis=1)
data_suspects['charge2_s_pattern'] = data_suspects.apply(lambda x: create_apattern(x, "2"), axis=1)
data_suspects['charge3_s_pattern'] = data_suspects.apply(lambda x: create_apattern(x, "3"), axis=1)
data_suspects['charge4_s_pattern'] = data_suspects.apply(lambda x: create_apattern(x, "4"), axis=1)

# merging
data = data.set_index("name")
data_suspects = data_suspects.set_index("name")
data = data.merge(data_suspects[['charge1_s_pattern','charge2_s_pattern','charge3_s_pattern','charge4_s_pattern']], left_index=True, right_index=True)
data = data.reset_index()

if "1_direct_true" in data.columns:
    def create_apattern(row, n):
        apattern = ""
        apattern += row[n + "_direct_true"][0]
        apattern += row[n + "_inherited_true"][0]
        apattern += row[n + "_direct_allegation_true"][0]
        apattern += row[n + "_inherited_allegation_true"][0]

        return apattern


    data['charge1_pattern'] = data.apply(lambda x: create_apattern(x, "1"), axis=1)
    data['charge2_pattern'] = data.apply(lambda x: create_apattern(x, "2"), axis=1)
    data['charge3_pattern'] = data.apply(lambda x: create_apattern(x, "3"), axis=1)
    data['charge4_pattern'] = data.apply(lambda x: create_apattern(x, "4"), axis=1)


    data['response_group'] = data.apply(lambda x: x['charge1_pattern']+x['charge2_pattern']
                                                  +x['charge3_pattern']+x['charge4_pattern'], axis=1)
else:
    st.write(" ... charge info not loaded?")


st.set_page_config(
    #page_title="Niort Network",
    #page_icon="🧊",
    layout="wide",
    initial_sidebar_state="expanded")

if "coords" in data.columns:

    map_data = []

    intro = """
#  Map visualisation of the trial against Bernard Niort (1234-1235)

Part of the talk "The Heresy Trial of Bernard-Othon de Niort and His Family, c. 1234-1235:
 Computing Discourses of Guilt at the Dawn of the Languedocian Inquisition" by
 Robert L.J. Shaw, Katalin Suba, Tomáš Hampejs, and David Zbíral


Created within DISSINET Project,  https://dissinet.cz

Please do not cite, or reuse without explicit permission.
Contact person: robert.shaw@mail.muni.cz

---------
    """

    st.markdown(intro)
    #st.write("# Niort persons on map")
    st.write("Simple display of Niort persons locations")

    st.markdown(f"Loaded {len(data)} persons, just <span style='color:red'>{len(data[data['coords'].str.len() > 2])}</span> have a geocoded location.",unsafe_allow_html=True)

    if "generated_timestamp" in data.columns:
        st.write("Data from "+ data['generated_timestamp'].iloc[0] + ".")

    for key, item in data.iterrows():

        item['locations'] = eval(item['locations'])
        item['coords'] = eval(item['coords'])
        item['occupations'] = eval(item['occupations'])
        item['offices'] = eval(item['offices'])

        for location, coord in zip(item['locations'], item['coords']): #
            location_data = {}

            if len(location) > 0:
                location_data['person'] = item['name']
                location_data['location'] = location

                occupation, office = ", ".join(item['occupations']), ", ".join(item['offices'])

                location_data['occupation'] = occupation
                location_data['office'] = office
                location_data['deposition_order'] = item['absolute_order']
                location_data['status'] = item['status']
                location_data['high_rank'] = item['high_rank']

                if "charge1_pattern" in item:
                    location_data['charge1_pattern'] = item['charge1_pattern']
                    location_data['charge2_pattern'] = item['charge2_pattern']
                    location_data['charge3_pattern'] = item['charge3_pattern']
                    location_data['charge4_pattern'] = item['charge4_pattern']

                    location_data['charge1_s_pattern'] = item['charge1_s_pattern']
                    location_data['charge2_s_pattern'] = item['charge2_s_pattern']
                    location_data['charge3_s_pattern'] = item['charge3_s_pattern']
                    location_data['charge4_s_pattern'] = item['charge4_s_pattern']

                    location_data['response_group'] = item['response_group']

                if ";" in coord:
                    location_data['lat'] = float(coord.split(";")[0].strip())
                    location_data['lon'] = float(coord.split(";")[1].strip())
                else:
                    location_data['lat'] = ""
                    location_data['lon'] = ""
                map_data.append(location_data.copy())

    map_df = pd.DataFrame(map_data)
    st.map(map_df, zoom=7)

    # -----------------------------------------------------------------------------------------------------------------



    st.write("## Details")
    col11, col22 = st.columns([10,1])
    with col11:
        show_responses = st.checkbox("Show charge responses", value=True)
    with col22:
        show_dev = st.checkbox("[Show DEV info]", value=False)

    col1, col2 = st.columns(2)

    if not show_dev:
        com_start = "<!--"
        com_end = "-->"
    else:
        com_start = ""
        com_end = ""

    gradient_string = "background-image: repeating-linear-gradient(45deg, white, white 2px, rgba(0, 0, 0, 0.1) 2px,rgba(0, 0, 0, 0.1) 5px);"
    charge_colors = f"""
        ### Charge responses
        Witnesses reacted to four charges, their responses are displayed in four squares  around the marker.<br />
        <span style="width:15px; height:15px; background-color:lightgreen; display:inline-block;">1</span> 
        <span style="width:15px; height:15px; background-color:lightgreen; display:inline-block;">2</span><br />
        <span style="width:15px; height:15px; background-color:lightgreen; display:inline-block;">3</span>
        <span style="width:15px; height:15px; background-color:lightgreen; display:inline-block;">4</span><br />
        and bear information about charge response (e.g. affirmed from hearsay), its scope (e.g. some suspects) and the way notary wrote it (e.g. idem quod testimony).

        **Charge square colors**: <br>
        Affirmed
        * <span style="width:10px; height:10px; background-color:darkgreen; display:inline-block;"></span>{com_start} TaF-F-F-  = {com_end} affirmed (all suspects, own testimony)<br>
        * <span style="width:10px; height:10px; background-color:darkgreen; display:inline-block;{gradient_string}"></span>{com_start} TsF-F-F- = {com_end} affirmed (some suspects, own testimony)<br>
        * <span style="width:10px; height:10px; background-color:lightgreen; display:inline-block;"></span>{com_start} F-TaF-F- = affirmed {com_end} (all suspects, idem quod testimony)<br>
        * <span style="width:10px; height:10px; background-color:lightgreen; display:inline-block;{gradient_string}"></span>{com_start} F-TsF-F- = {com_end} affirmed (some suspects, idem quod testimony)

        Affirmed from hearsay
        * <span style="width:10px; height:10px; background-color:blue; display:inline-block;"></span>{com_start} TaF-TaF- = {com_end} affirmed from hearsay (all suspects, own testimony)<br>
        * <span style="width:10px; height:10px; background-color:blue; display:inline-block;{gradient_string}"></span>{com_start} TsF-TsF- = {com_end} affirmed from hearsay (some suspects, own testimony)<br>
        * <span style="width:10px; height:10px; background-color:lightblue; display:inline-block;"></span>{com_start} F-TaF-Ta = affirmed from {com_end} hearsay (all suspects, idem quod testimony)<br>
        * <span style="width:10px; height:10px; background-color:lightblue; display:inline-block;{gradient_string}"></span>{com_start} F-Ts-F-Ts = {com_end} affirmed from hearsay (some suspects, idem quod testimony)

        Not affirmed
        * <span style="width:10px; height:10px; background-color:red; display:inline-block;"></span>{com_start} F-F-F-F-  = {com_end} <span style="color:red">not affirmed</span> 
        """

    with col1:
        st.write("### Markers")
        st.write(" **Click** on the marker for the details about a person.")
        st.write("* Markers in circle shape belong to same coordinates as vertically aligned close point marker.")
        st.write("Marker colors:")
        st.markdown("* **high_rank** = <span style=\"background-color:gold;\">gold background</span> (yes) / white (no)", unsafe_allow_html=True)
        st.markdown("* **church status** = <span style='color:purple'>purple border</span>  (clergyman) / :orange[orange] :orange[border] (religious) /  none (-)", unsafe_allow_html=True)
        st.write("Marker label:")
        st.markdown("* **number** = n. of textual order of deposition", unsafe_allow_html=True)


    with col2:
        if show_responses:
            st.markdown(charge_colors, unsafe_allow_html=True)

    m = folium.Map(location=[map_df.lat.mean(), map_df.lon.mean()],
                   zoom_start=10, control_scale=True,
                   )
    #tiles='https://{s}.tile.thunderforest.com/pioneer/{z}/{x}/{y}.png?apikey={apikey}',
    #attr='&copy; <a href="http://www.thunderforest.com/">Thunderforest</a>, &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',

    processed_multiples = []


    # Loop through each row in the dataframe
    for i, row in map_df.iterrows():

        o_lat = row['lat']
        o_lon = row['lon']

        # checking for the same location coordinates
        count_of_value = (map_df[['lat','lon']] == (row['lat'],row['lon'])).sum().sum()



        if count_of_value > 2:
            # st.write(f"There multiple people {int(count_of_value/2)} on same location coords {row['lat']},{row['lon']}.")
            processed_multiples.append((o_lat,o_lon))
            #multiples = map_df[map_df[['lat','lon']] == (row['lat'],row['lon'])]

            #st.write("#"+str(processed_multiples.count((row['lat'], row['lon']))))
            row['lat'] = row['lat'] + 0.002 * processed_multiples.count((o_lat,o_lon))
        else:
            pass

        response_legend = {
            "TaF-F-F-": "affirmed (all suspects, own testimony)",
            "TsF-F-F-" : "affirmed (some suspects, own testimony)",
            "F-TaF-F-" : "affirmed (all suspects, idem quod testimony)",
            "F-TsF-F-" : "affirmed (some suspects, idem quod testimony)",
            "TaF-TaF-" : "affirmed from hearsay (all suspects, own testimony)",
            "TsF-TsF-" : "affirmed from hearsay (some suspects, own testimony)",
            "F-TaF-Ta" : "affirmed from hearsay (all suspects, idem quod testimony)",
            "F-TsF-Ts" : "affirmed from hearsay (some suspects, idem quod testimony)",
            "F-F-F-F-" : "not affirmed"
        }

        c1 = "".join([ c1+c2.lower() for c1,c2 in zip(row['charge1_pattern'],row['charge1_s_pattern'])])
        c2 = "".join([ c1+c2.lower() for c1,c2 in zip(row['charge2_pattern'],row['charge2_s_pattern'])])
        c3 = "".join([ c1+c2.lower() for c1,c2 in zip(row['charge3_pattern'],row['charge3_s_pattern'])])
        c4 = "".join([ c1+c2.lower() for c1,c2 in zip(row['charge4_pattern'],row['charge4_s_pattern'])])

        if show_dev:
            c1 = c1+" "+response_legend[c1]
            c2 = c2+" "+response_legend[c2]
            c3 = c3+" "+response_legend[c3]
            c4 = c4+" "+response_legend[c4]
        else:
            c1 = response_legend[c1]
            c2 = response_legend[c2]
            c3 = response_legend[c3]
            c4 = response_legend[c4]

        # Set up the content of the popup
        iframe = folium.IFrame('Location: ' + str(row["location"])
                               + "<br /> Person: "
                               + str(row["person"])
                               + "<br /> Occupation: "
                               + str(row["occupation"])
                               + "<br /> Office: "
                               + str(row["office"])
                               + "<br /> Status: "
                               + str(row["status"])
                               + "<br /> High rank: "
                               + str(row["high_rank"])
                               + "<br /> Deposition n.: "
                               + str(row["deposition_order"])
                               + "<br /> Charge 1: " + c1
                               + "<br /> Charge 2: " + c2
                               + "<br /> Charge 3: " + c3
                               + "<br /> Charge 4: " + c4
                               )

        # Initialise the popup using the iframe
        popup = folium.Popup(iframe, min_width=300, max_width=300)


        if 'status' in row:
            status = row['status']
            if "religious" in status:
                color = "orange"
            elif "clergyman" in status:
                color = "purple"
            else:
                color = "white"
        else:
            color = "white"

        #st.write(processed_multiples.count((row['lat']- 0.005 * processed_multiples.count((row['lat'],row['lon'])), row['lon'])))
        if processed_multiples.count((o_lat, o_lon)) > 1:
            icon_shape = "circle"
        else:
            icon_shape = "marker"

        if "high_rank" in row:
            if "1" in str(row['high_rank']):
                background_color = "gold"
            else:
                background_color = "white"
        else:
            background_color = "white"

        # add charges hallo
        # folium.Marker(location=[row['lat'], row['lon']],
        #               #c=row['location'],
        #               icon=fplugins.BeautifyIcon(
        #                   icon="arrow-down", icon_shape="circle",
        #                   number="",
        #                   border_color="black",
        #                   background_color="black"
        #                   # border_color=itinerario_lunes.iloc[i]['hex_code'],
        #                   # background_color=itinerario_lunes.iloc[i]['hex_code']
        #               )
        #               ).add_to(m)


        if "response_group"in row and show_responses:
            # folium.CircleMarker(
            #     location=[row['lat'], row['lon']],
            #     radius=15,  # size of the marker
            #     color='red',
            #     fill=True,
            #     fill_color='red'
            # ).add_to(m)

            def charge_group_to_color(group_string):
                map = {
                    "FFFF" : "red",
                    "TFTF": "blue",
                    "FTFT" : "lightblue",
                    "TFFF": "darkgreen",
                    "FTFF": "lightgreen",
                    #"TTFT" : "yellow"
                }

                return map[group_string]
            def charge_scope_to_color(scope_string, charge_response_color):
                scope_string = scope_string.replace("N","-")
                map = {
                    "-S-S": "transparent",
                    "----": "transparent",
                    "-A--": "yellow",
                    "A---": "yellow",
                    "S---": "transparent",
                    "-A-A": "yellow",
                    "A-A-": "yellow",
                    "-S--": "transparent",
                    "S-S-": "transparent",
                }

                if map[scope_string] == "yellow":
                    return charge_response_color
                else:
                    return map[scope_string]

            c4s = ""#row['charge4_s_pattern'].replace("N","-")
            c1s = ""#row['charge1_s_pattern'].replace("N","-")
            c2s = ""#row['charge2_s_pattern'].replace("N","-")
            c3s = ""#row['charge3_s_pattern'].replace("N","-")

            # C4
            if "S" in row['charge4_s_pattern']:
                background_image_element = """
                background-image: repeating-linear-gradient(
                                    45deg,
                                    white,
                                    white 2px,
                                    rgba(0, 0, 0, 0.1) 2px,
                                    rgba(0, 0, 0, 0.1) 5px
                                  );
                """
            else:
                background_image_element = ""
            folium.Marker(location=[row['lat'], row['lon']],
                icon=folium.DivIcon(
                    icon_size=(0, 0),
                    icon_anchor=(0, 0),
                    html='<div style="'+background_image_element+'border:1px solid black; width:15px; height:15px; background-color:'+charge_group_to_color(row['charge4_pattern'])+';">'+c4s+'</div>',
            )).add_to(m)


                # folium.Marker(location=[row['lat'], row['lon']],
                #               icon=folium.DivIcon(
                #                   icon_size=(0, 0),
                #                   icon_anchor=(-15, 0),
                #                   html='<div style="border:1px solid black; width:7px; height:15px; background-color:'+charge_scope_to_color(row['charge4_s_pattern'],charge_group_to_color(row['charge4_pattern']))+';">' + c1s + '</div>',
                #  )).add_to(m)


            # C1
            if "S" in row['charge1_s_pattern']:
                background_image_element = """
                                background-image: repeating-linear-gradient(
                                    45deg,
                                    white,
                                    white 2px,
                                    rgba(0, 0, 0, 0.1) 2px,
                                    rgba(0, 0, 0, 0.1) 5px
                                  );
                                """
            else:
                background_image_element = ""
            folium.Marker(location=[row['lat'], row['lon']],
                          icon=folium.DivIcon(
                              icon_size=(0, 0),
                              icon_anchor=(15, 15),
                              html='<div style="'+background_image_element+'border:1px solid black; width:15px; height:15px; background-color:'+charge_group_to_color(row['charge1_pattern'])+';">'+c1s+'</div>',
            )).add_to(m)

                # folium.Marker(location=[row['lat'], row['lon']],
                #               icon=folium.DivIcon(
                #                   icon_size=(0, 0),
                #                   icon_anchor=(21, 15),
                #                   html='<div style="border:1px solid black; width:7px; height:15px; background-color:'+charge_scope_to_color(row['charge1_s_pattern'],charge_group_to_color(row['charge1_pattern']))+';">' + c1s + '</div>',
                #  )).add_to(m)


            # C3
            if "S" in row['charge3_s_pattern']:
                background_image_element = """
                                background-image: repeating-linear-gradient(
                                    45deg,
                                    white,
                                    white 2px,
                                    rgba(0, 0, 0, 0.1) 2px,
                                    rgba(0, 0, 0, 0.1) 5px
                                  );
                                """
            else:
                background_image_element = ""
            folium.Marker(location=[row['lat'], row['lon']],
                          icon=folium.DivIcon(
                              icon_size=(0, 0),
                              icon_anchor=(15, 0),
                              html='<div style="'+background_image_element+'border:1px solid black; width:15px; height:15px; background-color:'+charge_group_to_color(row['charge3_pattern'])+';">'+c3s+'</div>',
            )).add_to(m)

                # folium.Marker(location=[row['lat'], row['lon']],
                #               icon=folium.DivIcon(
                #                   icon_size=(0, 0),
                #                   icon_anchor=(21, 0),
                #                   html='<div style="border:1px solid black; width:7px; height:15px; background-color:'+charge_scope_to_color(row['charge3_s_pattern'],charge_group_to_color(row['charge3_pattern']))+';">' + c1s + '</div>',
                #  )).add_to(m)

            # C2
            if "S" in row['charge2_s_pattern']:
                background_image_element = """
                                background-image: repeating-linear-gradient(
                                    45deg,
                                    white,
                                    white 2px,
                                    rgba(0, 0, 0, 0.1) 2px,
                                    rgba(0, 0, 0, 0.1) 5px
                                  );
                                """
            else:
                background_image_element = ""
            folium.Marker(location=[row['lat'], row['lon']],
                          icon=folium.DivIcon(
                              icon_size=(0, 0),
                              icon_anchor=(0, 15),
                              html='<div style="'+background_image_element+'border:1px solid black; width:15px; height:15px; background-color:'+charge_group_to_color(row['charge2_pattern'])+';">'+c2s+'</div>',
                          )).add_to(m)

                # folium.Marker(location=[row['lat'], row['lon']],
                #               icon=folium.DivIcon(
                #                   icon_size=(0, 0),
                #                   icon_anchor=(-15, 15),
                #                   html='<div style="border:1px solid black; width:7px; height:15px; background-color:'+charge_scope_to_color(row['charge2_s_pattern'],charge_group_to_color(row['charge2_pattern']))+';">' + c1s + '</div>',
                #  )).add_to(m)

            # folium.Marker(
            #     location=[row['lat'], row['lon']],
            #     popup='Star Icon',
            #     #icon=folium.Icon(icon='star', prefix='fa', color='orange')
            #     #icon=folium.Icon(color='red',icon="cloud",icon_size=(200,200))
            #     icon=folium.Icon(color='red',icon="cloud",icon_size=(200,200))
            # ).add_to(m)

            # def style_function(feature):
            #     props = feature.get('properties')
            #     markup = f"""
            #         <a href="#">
            #             <div style="font-size: 0.8em;">
            #             <div style="width: 10px;
            #                         height: 10px;
            #                         border: 1px solid black;
            #                         border-radius: 15px;
            #                         background-color: orange;">*
            #             </div>
            #             {props.get('name')}
            #         </div>
            #         </a>
            #     """
            #     return {"html": markup}
            #
            # gdf = {
            #     "type": "FeatureCollection",
            #     "features": [
            #         {
            #             "properties": {"name": "Test"},
            #             "id": "AL",
            #             "type": "Feature",
            #             "geometry": {
            #                 "type": "Point",
            #                 "coordinates": [row['lat'], row['lon']]
            #                 }
            #             },
            #         ]
            #     }
            #
            #
            # def point_to_layer(feature, latlng):
            #     marker = folium.Marker(
            #         location=latlng,
            #         popup=feature['properties']['name']
            #     )
            #     return marker
            #
            #
            # folium.GeoJson(
            #     gdf,
            #     name="Test",
            #     point_to_layer=point_to_layer,
            #     #marker=folium.Marker(icon=folium.DivIcon()),
            #     #tooltip=folium.GeoJsonTooltip(fields=["name", "line", "notes"]),
            #     #popup=folium.GeoJsonPopup(fields=["name", "line", "href", "notes"]),
            #     style_function=style_function,
            #     #zoom_on_click=True,
            # ).add_to(m)
            pass

        # icon = folium.Icon(icon='cloud', icon_size=(30, 30))  # width and height in pixels
        #
        # # Add marker to the map
        # folium.Marker(
        #     location=[51.505, -0.09],
        #     icon=icon
        # ).add_to(m)



        # Add each row to the map
        folium.Marker(location=[row['lat'], row['lon']],
                      popup=popup, c=row['location'],
                      icon=fplugins.BeautifyIcon(
                          icon="arrow-down", icon_shape=icon_shape,
                          number=row['deposition_order'],
                          border_color=color,
                          background_color = background_color
                          #border_color=itinerario_lunes.iloc[i]['hex_code'],
                          #background_color=itinerario_lunes.iloc[i]['hex_code']
                      )
                      ).add_to(m)


        # html = f"""
        #     <h2>  Información de la ruta </h2>
        #     <p> Ruta: {DF.iloc[i]['route_id']}  </p>
        #     <p> Secuencia de visita: {DF.iloc[i]['sequencia']}  </p>
        #     """
        #
        # iframe = folium.IFrame(html=html, width=200, height=150)
        # popup = folium.Popup(iframe, max_width=650)
        # folium.Marker(
        #     location=[DF.iloc[i]['latitude'], DF.iloc[i]['longitude']], popup=popup,
        #     icon=plugins.BeautifyIcon(
        #         icon="arrow-down", icon_shape="marker",
        #         number=DF.iloc[i]['sequencia'],
        #         border_color=itinerario_lunes.iloc[i]['hex_code'],
        #         background_color=itinerario_lunes.iloc[i]['hex_code']
        #     )
        # ).add_to(n)


    st_data = folium_static(m, height=1000, width=2200)


else:
    st.write("Column 'coord' not found in the dataframe.")


footer = """
Powered by [Streamlit](https://streamlit.io/) and [Folio](https://python-visualization.github.io/folium/latest/#)
"""

st.markdown(footer)