from io import BytesIO
import base64
import json
import numpy as np
import matplotlib.pyplot as plt
import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State
import dash_bootstrap_components as dbc
import plotly.graph_objects as go

import utils
from truegamedata import get_weapons_data


# Defaults

MAX_WEAPONS = 5                             # Sets the number of rows of recoil measurement inputs
DEFAULT_NUM_DISTANCES = 100                 # Number of distances at which to compute TTK/STK
DEFAULT_MAX_DISTANCE = 100                  # Max analysis distance in meters
DEFAULT_AIM_OFFSET = (0, 20)                # Offset from image center as (% of image width, % of image height)
DEFAULT_TARGET_DISTANCE = 50
DEFAULT_ZOOM = 4
DEFAULT_FOV = 80


# Pre-saved data for testing so we don't have to scrape TGD every time
with open('example.json', 'r') as f:
    EXAMPLE_DATA = json.load(f)

with open('markdown/about.md', 'r') as f:
    ABOUT_TEXT = f.read()

with open('markdown/fetch-help.md', 'r') as f:
    FETCH_TEXT = f.read()

with open('markdown/howto.md', 'r') as f:
    HOWTO_TEXT = f.read()


def fig_to_uri(in_fig):
    # type: (plt.Figure) -> str
    """
    Save a figure as a URI, copied from
    https://github.com/plotly/dash-sample-apps/blob/master/apps/dash-nlp/wordcloud_matplotlib.py
    """
    out_img = BytesIO()
    in_fig.savefig(out_img, format='png')
    in_fig.clf()
    plt.close('all')
    out_img.seek(0)  # rewind file
    encoded = base64.b64encode(out_img.read()).decode("ascii").replace("\n", "")
    return "data:image/png;base64,{}".format(encoded)


def get_button_pressed():
    """
    Return name of button pressed when a click event triggers

    :return: str id of button object
    """
    ctx = dash.callback_context
    button_id = 'No clicks yet'
    if ctx.triggered:
        if ctx.triggered[0]['value'] is not None:
            button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    return button_id


def update_spreads(data, *spreads):
    """
    Update data variable with recoil spreads and return spreads as strings for HTML outputs

    :param data: TGD data
    :param spreads: list of recoil spreads [x1, y1, x2, y2, ...]
    :return: list of strings with degree symbol ["x1°", "y1°", ...]
    """
    for i, wpn in enumerate(data):
        spread_x, spread_y = spreads[i * 2: i * 2 + 2]
        wpn['spread'] = (float(spread_x), float(spread_y))
    return data, [f"{s:.1f}°" for s in spreads]


def make_slider_col(text, min, max, step, value, mark_values, mark_fmt, width):
    marks = {v: mark_fmt.format(v) for v in mark_values}
    slider = dcc.Slider(id=text, min=min, max=max, step=step, value=value, marks=marks)
    div = html.Div([slider], style={'height': '50px'})
    col = dbc.Col(div, width=width)
    return col


def make_recoil_slider_col(dim, num, width):
    """
    Generate a Slider for recoil measurements in a Dash Bootstrap column

    :param dim:
    :param num:
    :param width:
    :return:
    """
    col = make_slider_col(
        text=f"spread-{dim}-input-{num}",
        min=0.1,
        max=1.5,
        step=0.1,
        value=1.0,
        mark_values=[0.5, 1],
        mark_fmt="{:.2f}°",
        width=width
    )
    return col


def make_aim_slider_col(dim, width):
    """
    Generate a Slider for cross hair aim offset in a Dash Bootstrap column

    :param dim:
    :param width:
    :return:
    """
    if dim == 'x':
        value = DEFAULT_AIM_OFFSET[0]
    else:
        value = DEFAULT_AIM_OFFSET[1]
    col = make_slider_col(
        text=f"aim-{dim}-input",
        min=-50,
        max=50,
        step=5,
        value=value,
        mark_values=[-50, 0, 50],
        mark_fmt="{:.0f}%",
        width=width
    )
    return col


