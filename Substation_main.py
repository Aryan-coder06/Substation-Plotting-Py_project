import pandas as pd
import plotly.express as px
import dash 
from dash import html, dcc, Input, Output, dash_table
import folium
from folium.plugins import MarkerCluster
import base64
import io
from dash.exceptions import PreventUpdate

# Load data
df = pd.read_excel("maindataset.xlsx")
df.rename(columns={"Longitudes": "Longitude"}, inplace=True)

df["Latitude"] = pd.to_numeric(df["Latitude"], errors='coerce')
df["Longitude"] = pd.to_numeric(df["Longitude"], errors='coerce')
df["SS_FisYearName"] = pd.to_datetime(df["SS_FisYearName"], errors='coerce', unit='D', origin='1899-12-30').dt.year
df.dropna(subset=["SS_FisYearName"], inplace=True)
df["SS_FisYearName"] = df["SS_FisYearName"].astype(int)

total_substations = len(df)
unique_regions = df["Region"].nunique()
avg_spend = df[["Planning Plant", "Maintenence Plant"]].mean().mean()

app = dash.Dash(__name__, suppress_callback_exceptions=True)
app.title = "⚡ Substation Intelligence Platform"

app.css.append_css({
    'external_url': 'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css'
})

app.layout = html.Div([
    html.Div([
        html.Div([
            html.H1("Substation Intelligence Platform", className="app-title"),
            html.P("Comprehensive analytics for energy infrastructure", className="app-subtitle")
        ], className="title-container"),
        
        html.Button(
            id="dark-toggle",
            className="dark-toggle-btn",
            children=[
                html.Span("☀️", className="sun-icon"),
                html.Span("🌙", className="moon-icon")
            ],
            n_clicks=0
        )
    ], className="app-header"),
    
    # Metrics Cards Row
    html.Div([
        html.Div([
            html.Div([
                html.Div([
                    html.P("Total Substations", className="card-title"),
                    html.H3(f"{total_substations:,}", className="card-value")
                ], className="card-content"),
                html.Div(className="card-icon", children=html.I(className="fas fa-bolt"))
            ], className="metric-card", id="card-1")
        ], className="card-column"),
        
        html.Div([
            html.Div([
                html.Div([
                    html.P("Regions Covered", className="card-title"),
                    html.H3(f"{unique_regions}", className="card-value")
                ], className="card-content"),
                html.Div(className="card-icon", children=html.I(className="fas fa-map-marked-alt"))
            ], className="metric-card", id="card-2")
        ], className="card-column"),
        
        html.Div([
            html.Div([
                html.Div([
                    html.P("Avg Spend", className="card-title"),
                    html.H3(f"${avg_spend:,.0f}", className="card-value")
                ], className="card-content"),
                html.Div(className="card-icon", children=html.I(className="fas fa-chart-line"))
            ], className="metric-card", id="card-3")
        ], className="card-column"),
        
        html.Div([
            html.Div([
                html.Div([
                    html.P("Data Updated", className="card-title"),
                    html.H3("Q2 2023", className="card-value")
                ], className="card-content"),
                html.Div(className="card-icon", children=html.I(className="fas fa-calendar-check"))
            ], className="metric-card", id="card-4")
        ], className="card-column")
    ], className="cards-row"),
    
    # Main Content Area
    html.Div([
        # Filters Panel
        html.Div([
            html.Div([
                html.H4("FILTERS", className="filters-title"),
                html.Hr(className="divider"),
                
                html.Label("Select Regions", className="filter-label"),
                dcc.Dropdown(
                    id="region-filter",
                    options=[{"label": i, "value": i} for i in sorted(df["Region"].dropna().unique())],
                    multi=True,
                    placeholder="All Regions",
                    className="filter-dropdown"
                ),
                
                html.Label("Ownership Type", className="filter-label"),
                dcc.Dropdown(
                    id="ownership-filter",
                    options=[{"label": i, "value": i} for i in sorted(df["Substation Ownership"].dropna().unique())],
                    multi=True,
                    placeholder="All Ownership Types",
                    className="filter-dropdown"
                ),
                
                html.Label("Time Range", className="filter-label"),
                dcc.RangeSlider(
                    id='year-slider',
                    min=int(df["SS_FisYearName"].min()),
                    max=int(df["SS_FisYearName"].max()),
                    step=1,
                    value=[int(df["SS_FisYearName"].min()), int(df["SS_FisYearName"].max())],
                    marks={int(year): {'label': str(year), 'style': {'color': '#fff'}} 
                           for year in sorted(df["SS_FisYearName"].unique())},
                    tooltip={"placement": "bottom", "always_visible": False},
                    className="year-slider"
                ),
                
                html.Button("Apply Filters", id="apply-filters", className="apply-btn"),
                html.Button("Reset Filters", id="reset-filters", className="reset-btn")
            ], className="filters-panel")
        ], className="filters-column"),
        
        # Charts and Map Area
        html.Div([
            # First Row - Charts
            html.Div([
                html.Div([
                    dcc.Graph(id="spend-trend-chart", className="chart-container")
                ], className="chart-column"),
                
                html.Div([
                    dcc.Graph(id="ownership-pie-chart", className="chart-container")
                ], className="chart-column")
            ], className="charts-row"),
            
            # Second Row - Map and Data Table
            html.Div([
                html.Div([
                    html.Div([
                        html.H4("Substation Locations", className="map-title"),
                        html.Div([
                            html.Button("Satellite", id="satellite-btn", className="map-toggle-btn"),
                            html.Button("Dark", id="dark-btn", className="map-toggle-btn active"),
                            html.Button("Light", id="light-btn", className="map-toggle-btn")
                        ], className="map-toggle-group")
                    ], className="map-header"),
                    html.Iframe(id="map", srcDoc=None, className="map-iframe")
                ], className="map-container"),
                
                html.Div([
                    html.H4("Substation Data", className="table-title"),
                    html.Div([
                        dash_table.DataTable(
                            id='substation-table',
                            columns=[{"name": i, "id": i} for i in ["Substation Name", "Region", "Substation Ownership", "SS_FisYearName"]],
                            page_size=10,
                            sort_action='native',
                            filter_action='native',
                            style_table={'overflowX': 'auto'},
                            style_cell={
                                'textAlign': 'left',
                                'padding': '8px',
                                'minWidth': '100px', 'width': '150px', 'maxWidth': '200px',
                                'whiteSpace': 'normal',
                                'height': 'auto'
                            },
                            style_header={
                                'backgroundColor': 'var(--header-bg)',
                                'fontWeight': 'bold',
                                'border': '1px solid var(--border-color)'
                            },
                            style_data={
                                'backgroundColor': 'var(--table-bg)',
                                'color': 'var(--text-color)',
                                'border': '1px solid var(--border-color)'
                            },
                            style_data_conditional=[
                                {
                                    'if': {'row_index': 'odd'},
                                    'backgroundColor': 'var(--table-alt-bg)'
                                }
                            ]
                        )
                    ], className="table-container")
                ], className="data-table-container")
            ], className="map-table-row")
        ], className="content-column")
    ], className="main-content"),
    
    html.Div([
        html.P("© 2023 Energy Analytics Platform | v2.1.0", className="footer-text"),
        html.Div([
            html.A(html.I(className="fab fa-github"), href="#", className="social-icon"),
            html.A(html.I(className="fab fa-linkedin"), href="#", className="social-icon"),
            html.A(html.I(className="fas fa-envelope"), href="#", className="social-icon")
        ], className="social-links")
    ], className="app-footer"),
    
    html.Div(id="map-type-store", style={"display": "none"}, children="dark"),
    
    dcc.Store(id='filtered-data-store')
], id="main-container", className="light-mode")


