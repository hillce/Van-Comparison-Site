"""
App for comparing ford transit campervans
"""
import re
import time
import copy
import urllib
import requests

from bs4 import BeautifulSoup
from urllib.request import Request, urlopen, urlretrieve
import pandas as pd

import streamlit as st
from st_aggrid import GridOptionsBuilder, AgGrid, GridUpdateMode, DataReturnMode

import plotly.express as px

px.set_mapbox_access_token(
    open(".mapbox_token").read()
)

st.set_page_config(layout="wide")

@st.cache()
def get_data(runs=0):

    van_search = [
        ("Ford", "Transit"),
        ("Volkswagen", "Transporter"),
        ("Vauxhall", "Vivaro"),
        ("Mercedes-Benz", "Sprinter"),
    ]

    max_price = 5000

    auto_url = "https://www.autotrader.co.uk"
    vans_df = []

    for van_s in van_search:
        url = f"https://www.autotrader.co.uk/van-search?postcode=OX4%202FU&make={van_s[0]}&model={van_s[1]}&body-type=Panel%20Van&supplied-price-to={max_price}&include-delivery-option=on&advertising-location=at_vans&page=1"

        req = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        webpage = urlopen(req).read()

        soup = BeautifulSoup(webpage, "lxml")
        soup.find("li", {"class":"paginationMini__count"}).get_text().strip()

        pages = re.findall("\d+", soup.find("li", {"class":"paginationMini__count"}).get_text().strip())
        max_page = max(map(int, pages))

        for i in range(1, max_page):
            url = f"https://www.autotrader.co.uk/van-search?postcode=OX4%202FU&make={van_s[0]}&model={van_s[1]}&body-type=Panel%20Van&supplied-price-to={max_price}&include-delivery-option=on&advertising-location=at_vans&page={i}"
            req = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            webpage = urlopen(req).read()

            soup = BeautifulSoup(webpage, "lxml")

            vans = soup.find_all("article", {"class": "product-card"})

            for van in vans:
                temp_dict = {}

                price = van.find("div", {"class": "product-card-pricing__price"}).get_text().strip().replace(",","")

                temp_dict["Price (£)"] = float(re.findall("\d+", price)[0])

                if "VAT" in price.upper():
                    temp_dict["VAT"] = True
                else:
                    temp_dict["VAT"] = False

                temp_dict["Type"] = van.find("h3", {"class": "product-card-details__title"}).get_text().strip()
                temp_dict["Specs"] = van.find("p", {"class": "product-card-details__subtitle"}).get_text().strip()
                try:
                    temp_dict["Headline"] = van.find("p", {"class": "product-card-details__attention-grabber"}).get_text().strip()
                except AttributeError:
                    temp_dict["Headline"] = "None"

                key_specs = van.find("ul", {"class": "listing-key-specs"})
                key_specs = key_specs.find_all("li", {"class" :"atc-type-picanto--medium"})
                key_specs = [x.get_text().strip() for x in key_specs]

                for ks in key_specs:
                    if "reg" in ks.lower():
                        temp_dict["Year"] = int(re.findall("\d+", ks)[0])
                    elif "WB" in ks.upper():
                        temp_dict["Wheel Base"] = ks.upper()
                    elif "miles" in ks.lower():
                        temp_dict["Mileage"] = float(re.findall("\d+", ks.replace(",", ""))[0])
                    elif ks.endswith("L"):
                        temp_dict["Engine"] = float(re.findall("\d+\.\d+", ks)[0])
                    elif "BHP" in ks.upper():
                        temp_dict["Break Horse Power"] = float(re.findall("\d+", ks)[0])
                    elif ks.lower() in ["manual", "automatic"]:
                        temp_dict["Transmission"] = ks.lower()
                    elif ks.lower() in ["diesel", "petrol", "electric"]:
                        temp_dict["Fuel"] = ks.lower()
                    elif "seats" in ks.lower():
                        temp_dict["Seats"] = int(re.findall("\d+", ks)[0])
                    elif "Year" not in temp_dict.keys():
                        try:
                            temp_dict["Year"] = int(re.findall("\d+", ks)[0])
                        except IndexError:
                            temp_dict["Year"] = 2000

                temp_dict["Dealer"] = van.find("h3", {"class":"product-card-seller-info__name atc-type-picanto"}).get_text().strip()

                location = van.find_all("li", {"class":"product-card-seller-info__spec-item atc-type-picanto"})
                for loc in location:
                    for sub_loc in loc.get_text().strip().splitlines():
                        if "miles" in sub_loc:
                            temp_dict["Distance"] = float(re.findall("\d+",sub_loc)[0])

                url_van = van.find("a", {"class": "js-click-handler listing-fpa-link tracking-standard-link"})
                temp_dict["url_van"] = f"{auto_url}{url_van['href']}"

                location = van.find_all("span", {"class":"product-card-seller-info__spec-item-copy"})
                location = f"{location[-1].text}, UK"
                url = 'https://nominatim.openstreetmap.org/search/' + urllib.parse.quote(location) +'?format=json'
                response = requests.get(url).json()
                temp_dict["lat"] = response[0]["lat"]
                temp_dict["lon"] = response[0]["lon"]

                vans_df.append(temp_dict)

            time.sleep(0.1)

    vans_df = pd.DataFrame(vans_df)

    return vans_df