def make_distance_slider_col(width):
    """
    Generate a Slider for maximum analysis distance in a Dash Bootstrap column

    :param width:
    :return:
    """
    col = make_slider_col(
        text='distance-input',
        min=10,
        max=150,
        step=10,
        value=DEFAULT_MAX_DISTANCE,
        mark_values=[10, 50, 100, 150],
        mark_fmt="{:.0f}m",
        width=width
    )
    return col


def make_target_distance_slider_col(width):
    """
    Generate a Slider for hit box target distance in a Dash Bootstrap column

    :param width:
    :return:
    """
    col = make_slider_col(
        text='target-distance-input',
        min=10,
        max=100,
        step=10,
        value=DEFAULT_TARGET_DISTANCE,
        mark_values=[10, 50, 100],
        mark_fmt="{:.0f}m",
        width=width
    )
    return col


def make_zoom_slider_col(width):
    """
    Generate a Slider for zoom level in a Dash Bootstrap column

    :param width:
    :return:
    """
    col = make_slider_col(
        text='zoom-input',
        min=1,
        max=10,
        step=1,
        value=DEFAULT_ZOOM,
        mark_values=[1, 4, 7, 10],
        mark_fmt="{:.0f}x",
        width=width
    )
    return col


def make_fov_slider_col(width):
    """
    Generate a Slider for field of view in a Dash Bootstrap column

    :param width:
    :return:
    """
    col = make_slider_col(
        text='fov-input',
        min=60,
        max=120,
        step=10,
        value=DEFAULT_FOV,
        mark_values=[60, 80, 100, 120],
        mark_fmt="{:.0f}°",
        width=width
    )
    return col


def make_recoil_divs(rows):
    """
    Generate rows of recoil slider columns

    :param rows:
    :return:
    """
    out = []
    for i in range(rows):
        row = dbc.Row([
            make_recoil_slider_col('x', i, width=5),
            dbc.Col(html.Div(["1.0°"], id=f"spread-x-div-{i}"), width=1),
            make_recoil_slider_col('y', i, width=5),
            dbc.Col(html.Div(["1.0°"], id=f"spread-y-div-{i}"), width=1),
        ])
        out.append(row)
    return out


def make_weapon_name_divs(rows):
    """
    Generate rows of weapon name divs

    :param rows:
    :return:
    """
    out = []
    for i in range(rows):
        row = html.Div(id=f"weapon-name-{i}", style={'height': '50px'})
        out.append(row)
    return out


# BEGIN BUILDING THE APP

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.SLATE, 'assets/stylesheet.css'])
server = app.server

# Initialize main TTK/STK figure
fig = go.Figure()
fig.update_layout(
    width=1100,
    height=500,
    hovermode='x unified',
    template='plotly_dark',
)
fig.update_xaxes(title_text="Distance [m]", range=[1, 100])
fig.update_yaxes(title_text="Time-to-kill [s]", range=[1, 5])