app.css.append_css({
    'external_url': 'https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap'
})

app.css.append_css({
    'external_url': 'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css'
})

# Define your CSS
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <style>
            :root {
                --primary-color: #4361ee;
                --secondary-color: #3f37c9;
                --accent-color: #4895ef;
                --dark-color: #1a1a2e;
                --light-color: #f8f9fa;
                --success-color: #4cc9f0;
                --warning-color: #f72585;
                --danger-color: #7209b7;
                
                --text-color: #333;
                --text-light: #6c757d;
                --text-dark: #212529;
                
                --bg-color: #fff;
                --card-bg: #fff;
                --header-bg: #f8f9fa;
                --table-bg: #fff;
                --table-alt-bg: #f8f9fa;
                --border-color: #dee2e6;
                
                --shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                --shadow-hover: 0 8px 15px rgba(0, 0, 0, 0.1);
                
                --transition: all 0.3s ease;
            }
            
            .dark-mode {
                --primary-color: #4895ef;
                --secondary-color: #4361ee;
                --accent-color: #3f37c9;
                --dark-color: #121212;
                --light-color: #1e1e1e;
                
                --text-color: #f8f9fa;
                --text-light: #adb5bd;
                --text-dark: #e9ecef;
                
                --bg-color: #121212;
                --card-bg: #1e1e1e;
                --header-bg: #2d2d2d;
                --table-bg: #1e1e1e;
                --table-alt-bg: #2d2d2d;
                --border-color: #333;
                
                --shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
                --shadow-hover: 0 8px 15px rgba(0, 0, 0, 0.3);
            }
            
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
                font-family: 'Inter', sans-serif;
            }
            
            #main-container {
                min-height: 100vh;
                background-color: var(--bg-color);
                color: var(--text-color);
                transition: var(--transition);
            }
            
            .app-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 1.5rem 2rem;
                background-color: var(--primary-color);
                color: white;
                box-shadow: var(--shadow);
                position: relative;
                z-index: 100;
            }
            
            .title-container {
                display: flex;
                flex-direction: column;
            }
            
            .app-title {
                font-size: 1.8rem;
                font-weight: 600;
                margin-bottom: 0.25rem;
            }
            
            .app-subtitle {
                font-size: 0.9rem;
                opacity: 0.9;
                font-weight: 300;
            }
            
            .dark-toggle-btn {
                background: rgba(255, 255, 255, 0.2);
                border: none;
                border-radius: 50px;
                padding: 0.5rem 1rem;
                color: white;
                cursor: pointer;
                display: flex;
                align-items: center;
                gap: 0.5rem;
                transition: var(--transition);
            }
            
            .dark-toggle-btn:hover {
                background: rgba(255, 255, 255, 0.3);
            }
            
            .cards-row {
                display: flex;
                flex-wrap: wrap;
                gap: 1.5rem;
                padding: 1.5rem 2rem;
                justify-content: space-between;
            }
            
            .card-column {
                flex: 1;
                min-width: 200px;
            }
            
            .metric-card {
                background: var(--card-bg);
                border-radius: 10px;
                padding: 1.5rem;
                box-shadow: var(--shadow);
                transition: var(--transition);
                height: 100%;
                display: flex;
                justify-content: space-between;
                border-left: 4px solid var(--primary-color);
            }
            
            .metric-card:hover {
                transform: translateY(-5px);
                box-shadow: var(--shadow-hover);
            }
            
            .card-content {
                display: flex;
                flex-direction: column;
            }
            
            .card-title {
                font-size: 0.9rem;
                color: var(--text-light);
                margin-bottom: 0.5rem;
                font-weight: 500;
            }
            
            .card-value {
                font-size: 1.8rem;
                font-weight: 700;
                color: var(--primary-color);
                margin-bottom: 0;
            }
            
            .card-icon {
                font-size: 2rem;
                color: var(--primary-color);
                opacity: 0.2;
                align-self: center;
            }
            
            .main-content {
                display: flex;
                padding: 0 2rem 2rem;
                gap: 2rem;
            }
            
            .filters-column {
                flex: 0 0 280px;
            }
            
            .filters-panel {
                background: var(--card-bg);
                border-radius: 10px;
                padding: 1.5rem;
                box-shadow: var(--shadow);
                position: sticky;
                top: 1rem;
            }
            
            .filters-title {
                font-size: 1.1rem;
                margin-bottom: 1rem;
                color: var(--primary-color);
                display: flex;
                align-items: center;
                gap: 0.5rem;
            }
            
            .filters-title::before {
                content: '';
                display: block;
                width: 4px;
                height: 20px;
                background: var(--primary-color);
                border-radius: 2px;
            }
            
            .divider {
                border: none;
                height: 1px;
                background: var(--border-color);
                margin: 1rem 0;
                opacity: 0.5;
            }
            
            .filter-label {
                font-size: 0.85rem;
                font-weight: 500;
                margin-bottom: 0.5rem;
                display: block;
                color: var(--text-light);
            }
            
            .filter-dropdown {
                margin-bottom: 1.5rem;
            }
            
            .year-slider {
                margin: 1.5rem 0;
            }
            
            .apply-btn, .reset-btn {
                width: 100%;
                padding: 0.75rem;
                border: none;
                border-radius: 5px;
                font-weight: 500;
                cursor: pointer;
                transition: var(--transition);
                margin-bottom: 0.75rem;
            }
            
            .apply-btn {
                background: var(--primary-color);
                color: white;
            }
            
            .apply-btn:hover {
                background: var(--secondary-color);
            }
            
            .reset-btn {
                background: transparent;
                color: var(--primary-color);
                border: 1px solid var(--primary-color);
            }
            
            .reset-btn:hover {
                background: rgba(67, 97, 238, 0.1);
            }
            
            .content-column {
                flex: 1;
                display: flex;
                flex-direction: column;
                gap: 2rem;
            }
            
            .charts-row {
                display: flex;
                gap: 1.5rem;
            }
            
            .chart-column {
                flex: 1;
            }
            
            .chart-container {
                background: var(--card-bg);
                border-radius: 10px;
                box-shadow: var(--shadow);
                padding: 1rem;
                height: 350px;
            }
            
            .map-table-row {
                display: flex;
                flex-direction: column;
                gap: 1.5rem;
            }
            
            .map-container {
                background: var(--card-bg);
                border-radius: 10px;
                box-shadow: var(--shadow);
                overflow: hidden;
                height: 500px;
            }
            
            .map-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 1rem 1.5rem;
                border-bottom: 1px solid var(--border-color);
            }
            
            .map-title {
                font-size: 1.1rem;
                margin-bottom: 0;
                color: var(--primary-color);
            }
            
            .map-toggle-group {
                display: flex;
                gap: 0.5rem;
            }
            
            .map-toggle-btn {
                padding: 0.5rem 1rem;
                border: 1px solid var(--border-color);
                background: transparent;
                color: var(--text-color);
                border-radius: 5px;
                cursor: pointer;
                font-size: 0.8rem;
                transition: var(--transition);
            }
            
            .map-toggle-btn:hover, .map-toggle-btn.active {
                background: var(--primary-color);
                color: white;
                border-color: var(--primary-color);
            }
            
            .map-iframe {
                width: 100%;
                height: calc(500px - 60px);
                border: none;
            }
            
            .data-table-container {
                background: var(--card-bg);
                border-radius: 10px;
                box-shadow: var(--shadow);
                overflow: hidden;
            }
            
            .table-title {
                font-size: 1.1rem;
                padding: 1rem 1.5rem;
                margin-bottom: 0;
                color: var(--primary-color);
                border-bottom: 1px solid var(--border-color);
            }
            
            .table-container {
                padding: 1rem;
                max-height: 400px;
                overflow-y: auto;
            }
            
            .app-footer {
                background: var(--card-bg);
                padding: 1.5rem;
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-top: 2rem;
                border-top: 1px solid var(--border-color);
            }
            
            .footer-text {
                font-size: 0.85rem;
                color: var(--text-light);
                margin-bottom: 0;
            }
            
            .social-links {
                display: flex;
                gap: 1rem;
            }
            
            .social-icon {
                color: var(--text-light);
                font-size: 1.1rem;
                transition: var(--transition);
            }
            
            .social-icon:hover {
                color: var(--primary-color);
            }
            
            /* Responsive adjustments */
            @media (max-width: 1200px) {
                .main-content {
                    flex-direction: column;
                }
                
                .filters-column {
                    flex: 1;
                    width: 100%;
                }
                
                .charts-row {
                    flex-direction: column;
                }
            }
            
            @media (max-width: 768px) {
                .cards-row {
                    flex-direction: column;
                }
                
                .card-column {
                    min-width: 100%;
                }
                
                .app-header {
                    flex-direction: column;
                    align-items: flex-start;
                    gap: 1rem;
                }
                
                .dark-toggle-btn {
                    align-self: flex-end;
                }
            }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''

