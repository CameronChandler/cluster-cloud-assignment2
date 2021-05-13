@api.route('/home/<x>')
class Language(Resource):

    @api.marshal_with(a_language, envelope='the_data')
    def get(self):
        all_languages = db.view('_all_docs', include_docs=True)
        html = get_html(x)
        return html

@api.route('/correlation/<xy>')
class Language(Resource):

    @api.marshal_with(a_language, envelope='the_data')
    def get(self, xy):
        all_languages = db.view('_all_docs', include_docs=True)
        html = get_html(xy)
        return html

def get_html(page):
    head = f'''<!DOCTYPE html>
    <html lang="en">
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">

            <title>COMP90024 Application</title>

            <!--Lato font-->
            <link href='http://fonts.googleapis.com/css?family=Lato:400,700' rel='stylesheet' type='text/css'>

            <style>
            h1 {{
                font-family: "Lato", sans-serif; 
                font-size: 50px;
            }}
            p {{
                font-family: "Lato", sans-serif;
                font-size: 15px;
            }}
            img {{
                font-family: "Lato", sans-serif;
                font-size: 15px;
            }}

            .sidenav {{
                height: 100%;
                width: 160px;
                position: fixed;
                z-index: 1;
                top: 0;
                left: 0;
                background-color: #111;
                overflow-x: hidden;
                padding-top: 20px;
            }}

            .sidenav a {{
                padding: 6px 8px 6px 16px;
                text-decoration: none;
                font-size: 25px;
                color: #818181;
                display: block;
            }}

            .sidenav a:hover {{
                color: #f1f1f1;
            }}

            .main {{
                margin-left: 160px; /* Same as the width of the sidenav */
                font-size: 28px;
                padding: 0px 10px;
            }}

            @media screen and (max-height: 450px) {{
                .sidenav {{padding-top: 15px;}}
                .sidenav a {{font-size: 18px;}}
            }}
            </style>
        </head>
        <body><div class="main">
            <h1>Literacy on Twitter</h1>

            <div class="sidenav">
                <a href="#home">Home</a>
                <a href="#correlations">Correlations</a>
            </div>'''

    # If correlation
    if '__' in page:
        x, y = page.split('__')
        gen_graph(x, y)
        body = '''<div>

                <p>Select an x variable, a y variable and click "Plot"</p>
            
                <select id ="dropDownIdX">
                    <option value="x">-- x variable --</option>
                    <option value="x_unemployment">Unemployment</option>
                    <option value="x_income">Income</option>
                    <option value="x_word_length">Word Length</option>
                    <option value="x_education">Education</option>
                </select>

                <select id ="dropDownIdY">
                    <option value="y">-- y variable --</option>
                    <option value="y_unemployment">Unemployment</option>
                    <option value="y_income">Income</option>
                    <option value="y_word_length">Word Length</option>
                    <option value="y_education">Education</option>
                </select>

                <br>
                <input class="SubmitButton" type="submit" name="SUBMITBUTTON"  value="Plot" style="font-size:20px; " />
            </div>
            <script src = "//code.jquery.com/jquery-3.0.0.min.js"></script> <!-- add jquery library-->
            <script type = "text/javascript">
            $('.SubmitButton').click(function(){{ // on submit button click
            
                var x_choice = $('#dropDownIdX :selected').val(); // get the selected x option value
                var y_choice = $('#dropDownIdY :selected').val(); // get the selected y option value
                window.location.href = "http://"+x_choice+"__"+y_choice+".html" // Redirect
            }});
            
            </script>

            <img src="{x}__{y}.png" alt="img" width="104" height="142">
        </div></body>
    </html>'''

    else:
        x = page
        gen_graph(x)
        body = '''<div>

                <p>Select a variable and click "Plot"</p>
            
                <select id ="dropDownId">
                    <option value="x">-- variable --</option>
                    <option value="unemployment">Unemployment</option>
                    <option value="income">Income</option>
                    <option value="word_length">Word Length</option>
                    <option value="education">Education</option>
                </select>

                <br>
                <input class="SubmitButton" type="submit" name="SUBMITBUTTON"  value="Plot" style="font-size:20px; " />
            </div>
            <script src = "//code.jquery.com/jquery-3.0.0.min.js"></script> <!-- add jquery library-->
            <script type = "text/javascript">
            $('.SubmitButton').click(function(){{ // on submit button click
            
                var x_choice = $('#dropDownId :selected').val(); // get the selected option value
                window.location.href = "http://"+x_choice+".html" // Redirect
            }});
            
            </script>

            <img src="{x}.png" alt="img" width="104" height="142">
        </div></body>
    </html>'''

    return head + body