app.layout = html.Div(
    html.Div([


        # ABOUT PAGE
        html.Div([
            html.H2("Call of Duty weapon performance tool", style={'display': 'inline-block'}),
            dbc.Button("What is this?", id='about-button', style={'float': 'right'}),
        ]),
        dbc.Modal(
            [
                dbc.ModalHeader("What is this?"),
                dbc.ModalBody(dcc.Markdown(ABOUT_TEXT)),
                dbc.ModalFooter(
                    dbc.Button("Close", id="about-close", className="ml-auto")
                ),
            ],
            id="about-modal",
            size='lg',
        ),
        html.Br(),


        # LINK INPUT SECTION
        dbc.Card([
            dbc.CardHeader("Data entry", style={'font-size': 24, 'textAlign': 'center'}),
            dbc.CardBody([
                html.Div([
                    html.P("Link to TrueGameData comparison page:",
                           style={'margin-right': '10px', 'display': 'inline-block'}),
                    dcc.Input(id='link-input', type='text', value="", placeholder="Paste share link here",
                              style={'width': '400px', 'margin-right': '10px', 'display': 'inline-block'}),
                    dbc.Button('Fetch data', id='fetch-button', size='sm',
                               style={'font-size': 16, 'margin-right': '10px', 'display': 'inline-block'}),
                    dbc.Button('Use example data', id='example-button', size='sm',
                               style={'font-size': 16, 'margin-right': '10px', 'display': 'inline-block'}),
                    dbc.Button('Show help', id='fetch-help-button', size='sm',
                               style={'font-size': 16, 'display': 'inline-block'}),
                    dbc.Collapse(
                        dcc.Markdown(FETCH_TEXT),
                        id='fetch-help-collapse',
                    ),
                    dcc.Loading(id='fetch-loading', type='default',
                                children=html.Div(id='weapons-data', style={'margin-top': 25, 'margin-bottom': 25})),
                ], style={'width': '1200px', 'margin': '0 auto'})
            ]),
        ]),
        dcc.Store(id='weapons-data-store'),
        html.Br(),


        # RECOIL MEASUREMENTS SECTION
        dbc.Modal(
            [
                dbc.ModalHeader("Measuring your recoil spread"),
                dbc.ModalBody(
                    dcc.Markdown(HOWTO_TEXT)
                ),
                dbc.ModalFooter(
                    dbc.Button("Close", id="howto-close", className="ml-auto")
                ),
            ],
            id="howto-modal",
            size='lg',
        ),
        dbc.Row([
            dbc.Col(html.Div([html.Br(), html.Br()] + make_weapon_name_divs(MAX_WEAPONS)), width=2),
            dbc.Col(
                html.Div(
                    [
                        html.Center([
                            "Recoil spread (degrees)",
                            dbc.Button("Show help", id='howto-button', size='sm',
                                       style={'margin-left': 20, 'display': 'inline-block'})
                        ]),
                        dbc.Row([
                            dbc.Col([html.Div("Horizontal", style={'textAlign': 'center'})], width=5),
                            dbc.Col([], width=1),
                            dbc.Col([html.Div("Vertical", style={'textAlign': 'center'})], width=5),
                            dbc.Col([], width=1),
                        ])
                    ] + make_recoil_divs(MAX_WEAPONS)
                ), width=5
            ),
            dbc.Col(width=1),
            dbc.Col(
                html.Div(
                    [
                        html.Div([
                            html.Center("Crosshair offset (percent of enemy height)"),
                            dbc.Row([
                                make_aim_slider_col('x', width=5),
                                dbc.Col(html.Div(id=f"aim-x-div"), width=1),
                                make_aim_slider_col('y', width=5),
                                dbc.Col(html.Div(id=f"aim-y-div"), width=1),
                            ]),
                        ], style={'width': '90%'}),
                        html.Div([
                            html.Center("Max distance (meters)"),
                            dbc.Row([
                                make_distance_slider_col(width=9),
                                dbc.Col(html.Div(id=f"distance-div"), width=3)
                            ])
                        ]),
                        html.Div([
                            html.Div("Add ADS to TTK:", style={'display': 'inline-block'}),
                            dbc.RadioItems(
                                id='radio-plot-ads',
                                options=[{'label': 'Yes', 'value': 'yes'},
                                         {'label': 'No', 'value': 'no'}],
                                value='yes',
                                inline=True,
                                style={'margin-left': 20, 'display': 'inline-block'},
                            )
                        ]),
                        html.Div([
                            html.Div("Plot mode:", style={'display': 'inline-block'}),
                            dbc.RadioItems(
                                id='radio-plot-mode',
                                options=[{'label': 'TTK', 'value': 'ttk'},
                                         {'label': 'STK', 'value': 'stk'},
                                         {'label': 'DPS', 'value': 'dps'}],
                                value='ttk',
                                inline=True,
                                style={'margin-left': 20, 'display': 'inline-block'},
                            )
                        ], style={'margin-top': 5}),
                        html.Br(),
                        dbc.Button('Generate performance plot', id='plot-button', block=True),
                        html.Div("", id='perf-plot-err', style={'textAlign': 'center', 'margin-top': 5}),
                    ]
                ), width=4
            ),
        ]),
        html.Br(),


        # PERFORMANCE PLOT SECTION
        dcc.Store(data='ttk', id='perf-plot-store'),
        dbc.Card([
            dbc.CardHeader("Estimated performance plot", id='perf-plot-header', style={'font-size': 24, 'textAlign': 'center'}),
            dbc.CardBody([
                html.Div([
                    dbc.Row([
                        dbc.Col([], width=2),
                        dbc.Col([
                            html.Div("Change X-axis scale: ", style={'display': 'inline-block'}),
                            dbc.RadioItems(
                                id='radio-x-axis',
                                options=[{'label': 'Linear', 'value': 'lin'},
                                         {'label': 'Logarithmic', 'value': 'log'}],
                                value='lin',
                                inline=True,
                            ),
                        ], width=3),
                        dbc.Col([
                            html.Div("Change Y-axis scale: ", style={'display': 'inline-block'}),
                            dbc.RadioItems(
                                id='radio-y-axis',
                                options=[{'label': 'Linear', 'value': 'lin'},
                                         {'label': 'Logarithmic', 'value': 'log'}],
                                value='lin',
                                inline=True,
                            ),
                        ], width=3),
                        dbc.Col([
                            html.Div("No-recoil results: ", style={'display': 'inline-block'}),
                            dbc.RadioItems(
                                id='radio-show-nr',
                                options=[{'label': 'Hide', 'value': 'hide'},
                                         {'label': 'Show', 'value': 'show'}],
                                value='hide',
                                inline=True,
                            ),
                        ], width=2),
                        dbc.Col([], width=2),
                    ]),
                    html.Br(),
                    html.Center(
                        dcc.Loading(
                            id='perf-plot-loading',
                            type='default',
                            children=dcc.Graph(
                                id='perf-plot-figure',
                            )
                        ),
                    )
                ], style={'textAlign': 'center'}),
            ]),
        ]),
        html.Br(),


        # RECOIL SPREAD IMAGE SECTION
        dbc.Card([
            dbc.CardHeader("Recoil area viewer", style={'font-size': 24, 'textAlign': 'center'}),
            dbc.CardBody([
                dbc.Row([
                    dbc.Col(
                        html.Div([
                            html.Center("Target distance (meters)"),
                            dbc.Row([
                                make_target_distance_slider_col(width=9),
                                dbc.Col(html.Div(id=f"target-distance-div"), width=3)
                            ]),
                            html.Br(),
                        ]), width=4,
                    ),
                    dbc.Col(
                        html.Div([
                            html.Center("Zoom level"),
                            dbc.Row([
                                make_zoom_slider_col(width=9),
                                dbc.Col(html.Div(id=f"zoom-div"), width=3)
                            ]),
                            html.Br(),
                        ]), width=3,
                    ),
                    dbc.Col(
                        html.Div([
                            html.Center("Field of view"),
                            dbc.Row([
                                make_fov_slider_col(width=9),
                                dbc.Col(html.Div(id=f"fov-div"), width=3)
                            ]),
                            html.Br(),
                        ]), width=3,
                    ),
                    dbc.Col(
                        html.Div([
                            html.Center("Weapon"),
                            html.Div([
                                dcc.Dropdown(id='wpn-dropdown', clearable=False, style={'width': 180})
                            ]),
                            html.Br(),
                        ]), width=2,
                    ),
                ], style={'width': '90%', 'margin': '0 auto'}),
                html.Div([
                    html.Img(id='target-img', src='', style={'max-width': '80%'})
                ], style={'textAlign': 'center'})
            ]),
        ])
    ], style={'width': 1200, 'margin': '0 auto'}),
    style={'margin': 20}
)