# Callbacks
@app.callback(
    Output("main-container", "className"),
    [Input("dark-toggle", "n_clicks")]
)
def toggle_dark_mode(n):
    return "dark-mode" if n % 2 == 1 else "light-mode"

@app.callback(
    [Output("region-filter", "value"),
     Output("ownership-filter", "value"),
     Output("year-slider", "value")],
    [Input("reset-filters", "n_clicks")],
    prevent_initial_call=True
)
def reset_filters(n):
    if n is None:
        raise PreventUpdate
    return None, None, [int(df["SS_FisYearName"].min()), int(df["SS_FisYearName"].max())]

@app.callback(
    Output("map-type-store", "children"),
    [Input("satellite-btn", "n_clicks"),
     Input("dark-btn", "n_clicks"),
     Input("light-btn", "n_clicks")],
    [dash.dependencies.State("map-type-store", "children")]
)
def update_map_type(sat_clicks, dark_clicks, light_clicks, current_type):
    ctx = dash.callback_context
    if not ctx.triggered:
        return current_type
    
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    if button_id == "satellite-btn":
        return "satellite"
    elif button_id == "dark-btn":
        return "dark"
    elif button_id == "light-btn":
        return "light"
    
    return current_type

@app.callback(
    [Output("satellite-btn", "className"),
     Output("dark-btn", "className"),
     Output("light-btn", "className")],
    [Input("map-type-store", "children")]
)
def update_active_button(map_type):
    base_class = "map-toggle-btn"
    active_class = "map-toggle-btn active"
    
    satellite_class = active_class if map_type == "satellite" else base_class
    dark_class = active_class if map_type == "dark" else base_class
    light_class = active_class if map_type == "light" else base_class
    
    return satellite_class, dark_class, light_class

