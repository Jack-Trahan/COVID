'''
Track COVID-19 Progress in the state of Florida
'''

import urllib.request
import pandas as pd
from pathlib import Path
import datetime as dt
import os

import plotly.express as px
import plotly.graph_objects as go



# Florida Dept. of Health Open Data: Florida COVID19 Case Line Data
URL = "https://opendata.arcgis.com/datasets/37abda537d17458bae6677b8ab75fcb9_0.csv"

CSV_FILE = Path("./data/state.csv")


class StateCovid:
    def __init__(self):

        # Retrieve and load data into a DataFrame
        if not CSV_FILE.is_file():
            print("Downloading data...")
            self.download_data()
            print("Done.\n")
        else:
            # Check if the file date is current
            csv_date = dt.datetime.fromtimestamp((os.path.getmtime(CSV_FILE))).date()
            today = dt.date.today()
            if csv_date == today:
                print("Local file is up to date.")
            else:
                print("Data is out of date.")
                self.download_data()


        self.df = pd.read_csv(URL)


        self.process()


    def download_data(self):
        print("Downloading Current Data...")
        try:
            urllib.request.urlretrieve(URL, './data/state.csv')
            print("Download success!")
        except Exception as e:
            print("An error occured:", e)
            print("Using old data instead...")





    def process(self):
        ''' whittle data down to what we are using'''

        to_del = ['Jurisdiction', 'Origin', 'Travel_related', 'Case_', 'EDvisit', 'Contact', 'Hospitalized']
        for col in to_del:
            self.df.drop(col, axis=1, inplace=True)

        # Make Died column bool
        self.df['Died'] = self.df['Died'].map({'Yes':1})
        self.df['Died'].fillna(0, inplace=True)

        # Set dtypes
        self.df = self.df.astype({'Died':'category', 'Gender':'category', 'County':'category'})
        self.df["EventDate"] = pd.to_datetime(self.df["EventDate"])
        self.df.rename({"EventDate" : "Date"}, axis=1, inplace=True)


        # Total Case Counts per date
        self.case_counts = pd.DataFrame(self.df['Date'].value_counts()).sort_index()
        self.case_counts.rename({'Date':'New Cases'}, axis=1, inplace=True)
        self.case_counts.reset_index(inplace=True)
        self.case_counts.rename(columns={'index':'Date'}, inplace=True)
        # Create a 'Total Cases Column
        self.case_counts['Total Cases'] = self.case_counts['New Cases'].cumsum()
        # Drop two dates from early last year
        self.case_counts.drop([0,1], inplace=True)


        # First Resample to weekly to smooth out trajectory
        self.case_counts.set_index('Date', inplace=True)
        r = self.case_counts.resample('W-MON')



        self.week = pd.DataFrame()
        self.week['Total Cases'] = r['Total Cases'].last()
        self.week['New Cases'] = r['New Cases'].sum()

        # Fill gap in total cases
        self.week['Total Cases'].fillna(method='ffill', inplace=True)

        # Drop some eliminate wild fluctuation in early data trajectory
        self.week = self.week.iloc[3:]

        # Drop incomplete current week
        df = self.week
        if df.index[-1].strftime ('%d%m%Y') >= dt.datetime.today().strftime ('%d%m%Y'):
                df.drop([df.index[-1]], inplace=True)





    def gender_chart(self):
        ''' Display Gender Stats '''
        self.gender = pd.DataFrame()
        self.gender['Number'] = self.df['Gender'].value_counts()
        self.gender.reset_index(inplace=True)

        ''' Confirmed Cases by Gender '''
        fig = px.pie(self.gender, values='Number', names='index')
        fig.update_layout(title="Gender of Confirmed Cases")
        fig.update_traces(textposition='inside', textinfo='label+percent')
        fig.show()

        ''' Deceased by Gender '''
        fig = px.pie(self.df, values='Died', names='Gender')
        fig.update_layout(title="Gender of Deceased")
        fig.update_traces(textposition='inside', textinfo='label+percent')
        fig.show()

    def trajectory(self):

        ''' Total Cases v Date linear '''
        # Drop Dates where Total Cases where beloew 50
        df = self.week
        fig = go.Figure()
        fig.add_trace(go.Scatter(name='Total Cases', mode='lines',
                                 x=df.index, y=df['Total Cases'],
                                line = {'shape':'spline', 'smoothing':.9},
                                ))
        fig.update_layout(title= {'text':"Total Confirmed Forida COVID-19 Cases (" + dt.date.today().strftime("%B %d, %Y") + ")",
                         'xanchor':'center', 'x':0.46})

        fig.update_xaxes(type="date", ticks='outside', title_text="")
        fig.update_yaxes(type="linear", ticks='outside', title_text="Total Cases")
        fig.show()








        ''' Trajectory Logrithmic '''
        fig = go.Figure()
        fig.add_trace(go.Scatter(name='Florida', mode='lines+markers',
                                 x=self.week['Total Cases'], y=self.week['New Cases'],
                                line = {'shape':'spline', 'smoothing':.9},
                                ))
        fig.update_layout(title= {'text':"Trajectory of Florida COVID-19 Confirmed Cases (" + dt.date.today().strftime("%B %d, %Y") + ")",
                         'xanchor':'center', 'x':0.46})

        fig.update_xaxes(type="log", ticks='outside', title_text="Total Confired Cases")
        fig.update_yaxes(type="log", ticks='outside', title_text="Weekly New Cases")
        fig.show()

    def growth_factor(self):
        self.week['Growth Factor'] = round((self.week['New Cases'] / self.week['New Cases'].shift(1)), 2).fillna(0)

        # Only plot completed weeks
        # Check if the file date is current
        csv_date = dt.datetime.fromtimestamp((os.path.getmtime(CSV_FILE))).date()
        today = dt.date.today()
        df = self.week


        x = df.index
        y = df['Growth Factor']


        fig = go.Figure()
        fig.add_trace(go.Scatter(name='Growth Factor', mode='lines+markers',
                                 x=x, y=y,
                                line = {'shape':'spline', 'smoothing':.9},
                                ))
        fig.update_layout(title= {'text':"Florida COVID-19 Weekly Growth Factor",
                         'x':0.5})

        fig.update_xaxes(type="date", ticks='outside', title_text="")
        fig.update_yaxes(type="linear", ticks='outside', title_text="", range=[0,5])
        # Draw a Horizontal Line at Growth Factor = 1
        fig.add_shape(type='line',
                     x0=df.index[0], x1=df.index[-1],
                      y0=1, y1=1,
                      line=dict(
                          color='black',
                          width=4,
                          dash='dot'))
        # Label horizontal line with a scatter
        fig.add_trace(go.Scatter(
            x=[dt.datetime(2020,3,7)],
            y=[1.1],
            text=["Growth Factor = 1"],
            mode="text",
            showlegend=False))

        fig.show()

    def age_stats(self):
        ''' Display Age Statistics '''

        # Calculate age metrics
        self.age = self.df.groupby(['Age_group', 'Died']).agg(
            Number=('Age_group', 'count'))
        self.age = self.age.reset_index()
        self.age = self.age.astype({'Died':'object'})
        self.age['Died'] = self.age['Died'].map({0.0:'No', 1.0:'Yes'})
        self.age = self.age.pivot(index='Age_group', columns='Died', values='Number')

        # Create New Columns
        self.age['Mortality Rate'] = self.age['Yes'] / self.age['No']
        self.age['Total Cases'] = self.age['Yes'] + self.age['No']

        # Drop entries with an unknown Age
        self.age.drop(['Unknown'], inplace=True)

        # Reorder index by age
        self.age = self.age.reindex(['0-4 years', '5-14 years', '15-24 years', '25-34 years', '35-44 years', '45-54 years',
        '55-64 years', '65-74 years', '75-84 years', '85+ years'])

        ''' Ages of the Deceased '''
        df = self.age.where(self.age['Yes'] >= 1)
        fig = px.pie(df, values='Yes', names=df.index)
        fig.update_layout(title="Ages of the Deceased")
        fig.update_traces(textposition='inside', textinfo='label+percent')
        fig.show()

        ''' Affected Age Groups '''
        from plotly.subplots import make_subplots
        text = ['{0:.2%}'.format(val) for val in self.age['Mortality Rate']]

        fig = make_subplots(specs=[[{"secondary_y": True}]])

        fig.add_trace(
            go.Bar(x=self.age.index, y=self.age['Total Cases'], name="Total Cases", yaxis='y', offsetgroup=1),
            secondary_y=False,
        )

        fig.add_trace(
            go.Bar(x=self.age.index, y=text, name="Mortality Rate",
                  text=text, textposition='outside',
                   hoverinfo = "x+y",
                   marker=dict(color='rgb(214,39, 40)'), yaxis='y2', offsetgroup=2
                  ),
            secondary_y=True,
        )


        fig.update_layout(title= {'text':"Total Cases and Mortality Rate per Age Group",'x':0.5})
        fig.update_xaxes(title="Age Group")
        fig.update_yaxes(title="Number of Cases", secondary_y=False)
        fig.update_yaxes(title="Mortality Rate",ticksuffix='%', secondary_y=True)
        fig.show()


