# Organize outputs, inputs, and states for weapons and recoil measurements
weapon_name_outputs = []
spread_inputs = []
spread_states = []
spread_outputs = []
for n in range(MAX_WEAPONS):
    weapon_name_outputs.append(Output(f'weapon-name-{n}', 'children'))
    spread_inputs.append(Input(f'spread-x-input-{n}', 'value'))
    spread_inputs.append(Input(f'spread-y-input-{n}', 'value'))
    spread_states.append(State(f'spread-x-input-{n}', 'value'))
    spread_states.append(State(f'spread-y-input-{n}', 'value'))
    spread_outputs.append(Output(f'spread-x-div-{n}', 'children'))
    spread_outputs.append(Output(f'spread-y-div-{n}', 'children'))


# @app.callback(
#     spread_outputs,
#     spread_inputs,
#     [State('weapons-data-store', 'data')]
# )
# def update_spread_divs(*args):
#     spreads = args[:-1]
#     data = args[-1]
#     if data is not None:
#         _, spreads = update_spreads(data, *spreads)
#     else:
#         _, spreads = update_spreads([], *spreads)
#     return spreads


@app.callback(
    [Output('aim-x-div', 'children'), Output('aim-y-div', 'children')],
    [Input('aim-x-input', 'value'), Input('aim-y-input', 'value')]
)
def update_aim_divs(*args):
    return [f"{s}%" for s in args]