@app.callback(
    Output("filtered-data-store", "data"),
    [Input("apply-filters", "n_clicks")],
    [dash.dependencies.State("region-filter", "value"),
     dash.dependencies.State("ownership-filter", "value"),
     dash.dependencies.State("year-slider", "value")]
)
def update_filtered_data(n_clicks, regions, ownerships, years):
    if n_clicks is None:
        raise PreventUpdate
    
    dff = df.copy()
    
    if regions:
        dff = dff[dff["Region"].isin(regions)]
    if ownerships:
        dff = dff[dff["Substation Ownership"].isin(ownerships)]
    
    if years:
        dff = dff[(dff["SS_FisYearName"] >= years[0]) & (dff["SS_FisYearName"] <= years[1])]
    
    return dff.to_json(date_format='iso', orient='split')

@app.callback(
    [Output("spend-trend-chart", "figure"),
     Output("ownership-pie-chart", "figure"),
     Output("map", "srcDoc"),
     Output("substation-table", "data")],
    [Input("filtered-data-store", "data"),
     Input("map-type-store", "children")]
)
def update_visualizations(data, map_type):
    if data is None:
        raise PreventUpdate
    
    dff = pd.read_json(data, orient='split')
    
    # Spend Trend Chart
    trend_fig = px.line(
        dff.groupby("SS_FisYearName")[["Planning Plant", "Maintenence Plant"]].mean().reset_index(),
        x="SS_FisYearName",
        y=["Planning Plant", "Maintenence Plant"],
        title="Spend Trend Analysis",
        labels={"value": "Average Spend", "SS_FisYearName": "Fiscal Year"},
        color_discrete_sequence=["#4361ee", "#f72585"]
    )
    
    trend_fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font_color="var(--text-color)",
        hovermode="x unified",
        legend_title_text="Plant Type"
    )
    
    # Ownership Pie Chart
    ownership_counts = dff["Substation Ownership"].value_counts().reset_index()
    ownership_counts.columns = ["Ownership", "Count"]
    
    pie_fig = px.pie(
        ownership_counts,
        values="Count",
        names="Ownership",
        title="Ownership Distribution",
        hole=0.4,
        color_discrete_sequence=px.colors.sequential.Blues_r
    )
    
    pie_fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font_color="var(--text-color)",
        showlegend=True
    )
    
    pie_fig.update_traces(
        textposition='inside',
        textinfo='percent+label',
        marker=dict(line=dict(color='var(--bg-color)', width=1))
    )
    
    # Map
    dff_map = dff.dropna(subset=["Latitude", "Longitude"])
    
    if map_type == "satellite":
        tiles = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
        attr = "Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community"
        map_style = "white"
    elif map_type == "dark":
        tiles = "CartoDB dark_matter"
        attr = ""
        map_style = "dark"
    else:
        tiles = "OpenStreetMap"
        attr = ""
        map_style = "light"
    
    m = folium.Map(
        location=[dff_map["Latitude"].mean(), dff_map["Longitude"].mean()],
        zoom_start=5,
        tiles=tiles,
        attr=attr
    )
    
    # Use a single color for all markers
    for _, row in dff_map.iterrows():
        folium.Marker(
            location=[row["Latitude"], row["Longitude"]],
            popup=f"""
                <b>{row['Substation Name']}</b><br>
                <table style="width:100%">
                    <tr><td>Region:</td><td>{row.get('Region', 'N/A')}</td></tr>
                    <tr><td>Ownership:</td><td>{row.get('Substation Ownership', 'N/A')}</td></tr>
                    <tr><td>Year:</td><td>{row.get('SS_FisYearName', 'N/A')}</td></tr>
                </table>
            """,
            icon=folium.Icon(color="lightblue", icon="bolt", prefix="fa")
        ).add_to(m)

    # Draw red lines connecting substations
    dff_sorted = dff_map.sort_values(by=["Region", "Substation Name"])
    coords = list(zip(dff_sorted["Latitude"], dff_sorted["Longitude"]))
    for i in range(len(coords) - 1):
        folium.PolyLine(
            locations=[coords[i], coords[i + 1]],
            color="red",
            weight=2,
            opacity=0.7
        ).add_to(m)

    
    # Table data
    table_data = dff[["Substation Name", "Region", "Substation Ownership", "SS_FisYearName"]].to_dict('records')
    
    return trend_fig, pie_fig, m._repr_html_(), table_data

if __name__ == "__main__":
    app.run(debug=True)