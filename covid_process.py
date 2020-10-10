# -*- coding: utf-8 -*-
"""
COVID-19 Data Visualiztion Processing
Created on Thu Apr 16 18:31:53 2020

@author: Jack
"""

import pandas as pd
from arcgis.gis import GIS
from pathlib import Path
import datetime as dt
import os


#import plotly as py
import plotly.graph_objects as go
import plotly.express as px
#from plotly.subplots import make_subplots
import plotly.io as pio
pio.renderers.default = "notebook"
#import cufflinks as cf
#cf.go_offline()







class Covid:
    def __init__(self):



        # If local csv file exists, use that
        self.csv_file = Path("./data/TimeSeries.csv")
        if not self.csv_file.is_file():
            print("No local copy found.")
            self.download_data()
        else:
            print("Checking to see if we have the most recent data...")
            today = dt.date.today()
            data_date = dt.datetime.fromtimestamp((os.path.getmtime(self.csv_file))).date()


            if data_date == today:
                print("Local data is up to date")
                self.process()
            else:
                print("Data is old...updating...")
                self.download_data()


    def download_data(self):
        ''' update local copy of data '''
        print("Downloading from server...")
        main_url = "https://services1.arcgis.com/CY1LXxl9zlJeBuRZ/ArcGIS/rest/services/Florida_COVID19_Case_Line_Data/FeatureServer/0?f=pjson"
        public_data_item_id = "0f0db541a48f47b7a8fd9ecc82358418"

        anon_gis = GIS()
        data_item = anon_gis.content.get(public_data_item_id)

        data_path = Path('./data')

        if not data_path.exists():
            data_path.mkdir()


        data_item.download(save_path=data_path)
        print("Updated.")


        self.process()

    def process(self):

        self.dataframe = pd.read_csv(self.csv_file, index_col=0, parse_dates=True)

        # Convert Date Column to DateTime dtype
        self.dataframe["Date"] = pd.to_datetime(self.dataframe["Date"])

        # Change the name of FREQ column
        self.dataframe.rename({"FREQUENCY" : "New Cases"}, axis=1, inplace=True)

        # Remove unnecessary columns
        del self.dataframe['State']

        # Sort Data by County
        self.dataframe.sort_values(by=["County"], inplace=True)

        # Generate new Dataframes for Marion and Alachua Counties
        self.dataframe.set_index('County', inplace=True)
        self.marion = self.dataframe.loc['Marion'].copy()
        self.alachua = self.dataframe.loc['Alachua'].copy()

        # List of dataframes to iterate through for making calculations and such
        self.frames = [self.marion, self.alachua]

        self.calculate()
        self.adjust_period()



    def calculate(self):
        # Calculate new metrics
        frames = [self.marion, self.alachua]
        for df in frames:
            # Sort by Date and reset the index
            df.set_index('Date', inplace=True)
            df.sort_values(by=['Date'], inplace=True)

            # Calculate new columns
            df['Total Cases'] = df['New Cases'].cumsum()
            df['Growth Factor'] = round((df['New Cases'] / df['New Cases'].shift(1)), 2)
            df.fillna(0, inplace=True)



    def adjust_period(self, period="W-MON"):
        ''' Resamle Data to specified time period, W = weekly, M = Monthly '''

        self.marion_adj = pd.DataFrame(self.marion["New Cases"])
        self.alachua_adj = pd.DataFrame(self.alachua["New Cases"])

        self.marion_adj = self.marion_adj.resample(period).sum()
        self.alachua_adj = self.alachua_adj.resample(period).sum()

        self.marion_adj['Total Cases'] = self.marion_adj['New Cases'].cumsum()
        self.alachua_adj['Total Cases'] = self.alachua_adj['New Cases'].cumsum()

        self.marion_adj['Growth Factor'] = round((self.marion_adj['New Cases'] / self.marion_adj['New Cases'].shift(1)), 2).fillna(0)
        self.alachua_adj['Growth Factor'] = round((self.alachua_adj['New Cases'] / self.alachua_adj['New Cases'].shift(1)), 2).fillna(0)


        # Drop incomplete week from Dataframe
        frames = [self.marion_adj, self.alachua_adj]
        for df in frames:
            if df.index[-1].strftime ('%d%m%Y') >= dt.datetime.today().strftime ('%d%m%Y'):
                df.drop([df.index[-1]], inplace=True)



    def state_wide(self):
        ''' Compare all counties state-wide '''
        self.state = self.dataframe.copy()
        self.state.reset_index(inplace=True)
        self.state.set_index('Date', inplace=True)



    def trajectory(self):
        ''' Chart the New Cases v. Total Cases on a log scale '''
        fig = go.Figure()


        ''' Alachua County'''
        df = self.alachua_adj
        fig.add_trace(go.Scatter(name='Alachua', mode='lines+markers',
                                 x=df['Total Cases'], y=df['New Cases'],
                                line = {'shape':'spline', 'smoothing':.9},
                                ))


        ''' Marion County '''
        df = self.marion_adj
        fig.add_trace(go.Scatter(name='Marion', mode='lines+markers',
                                 x=df['Total Cases'], y=df['New Cases'],
                                line = {'shape':'spline', 'smoothing':.9},
                                ))



        # Adjust Axes
        fig.update_layout(title= {'text':"Trajectory of COVID-19 Confirmed Cases (" + dt.date.today().strftime("%B %d, %Y") + ")",
                         'xanchor':'center', 'x':0.46})

        fig.update_xaxes(type="log", ticks='outside', title_text="Total Confired Cases")
        fig.update_yaxes(type="log", ticks='outside', title_text="Weekly New Cases")
        fig.show()

    def growth_factor(self):
        ''' Chart the County Growth Factors '''
        fig = go.Figure()


        ''' Alachua County'''
        df = self.alachua_adj
        fig.add_trace(go.Scatter(name='Alachua', mode='lines+markers',
                                 x=df.index[1:], y=df['Growth Factor'].iloc[1:],
                                line = {'shape':'spline', 'smoothing':.9},
                                ))


        ''' Marion County '''
        df = self.marion_adj
        fig.add_trace(go.Scatter(name='Marion', mode='lines+markers',
                                 x=df.index[1:], y=df['Growth Factor'].iloc[1:],
                                line = {'shape':'spline', 'smoothing':.9},
                                ))



        # Adjust Axes
        fig.update_layout(title= {'text':"COVID-19 Growth Factor by County",
                         'xanchor':'center', 'x':0.46})

        fig.update_xaxes(type="date", ticks='outside', title_text="")
        fig.update_yaxes(type="linear", ticks='outside', title_text="Weekly Growth Factor", range=[0,2])




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
            x=[dt.datetime(2020,3,24)],
            y=[1.1],
            text=["Growth Factor = 1"],
            mode="text",
            showlegend=False
        ))





        fig.show()

    def linear_progression(self):
        ''' Chart the Total Cases v. Date on a linear scale '''
        fig = go.Figure()


        ''' Alachua County'''
        df = self.alachua
        fig.add_trace(go.Scatter(name='Alachua', mode='lines+markers',
                                 x=df.index, y=df['Total Cases'],
                                line = {'shape':'spline', 'smoothing':.9},
                                ))


        ''' Marion County '''
        df = self.marion
        fig.add_trace(go.Scatter(name='Marion', mode='lines+markers',
                                 x=df.index, y=df['Total Cases'],
                                line = {'shape':'spline', 'smoothing':.9},
                                ))



        # Adjust Axes
        fig.update_layout(title= {'text':"Total Confirmed COVID-19 Cases (" + dt.date.today().strftime("%B %d, %Y") + ")",
                         'xanchor':'center', 'x':0.46})

        fig.update_xaxes(type="date", ticks='outside', title_text="")
        fig.update_yaxes(type="linear", ticks='outside', title_text="Total Cases")
        fig.show()

    def age_stats(self):
        df = self.df[['Age', 'Died']]
        df = df.groupby(['Age', 'Died']).size()







# So I don't have to type these for development purposes