@app.callback(
    Output('distance-div', 'children'),
    Input('distance-input', 'value')
)
def update_distance_div(distance):
    return f"{distance} m"


@app.callback(
    Output('target-distance-div', 'children'),
    Input('target-distance-input', 'value')
)
def update_target_distance_div(target_distance):
    return f"{target_distance} m"


@app.callback(
    Output('zoom-div', 'children'),
    Input('zoom-input', 'value')
)
def update_zoom_div(zoom):
    return f"{zoom}x"


@app.callback(
    Output('fov-div', 'children'),
    Input('fov-input', 'value')
)
def update_fov_div(fov):
    return f"{fov}°"


@app.callback(
    Output('about-modal', 'is_open'),
    [Input('about-button', 'n_clicks'), Input('about-close', 'n_clicks')],
    [State('about-modal', 'is_open')]
)
def toggle_about_modal(n1, n2, is_open):
    if n1 or n2:
        return not is_open
    return is_open


@app.callback(
    Output('howto-modal', 'is_open'),
    [Input('howto-button', 'n_clicks'), Input('howto-close', 'n_clicks')],
    [State('howto-modal', 'is_open')]
)
def toggle_howto_modal(n1, n2, is_open):
    if n1 or n2:
        return not is_open
    return is_open


@app.callback(
    [Output('weapons-data-store', 'data'),
     Output('weapons-data', 'children'),
     Output('wpn-dropdown', 'options'),
     Output('wpn-dropdown', 'value')] + weapon_name_outputs + spread_outputs,
    [Input('fetch-button', 'n_clicks'),
     Input('example-button', 'n_clicks')] + spread_inputs,
    [State('link-input', 'value'), State('weapons-data-store', 'data')]
)
def fetch_data(btn1, btn2, *args):
    spreads = args[:-2]
    link, data = args[-2:]
    if data is not None:
        data, spreads = update_spreads(data, *spreads)
    else:
        data, spreads = update_spreads([], *spreads)
    button_id = get_button_pressed()
    fetch = (button_id == 'fetch-button')
    example = (button_id == 'example-button')

    if fetch:
        if 'share=' in link:
            data = get_weapons_data(link)
            weapons, output_str = get_weapon_text(data)
        else:
            weapons = ["N/A" for _ in range(MAX_WEAPONS)]
            output_str = "Invalid link."
    elif example:
        data = EXAMPLE_DATA
        weapons, output_str = get_weapon_text(data)
    else:
        if data is not None:
            weapons, output_str = get_weapon_text(data)
        else:
            data, spreads = update_spreads([], *spreads)
            weapons = ["N/A" for _ in range(MAX_WEAPONS)]
            output_str = "Copy a share link and click 'Fetch data' to get started."
    weapon_options = [{'label': wpn, 'value': i} for i, wpn in enumerate(weapons) if wpn != 'N/A']
    if len(weapon_options) > 0:
        weapon = weapon_options[0]['value']
    else:
        weapon = None
    return (data,) + (output_str, weapon_options, weapon) + tuple(weapons) + tuple(spreads)


def get_weapon_text(data):
    weapons = [d['gun'] for d in data]
    if len(weapons) < MAX_WEAPONS:
        weapons.extend(["N/A" for _ in range(MAX_WEAPONS - len(weapons))])
    output_str = f"{len(data)} weapons found: " + ', '.join(weapons[:len(data)])
    return weapons, output_str