#### Graphing Code ####
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np

import shapefile
from descartes import PolygonPatch
import matplotlib
import matplotlib.colors as mcolors
from tqdm import tqdm

import json
from collections import defaultdict as dd

def get_name(x, col=True):
    i = 0 if col else 1
    return {'Unemployment': ['UNEMPLOYMENT_RATE', 'Unemployment Rate (%)'], 
            'Income': ['MEDIAN_INCOME', 'Median Annual Personal Income ($`000s)'], 
            'Education': ['TOTAL', 'Adults with Non-School Qualifications (%)']}[x][i]

def graph_map(x, data):
    loc_ids = pd.DataFrame({'AREA': ['Greater Sydney',
                                    'Greater Melbourne',
                                    'Greater Brisbane',
                                    'Greater Adelaide',
                                    'Greater Perth',
                                    'Greater Hobart',
                                    'Greater Darwin',
                                    'Australian Capital Territory'], 'ID': [1, 3, 4, 7, 8, 10, 13, 14]})
    if 'ID' not in data:
        data = pd.merge(data, loc_ids, on='AREA')

    locs = shapefile.Reader('GCCSA_2016_AUST.shp')

    fig, ax = plt.subplots(figsize=(20, 10))

    for loc_id, loc in tqdm(enumerate(locs.iterShapes())):
        if loc_id > 15:
            continue
        BLUE, GREY = '#FFFFFF', '#888888'
        
        norm = matplotlib.colors.Normalize(vmin=data[get_name(x)].min(), vmax=data[get_name(x)].max(), clip=True)
        mapper = plt.cm.ScalarMappable(norm=norm, cmap=plt.cm.viridis)

        # 2019
        if loc_id in data.ID.values:
            col = mcolors.to_hex(mapper.to_rgba(data[data.ID == loc_id][get_name(x)].iloc[0]))
        else:
            col = GREY


        ax.add_patch(PolygonPatch(loc, fc=col, ec=BLUE, alpha=0.9, zorder=10, linewidth=0.2))
        ax.axis('scaled')

    ax.set_title(get_name(x, col=False))
    ax.axis('off')

    left, bottom, width, height = 0.75, 0.2, 0.02, 0.6
    cbar_ax = fig.add_axes([left, bottom, width, height])
    fig.colorbar(mapper, cax=cbar_ax, orientation='vertical', cmap='viridis')
    cbar_ax.set_xlabel(get_name(x, col=False))

    plt.savefig(f'{x}.png', dpi=fig.dpi*2, bbox_inches="tight")
    #plt.show()

def graph_corr(x, y, data):
    fig, ax = plt.subplots(figsize=(12, 6), tight_layout=True)

    ax.scatter(data[get_name(x)], data[get_name(y)])
    ax.set_xlabel(get_name(x, col=False))
    ax.set_ylabel(get_name(y, col=False))

    sns.despine()
    plt.savefig(f'{x}__{y}.png', dpi=2*fig.dpi)
    #plt.show()

def gen_graph(x, y=None):

    plt.rc('axes', titlesize=18)     # fontsize of the axes title
    plt.rc('axes', labelsize=14)    # fontsize of the x and y labels
    plt.rc('xtick', labelsize=13)    # fontsize of the tick labels
    plt.rc('ytick', labelsize=13)    # fontsize of the tick labels
    plt.rc('legend', fontsize=13)    # legend fontsize
    plt.rc('font', size=13)          # controls default text sizes

    def read_data(file):
        with open(file+'.json') as f:
            data = json.load(f)

            dataframe = dd(list)
            for feature in data['features']:
                for column, value in feature['properties'].items():
                    dataframe[column].append(value)

        return pd.DataFrame(dataframe)

    income = read_data('data_income')
    income.columns = [ 'GCCSA', 'MEDIAN_INCOME', 'AREA']

    edu_emp = read_data('data_education_employment')
    edu_emp.columns = ['UNEMPLOYMENT_RATE', 'TOTAL', 'AREA', 'YEAR', 'BACHELORS', 
                       'POST_GRAD', 'DIPLOMA', 'GCCSA', 'CERT', 'NA', 'CENSUS_CERT']

    data = pd.merge(income, edu_emp, on=['AREA', 'GCCSA']).drop('GCCSA', axis=1)
    data = data[(data.AREA.str.contains('Greater')) | (data.AREA == 'Australian Capital Territory')].reset_index(drop=True)
    
    if y is None:
        graph_map(x, data)
    else:
        graph_corr(x, y, data)