def update_data():
    num_runs += 1

global num_runs
num_runs = 0
vans_df = get_data(runs=num_runs)

page = st.sidebar.selectbox("App Navigation: ", ["Van Table", "Data Analysis"])

if page == "Van Table":
    st.sidebar.subheader("Filters: ")

    van_types = ["All"]
    van_types.extend(vans_df["Type"].unique())

    make = st.sidebar.selectbox("Select Make: ", van_types)
    if make == "All":
        make_select = copy.deepcopy(vans_df)
    else:
        make_select = vans_df.loc[vans_df["Type"] == make]


    wheel_base_types = ["All"]
    wheel_base_types.extend(make_select["Wheel Base"].unique())

    wheel_base = st.sidebar.selectbox("Select Wheelbase: ", wheel_base_types)
    if wheel_base == "All":
        wheel_select = copy.deepcopy(make_select)
    else:
        wheel_select = make_select.loc[make_select["Wheel Base"] == wheel_base]

    prices = st.sidebar.slider(
        "Price: ",
        int(wheel_select["Price (£)"].min()),
        int(wheel_select["Price (£)"].max()),
        (int(wheel_select["Price (£)"].min()), int(wheel_select["Price (£)"].max())),
        format=f"£%g"
    )

    price_select = wheel_select.loc[
                                (wheel_select["Price (£)"] >= prices[0]) & \
                                (wheel_select["Price (£)"] <= prices[1])
                                ]

    years = st.sidebar.slider(
        "Year: ",
        int(price_select["Year"].min()),
        int(price_select["Year"].max()),
        (int(price_select["Year"].min()), int(price_select["Year"].max())),
    )

    year_select = price_select.loc[
                                (price_select["Year"] >= years[0]) & \
                                (price_select["Year"] <= years[1])
                                ]

    mileage = st.sidebar.slider(
        "Mileage: ",
        int(year_select["Mileage"].min()),
        int(year_select["Mileage"].max()),
        (int(year_select["Mileage"].min()), int(year_select["Mileage"].max())),
    )

    st.sidebar.button("Update Table", on_click=update_data)

    enable_selection = True
    selection_mode = "single"
    use_checkbox = True
    st.sidebar.subheader("Table Options: ")
    grid_height = st.sidebar.number_input("Grid height", min_value=200, max_value=800, value=500)

    # return_mode = st.sidebar.selectbox("Return Mode", list(DataReturnMode.__members__), index=1)
    return_mode_value = DataReturnMode.__members__["AS_INPUT"]

    # update_mode = st.sidebar.selectbox("Update Mode", list(GridUpdateMode.__members__), index=6)
    update_mode_value = GridUpdateMode.__members__["SELECTION_CHANGED"]

    #Infer basic colDefs from dataframe types
    gb = GridOptionsBuilder.from_dataframe(vans_df)

    #customize gridOptions
    gb.configure_default_column(groupable=True, value=True, enableRowGroup=True, aggFunc='sum', editable=True)
    gb.configure_selection(selection_mode, use_checkbox=use_checkbox)
    gb.configure_grid_options(domLayout='normal')
    gridOptions = gb.build()

    col1, col2 = st.columns(2)


    with col1:

        if make == "All":
            if wheel_base == "All":
                grid_df = vans_df.loc[
                            (vans_df["Price (£)"] >= prices[0]) & \
                            (vans_df["Price (£)"] <= prices[1]) & \
                            (vans_df["Year"] >= years[0]) & \
                            (vans_df["Year"] <= years[1]) & \
                            (vans_df["Mileage"] >= mileage[0]) & \
                            (vans_df["Mileage"] <= mileage[1])
                ]
            else:
                grid_df = vans_df.loc[
                            (vans_df["Wheel Base"] == wheel_base) & \
                            (vans_df["Price (£)"] >= prices[0]) & \
                            (vans_df["Price (£)"] <= prices[1]) & \
                            (vans_df["Year"] >= years[0]) & \
                            (vans_df["Year"] <= years[1]) & \
                            (vans_df["Mileage"] >= mileage[0]) & \
                            (vans_df["Mileage"] <= mileage[1])
                ]
        elif wheel_base == "All":
            grid_df = vans_df.loc[
                        (vans_df["Type"] == make) & \
                        (vans_df["Price (£)"] >= prices[0]) & \
                        (vans_df["Price (£)"] <= prices[1]) & \
                        (vans_df["Year"] >= years[0]) & \
                        (vans_df["Year"] <= years[1]) & \
                        (vans_df["Mileage"] >= mileage[0]) & \
                        (vans_df["Mileage"] <= mileage[1])
            ]
        else:
            grid_df = vans_df.loc[
                        (vans_df["Wheel Base"] == wheel_base) & \
                        (vans_df["Type"] == make) & \
                        (vans_df["Price (£)"] >= prices[0]) & \
                        (vans_df["Price (£)"] <= prices[1]) & \
                        (vans_df["Year"] >= years[0]) & \
                        (vans_df["Year"] <= years[1]) & \
                        (vans_df["Mileage"] >= mileage[0]) & \
                        (vans_df["Mileage"] <= mileage[1])
            ]
        grid_response = AgGrid(
            grid_df,
            gridOptions=gridOptions,
            height=grid_height,
            data_return_mode=return_mode_value,
            update_mode=update_mode_value,
        )

    sub_df = grid_response["data"]
    selected = grid_response['selected_rows']

    if len(selected) > 0:
        with st.spinner("Displaying results..."):
            with col2:
                st.write(f"[AUTOTRADER LINK]({selected[0]['url_van']})")

                sub_req = Request(selected[0]["url_van"], headers={'User-Agent': 'Mozilla/5.0'})
                sub_webpage = urlopen(sub_req).read()

                soup = BeautifulSoup(sub_webpage, "lxml")

                imgs = soup.find_all("img")
                for img in imgs:
                    url_img = img["src"]
                    if url_img.endswith(".jpg"):
                        urlretrieve(url_img, "temp.jpg")

                st.image("temp.jpg")

                temp_df = pd.DataFrame(selected)
                temp_df["lon"] = temp_df["lon"].astype(float)
                temp_df["lat"] = temp_df["lat"].astype(float)

                st.map(temp_df)

            with col1:
                sub_df = pd.DataFrame(selected).T
                sub_df.rename(columns={0: "Values"}, inplace=True)
                sub_df["Values"] = sub_df["Values"].astype(str)
                st.write(sub_df)
    else:
        with col2:
            temp_df = copy.deepcopy(sub_df)
            temp_df["lon"] = temp_df["lon"].astype(float)
            temp_df["lat"] = temp_df["lat"].astype(float)


            fig = px.scatter_mapbox(
                temp_df,
                lat=temp_df.lat,
                lon=temp_df.lon,
                hover_name="Type",
            )

            st.plotly_chart(fig)


elif page == "Data Analysis":
    col1, col2 = st.columns(2)

    types = ["ford", "vauxhall", "mercedes-benz", "volkswagen"]

    metrics_df = []
    for i,val in vans_df.iterrows():
        metrics_dict = {"Type": [], "Price (£)":[], "Mileage": [], "Year": []}
        for k in types:
            if k in val["Type"].lower():
                metrics_dict["Type"] = k
                for sub_k in list(metrics_dict.keys())[1:]:
                    metrics_dict[sub_k] = val[sub_k]

                metrics_df.append(metrics_dict)
                continue

    metrics_df = pd.DataFrame(metrics_df)

    with col1:
        st.plotly_chart(px.histogram(metrics_df, x="Price (£)", color="Type", barmode="overlay"))

        st.plotly_chart(px.histogram(metrics_df, x="Price (£)", color="Year", barmode="overlay"))

    with col2:
        st.plotly_chart(px.scatter(vans_df, y="Price (£)", x="Mileage", color="Type", trendline="ols"))