@app.callback(
    Output('fetch-help-collapse', 'is_open'),
    [Input('fetch-help-button', 'n_clicks')],
    [State('fetch-help-collapse', 'is_open')],
)
def toggle_fetch_help(n_clicks, is_open):
    if n_clicks:
        return not is_open
    return is_open


@app.callback(
    [Output('perf-plot-figure', 'figure'),
     Output('perf-plot-err', 'children'),
     Output('perf-plot-header', 'children'),
     Output('perf-plot-store', 'data')],
    [Input('plot-button', 'n_clicks'),
     Input('radio-x-axis', 'value'),
     Input('radio-y-axis', 'value'),
     Input('radio-show-nr', 'value')],
    [State('weapons-data-store', 'data'),
     State('perf-plot-store', 'data'),
     State('radio-plot-mode', 'value'),
     State('aim-x-input', 'value'),
     State('aim-y-input', 'value'),
     State('radio-plot-ads', 'value'),
     State('distance-input', 'value')] + spread_states
)
def generate_plot(n_clicks, x_mode, y_mode, show_nr, data, stored_mode, new_mode, aim_x, aim_y, ads, d_max, *spreads):
    button_id = get_button_pressed()
    plot = (button_id == 'plot-button')
    header_mode = {
        'ttk': "(Time-to-kill)",
        'stk': "(Shots-to-kill)",
        'dps': "(Damage per second)",
    }
    log_x = (x_mode == 'log')
    log_y = (y_mode == 'log')
    msg = ""

    if plot:
        mode = new_mode
        if len(data) > 0:
            distances = np.linspace(1, d_max, d_max)
            data, spreads = update_spreads(data, *spreads)
            aim_offset = (0.01 * aim_x, 0.01 * aim_y)
            aim_center = utils.get_aim_center(aim_offset)
            try:
                results = utils.analyze(data, distances, aim_center, ads=(ads == 'yes'))
            except ValueError:
                return fig, "Cross hair must overlap with enemy hit-box. " \
                           "Use the recoil spread visualizer below to see cross hair location"
            utils.plot_results(fig, distances, data, results, mode=mode, log_x=log_x, log_y=log_y, show_nr=show_nr)
        else:
            msg = "No data found. Fetch data first!"
    else:
        mode = stored_mode
        utils.update_fig(fig, mode=mode, log_x=log_x, log_y=log_y, show_nr=show_nr)
    header = "Estimated performance plot " + header_mode[mode]
    return fig, msg, header, mode


@app.callback(
    Output('target-img', 'src'),
    [Input('aim-x-input', 'value'),
     Input('aim-y-input', 'value'),
     Input('target-distance-input', 'value'),
     Input('zoom-input', 'value'),
     Input('fov-input', 'value'),
     Input('wpn-dropdown', 'value')] + spread_inputs,
    [State('weapons-data-store', 'data')]
)
def update_image(aim_x, aim_y, dist, zoom, fov, wpn_idx, *spreads_and_data):
    """
    Update image of recoil spread and enemy hit-box

    :param aim_x:
    :param aim_y:
    :param dist:
    :param zoom:
    :param fov:
    :param wpn_idx:
    :param spreads_and_data:
    :return: figure URI, error message
    """
    spreads = spreads_and_data[:-1]
    data = spreads_and_data[-1]
    if data is not None:
        if len(data) > 0:
            if wpn_idx is None:
                return ""
            data, spreads = update_spreads(data, *spreads)
            aim_offset = (0.01 * aim_x, 0.01 * aim_y)
            aim_center = utils.get_aim_center(aim_offset)
            target_fig = utils.plot_target_area(data[wpn_idx], dist, aim_center, zoom=zoom, fov=fov)
            target_fig_uri = fig_to_uri(target_fig)
            return target_fig_uri
        else:
            return ""
    else:
        return ""


if __name__ == '__main__':
    from argparse import ArgumentParser
    parser = ArgumentParser()
    parser.add_argument("-d", "--debug", default=False, action="store_true",
                        help="run in debug mode (development only)")
    args = parser.parse_args()
    app.run_server(debug=args.debug)